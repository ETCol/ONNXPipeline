# CRN Build Config Library

This directory contains one registered `CRNBuildConfig` for every one of the
25 multiplier--rectifier pairings in the current plug-and-play table.  The
table assignment is retained as metadata: 17 are direct, 6 require an
interface modification, and 2 are incompatible under the tested assumptions.

The key design rule is:

```python
CRNBuildConfig.crn_template + CRNBuildConfig.species_template
# are the structure passed to
CRN.from_string(crn_template, species=species_template)
```

## Files

```text
crn_build_configs/
    __init__.py
    base.py
    fragments.py
    table_extension_templates.py
    registry.py
    configs/
        toehold_exchange_threshold.py
        toehold_exchange_decoy.py
        toehold_exchange_cyclical.py
        toehold_exchange_weighted_subtraction.py
        toehold_exchange_pairwise_annihilation.py
        see_saw_threshold.py
        see_saw_decoy.py
        see_saw_cyclical.py
        see_saw_weighted_subtraction.py
        see_saw_pairwise_annihilation.py
        weight_loop_threshold.py
        weight_loop_decoy.py
        weight_loop_cyclical.py
        weight_loop_weighted_subtraction.py
        weight_loop_pairwise_annihilation.py
        weight_race_threshold.py
        weight_race_decoy.py
        weight_race_cyclical.py
        weight_race_weighted_subtraction.py
        weight_race_pairwise_annihilation.py
        switching_gate_threshold.py
        switching_gate_decoy.py
        switching_gate_cyclical.py
        switching_gate_weighted_subtraction.py
        switching_gate_pairwise_annihilation.py
validate_crn_configs.py
```

## Status

- The other direct entries are buildable template-level CRNs marked
  `draft_template_unvalidated_chemistry`.
- The six partial entries are marked
  `draft_template_partial_compatibility` and include explicit adapter or
  restoration species corresponding to the table's ``after modification``
  results.
- The two failed entries are marked
  `draft_template_incompatible_under_tested_assumptions`.  They are still
  executable CRN templates, but their failure status is retained and must not
  be interpreted as validated chemistry.
- All templates are structural/simulation artefacts.  Their rate constants are
  not experimentally calibrated DNA strand-displacement parameters.

## Usage

```python
from crn_build_configs import get_config
from crn_example import CRN

cfg = get_config("see_saw_pairwise_annihilation")
crn = cfg.build(CRN)

rendered = cfg.rendered(
    instance_id="o0_i1",
    species_overrides={"PosInput": "Input1"},
    initial_overrides={"Input1": 0.5, "PosGateOutput_o0_i1": 0.75},
)
crn_instance = rendered.build(CRN)
```

The partial and failed table rows can be selected in exactly the same way:

```python
partial = get_config("see_saw_threshold")
failed = get_config("see_saw_cyclical")
assert partial.compatibility_status == "partial"
assert failed.compatibility_status == "incompatible"
partial_crn = partial.build(CRN)
failed_crn = failed.build(CRN)
```

The registry retains the quantitative table evidence on each configuration in
`table_relative_error`, `table_stable_output`, and
`table_threshold_ordering`.

Run the syntax check with:

```bash
python validate_crn_configs.py
```
