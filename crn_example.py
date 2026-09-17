"""Small mass-action CRN parser and ODE simulator used by the pipeline.

The original research prototype depended on ``lmfit`` only for a container
around scalar rate constants. This version keeps the public ``CRN`` API while
using a tiny local parameter class, which makes the pipeline reproducible with
only NumPy and SciPy. ``CRN.parameters`` remains mapping-like for notebooks
that inspect or update rate values.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import numpy as np
from scipy.integrate import solve_ivp


@dataclass
class RateParameter:
    name: str
    value: float
    vary: bool = True
    min: float = 0.0


class ParameterSet(dict[str, RateParameter]):
    """Mapping-compatible replacement for the subset of lmfit used here."""

    def add(self, parameter: RateParameter) -> None:
        self[parameter.name] = parameter


class CRN:
    """Mass-action chemical reaction network."""

    def __init__(self, species: Sequence[str] | None = None):
        self.species = list(species or [])
        self.complexes: list[tuple[str, ...]] = []
        self.reactions: dict[tuple[tuple[str, ...], tuple[str, ...]], RateParameter] = {}
        self.parameters = ParameterSet()

    @property
    def complex_graph(self) -> np.ndarray:
        return np.asarray(
            [[complex_.count(name) for complex_ in self.complexes] for name in self.species],
            dtype=float,
        )

    @property
    def complex_adjacency(self) -> np.ndarray:
        return np.asarray(
            [
                [self.reactions.get((lhs, rhs), RateParameter("_missing", 0.0)).value for lhs in self.complexes]
                for rhs in self.complexes
            ],
            dtype=float,
        )

    def scale_concentration_unit(self, factor: float) -> None:
        """Rescale rates when changing concentration units."""

        factor = float(factor)
        for reaction, rate in self.reactions.items():
            rate.value *= factor ** (len(reaction[0]) - 1)

    def add_reaction(self, lhs: Sequence[str], rhs: Sequence[str], rate: RateParameter) -> None:
        if rate.name in self.parameters:
            raise ValueError(f"Parameter '{rate.name}' is already used.")
        if rate.value < 0:
            raise ValueError(f"Rate constant '{rate.name}' must be non-negative.")

        lhs_tuple = tuple(lhs)
        rhs_tuple = tuple(rhs)
        for name in lhs_tuple + rhs_tuple:
            if name not in self.species:
                self.species.append(name)
        for complex_ in (lhs_tuple, rhs_tuple):
            if complex_ not in self.complexes:
                self.complexes.append(complex_)

        key = (lhs_tuple, rhs_tuple)
        if key in self.reactions:
            raise ValueError(f"Duplicate reaction pair with parameter '{rate.name}'.")
        self.reactions[key] = rate
        self.parameters.add(rate)

    def rate_law(self):
        """Return the mass-action derivative function for ``solve_ivp``."""

        if not self.reactions:
            return lambda _time, state: np.zeros_like(state, dtype=float)

        species_index = {name: index for index, name in enumerate(self.species)}
        reactions = []
        for (lhs, rhs), rate in self.reactions.items():
            lhs_counts = np.zeros(len(self.species), dtype=float)
            rhs_counts = np.zeros(len(self.species), dtype=float)
            for name in lhs:
                lhs_counts[species_index[name]] += 1.0
            for name in rhs:
                rhs_counts[species_index[name]] += 1.0
            reactions.append((lhs_counts, rhs_counts - lhs_counts, rate))

        def kinetics(_time: float, state: np.ndarray) -> np.ndarray:
            # Numerical integration can make a concentration microscopically
            # negative. Clamp only for the rate calculation.
            concentrations = np.maximum(np.asarray(state, dtype=float), 0.0)
            derivative = np.zeros_like(concentrations)
            for lhs_counts, stoich, rate in reactions:
                propensity = float(rate.value)
                for index, count in enumerate(lhs_counts):
                    if count:
                        propensity *= concentrations[index] ** count
                derivative += stoich * propensity
            return derivative

        return kinetics

    def integrate(
        self,
        initial_condition: np.ndarray,
        t0: float = 0.0,
        t_eval: np.ndarray | None = None,
        **solve_kwargs,
    ) -> np.ndarray:
        initial = np.asarray(initial_condition, dtype=float)
        if initial.ndim != 1:
            raise ValueError("initial_condition must be a one-dimensional array")
        if initial.size != len(self.species):
            raise ValueError(
                f"initial_condition has {initial.size} values but CRN has {len(self.species)} species"
            )
        t_eval = np.asarray(t_eval if t_eval is not None else np.linspace(0.0, 100.0, 101), dtype=float)
        if t_eval.ndim != 1 or t_eval.size < 2:
            raise ValueError("t_eval must contain at least two time points")
        if np.any(np.diff(t_eval) < 0):
            raise ValueError("t_eval must be non-decreasing")

        result = solve_ivp(
            self.rate_law(),
            (float(t0), float(t_eval[-1])),
            initial,
            t_eval=t_eval,
            vectorized=False,
            **solve_kwargs,
        )
        if not result.success:
            raise RuntimeError(f"CRN integration failed: {result.message}")
        return result.y

    @staticmethod
    def _parse_complex(text: str) -> tuple[str, ...]:
        return tuple(sorted(token.strip() for token in text.split("+") if token.strip()))

    @classmethod
    def from_string(cls, text: str, species: Sequence[str] | None = None) -> "CRN":
        """Parse ``A + B -> C; rate_name=1.0`` reaction lines."""

        crn = cls(species=species)
        automatic_index = 0
        for line_number, original in enumerate(text.splitlines(), start=1):
            line = original.split("#", 1)[0].strip()
            if not line or "->" not in line:
                continue
            reaction_text, separator, rate_text = line.partition(";")
            if not separator:
                raise ValueError(f"line {line_number}: reaction is missing '; rate=value'")
            lhs_text, _, rhs_text = reaction_text.partition("->")
            lhs = cls._parse_complex(lhs_text)
            rhs = cls._parse_complex(rhs_text)
            if not lhs or not rhs:
                raise ValueError(f"line {line_number}: both reaction sides must contain species")

            rate_text = rate_text.strip()
            if "=" in rate_text:
                name, value_text = rate_text.split("=", 1)
                name = name.strip()
                if not name:
                    raise ValueError(f"line {line_number}: missing rate parameter name")
            else:
                name = f"k{automatic_index}"
                value_text = rate_text
                automatic_index += 1
            try:
                value = float(value_text.strip())
            except ValueError as exc:
                raise ValueError(f"line {line_number}: invalid rate value {value_text!r}") from exc
            crn.add_reaction(lhs, rhs, RateParameter(name=name, value=value))
        return crn

    @classmethod
    def from_kinDA(cls, path: str | Path, species: Sequence[str] | None = None) -> "CRN":
        """Read the reaction-rate table emitted by KinDA."""

        crn = cls(species=species)
        with open(path, newline="") as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                if len(row) >= 4 and row[0] == "reaction":
                    break
            for row in reader:
                if len(row) != 5:
                    break
                reaction, k_forward, _, k_backward = row[:4]
                lhs, rhs = cls._parse_reaction(reaction)
                if lhs == rhs:
                    continue
                kf = float(k_forward)
                kb = float(k_backward)
                effective = kf * kb / (kf + kb) if (kf + kb) else 0.0
                crn.add_reaction(lhs, rhs, RateParameter(f"k{len(crn.parameters)}", effective))
        return crn

    @classmethod
    def _parse_reaction(cls, string: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
        lhs, _, rhs = string.partition("->")
        return cls._parse_complex(lhs), cls._parse_complex(rhs)


__all__ = ["CRN", "ParameterSet", "RateParameter"]
