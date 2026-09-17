"""Validate that every CRNBuildConfig has CRN.from_string-compatible syntax.

This script uses a tiny parser so it does not require lmfit/scipy. It checks the
same high-level structure required by CRN.from_string: reaction lines contain
``->`` and ``; parameter=value`` rate constants; all species used in the CRN are
included in the species_template.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from crn_build_configs.registry import TABLE_ASSIGNMENTS, all_configs


def parse_species(template: str) -> list[str]:
    species = []
    for line_number, line in enumerate(template.splitlines(), start=1):
        if "->" not in line:
            continue
        reaction, sep, rate = line.partition(";")
        if not sep:
            raise ValueError(f"line {line_number}: reaction missing '; rate=value'")
        name, equals, value = rate.partition("=")
        if not name.strip() or not equals:
            raise ValueError(f"line {line_number}: malformed rate constant")
        float(value.strip())
        lhs, _, rhs = reaction.partition("->")
        for side in (lhs, rhs):
            for token in side.split("+"):
                name = token.strip()
                if name and name not in species:
                    species.append(name)
    return species


def main() -> int:
    failures = []
    configs = all_configs()
    for cfg in configs:
        try:
            expected_status = TABLE_ASSIGNMENTS[(cfg.multiplier, cfg.rectifier)]
            if cfg.compatibility_status != expected_status:
                raise ValueError(
                    f"table assignment is {expected_status!r}, but config metadata is "
                    f"{cfg.compatibility_status!r}"
                )
            used_species = parse_species(cfg.crn_template)
            missing = [s for s in used_species if s not in cfg.species_template]
            if missing:
                raise ValueError(f"missing species from species_template: {missing}")
            rendered = cfg.rendered(instance_id="o0_i0")
            parse_species(rendered.crn_template)
        except Exception as exc:  # noqa: BLE001 - validation output should be explicit
            failures.append((cfg.id, exc))

    if failures:
        for config_id, exc in failures:
            print(f"FAIL {config_id}: {exc}")
        return 1

    print(f"OK: validated {len(configs)} CRNBuildConfig files against the complete table")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
