from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Mapping, Sequence
import re


@dataclass(frozen=True)
class RenderedCRNBuildConfig:
    """A concrete CRN template after optional species/parameter renaming."""

    config_id: str
    crn_template: str
    species: list[str]
    initial_conditions: dict[str, float]
    role_map: dict[str, str]

    def build(self, CRN):
        """Build with the user's CRN class, usually CRN.from_string(...)."""
        return CRN.from_string(self.crn_template, species=list(self.species))


@dataclass(frozen=True)
class CRNBuildConfig:
    """Complete CRN construction structure for one plug-and-play table entry.

    The important fields are ``crn_template`` and ``species_template``. Together
    they are the structure passed to ``CRN.from_string(crn_template, species=...)``.
    Labels such as multiplier/rectifier/reporter are metadata for XML, XPath,
    registry lookup, and experiment tracking.
    """

    id: str
    multiplier: str
    rectifier: str
    reporter: str
    crn_template: str
    species_template: Sequence[str]
    default_initial_conditions: Mapping[str, float]
    role_map: Mapping[str, str]
    status: str = "template_level"
    description: str = ""
    compatibility_status: str = "direct"
    table_relative_error: float | None = None
    table_stable_output: bool | None = None
    table_threshold_ordering: bool | None = None
    table_note: str = ""

    def build(self, CRN):
        """Build the unrendered template with the user's CRN class."""
        return CRN.from_string(self.crn_template, species=list(self.species_template))

    def rendered(
        self,
        *,
        instance_id: str | None = None,
        species_overrides: Mapping[str, str] | None = None,
        parameter_suffix: str | None = None,
        initial_overrides: Mapping[str, float] | None = None,
    ) -> RenderedCRNBuildConfig:
        """Return a concrete, optionally renamed CRN template.

        ``instance_id`` is useful when instantiating the same CRNBuildConfig for
        many inputs/weights/neurons. It suffixes species and parameters so they
        do not collide. ``species_overrides`` can then pin selected abstract
        species to externally defined names, for example ``{"PosInput": "Input0"}``.
        """
        species_overrides = dict(species_overrides or {})
        initial_overrides = dict(initial_overrides or {})

        suffix = f"_{instance_id}" if instance_id else ""
        rendered_species = {
            name: species_overrides.get(name, f"{name}{suffix}")
            for name in self.species_template
        }

        text = self.crn_template
        # Replace longer names first to avoid partial replacement.
        for old in sorted(rendered_species, key=len, reverse=True):
            new = rendered_species[old]
            text = re.sub(rf"\b{re.escape(old)}\b", new, text)

        param_suffix = parameter_suffix if parameter_suffix is not None else suffix
        if param_suffix:
            text = _suffix_parameter_names(text, param_suffix)

        init = {
            rendered_species[name]: value
            for name, value in self.default_initial_conditions.items()
            if name in rendered_species
        }
        # initial_overrides are assumed to refer to rendered species names.
        init.update(initial_overrides)

        rendered_role_map = {
            role: rendered_species.get(species_name, species_overrides.get(species_name, species_name))
            for role, species_name in self.role_map.items()
        }

        return RenderedCRNBuildConfig(
            config_id=self.id,
            crn_template=text,
            species=list(rendered_species.values()),
            initial_conditions=init,
            role_map=rendered_role_map,
        )

    def with_rates(self, **rates: float) -> "CRNBuildConfig":
        """Return a copy with selected rate constants replaced by value.

        Example: ``cfg.with_rates(ss_pos_bind=0.5, ss_neg_bind=0.5)``.
        """
        text = self.crn_template
        for name, value in rates.items():
            text = re.sub(rf"(?<=;\s){re.escape(name)}\s*=\s*[-+0-9.eE]+", f"{name}={value}", text)
        return replace(self, crn_template=text)


def _suffix_parameter_names(text: str, suffix: str) -> str:
    def repl(match: re.Match[str]) -> str:
        return f"; {match.group(1)}{suffix}="

    return re.sub(r";\s*([A-Za-z_]\w*)\s*=", repl, text)
