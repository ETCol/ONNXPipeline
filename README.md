# ONNX-to-CRN pipeline

This repository contains the computational pipeline described in Chapter 3 of
the thesis *An End-to-End Pipeline for the Development of Molecular Neural
Networks*. It converts a restricted, perceptron-style ONNX model into an
inspectable chemical reaction network (CRN), assigns initial concentrations,
and optionally simulates the CRN with mass-action ordinary differential
equations.

The public conversion path is deliberately explicit:

```text
ONNX model
  -> weight/bias extraction
  -> editable XML intermediate representation
  -> optional XPath edits
  -> signed CRN synthesis
  -> ordered species and initial concentrations
  -> numerical simulation and reporter output
```

The implementation supports a single rank-two weight initializer and an
optional matching bias initializer. It does not claim to convert arbitrary
ONNX graphs, deep networks, convolutional layers, recurrent networks, or
nonlinear activation operators.

## Installation

Python 3.10 or newer is required.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Optional dependencies are listed in `requirements-optional.txt`. Install
`matplotlib` to use `--plot`, `lxml` for full XPath expressions, and
`onnxruntime` for the optional digital-versus-CRN evaluator.

The package can also be installed in editable mode:

```bash
python -m pip install -e .
```

## Quick start

The smallest reproducible invocation is:

```bash
python crn_cli.py \
  --model simplest_model.onnx \
  --input Input0=0.5 \
  --input Input1=0.5 \
  --no-plot \
  --export-xml results/network.xml \
  --save-dir results/example_run
```

The same input values can be supplied in JSON:

```json
{
  "Input0": 0.5,
  "Input1": 0.5
}
```

```bash
python crn_cli.py \
  --model simplest_model.onnx \
  --inputs-json inputs.json \
  --no-plot \
  --save-dir results/example_run
```

When both forms are supplied, repeated `--input KEY=VALUE` values override
values read from JSON.

## Programmatic API

```python
from onnx_crn_pipeline import (
    CRNBuildConfig,
    convert_onnx_model,
    simulate_crn,
)

config = CRNBuildConfig(
    fuel_conc=10.0,
    k_bind=1.0,
    k_unbind=0.1,
    k_output=1.0,
)

result = convert_onnx_model(
    "simplest_model.onnx",
    {"Input0": 0.5, "Input1": 0.5},
    config,
    export_xml_path="network.xml",
)

times, trajectory = simulate_crn(
    result.crn_code,
    result.species_list,
    result.init_cond,
    tmax=100.0,
    steps=101,
)
```

For compatibility with the earlier research scripts, the three-value entry
point remains available:

```python
from onnx_crn_pipeline import onnx_to_crn_perceptron_multi_output

crn_code, species_list, init_cond = onnx_to_crn_perceptron_multi_output(
    "simplest_model.onnx",
    {"Input0": 0.5, "Input1": 0.5},
)
```

## CLI options

```text
-m, --model PATH             Required ONNX model
-j, --inputs-json PATH       JSON input concentrations
-i, --input KEY=VALUE        Repeatable input override
    --config PATH            JSON CRNBuildConfig values
    --set KEY=VALUE          Override a configuration value
    --config-id ID            Default motif-registry ID in the XML
    --xpath-config X=ID       Reassign XPath-selected components; repeatable
    --xpath EXPR              Query the exported XML
    --xpath-mask EXPR         Keep only selected neuron nodes
    --zero-weights-xpath EXPR Set selected weights to zero
    --fuel-conc VALUE         Ordinary fuel initial concentration
    --tmax VALUE              Simulation end time; default 100
    --steps N                 Number of time samples; default 101
    --plot / --no-plot        Reporter plot; plotting is enabled by default
    --export-xml PATH         Save the intermediate XML representation
    --save-dir DIRECTORY      Save CRN and simulation arrays
```

The saved directory contains:

```text
crn.txt          generated reaction text
species.txt      ordered simulator species
init.npy         initial concentration vector
times.npy        simulation time vector
trajectory.npy   concentration trajectory, shape (species, time)
metadata.json    selected config IDs and extracted parameters
```

The CLI exits with status 2 for malformed arguments, missing input
concentrations, invalid files, or conversion/simulation errors.

## XML and XPath customisation

The XML intermediate representation records the extracted layer, neurons,
weights, biases, species roles, and the selected motif metadata. For example,
the following changes the implementation metadata for neuron 0:

```bash
python crn_cli.py \
  --model simplest_model.onnx \
  --input Input0=0.5 \
  --input Input1=0.5 \
  --no-plot \
  --export-xml results/reassigned.xml \
  --xpath-config "//neuron[@index='0']/implementation=see_saw_pairwise_annihilation"
```

Weight suppression and neuron filtering can be combined with reassignment:

```bash
python crn_cli.py \
  --model simplest_model.onnx \
  --input Input0=0.5 \
  --input Input1=0.5 \
  --no-plot \
  --zero-weights-xpath "//weight[@input='Input1']" \
  --xpath-mask "//neuron[@index='0']" \
  --export-xml results/edited.xml
```

The documented XPath examples work with the standard-library fallback. Full
XPath syntax is available when `lxml` is installed.

## CRN build-configuration library

`crn_build_configs/` packages every entry from the Chapter 2 plug-and-play
table. It contains 25 registered configurations: 17 direct pairings, six
partial pairings that require an interface modification, and two pairings
that remain incompatible under the tested assumptions. Each entry has a
common `CRNBuildConfig` base, rendering/renaming support, table-status
metadata, and a registry.

Validate the templates with:

```bash
python validate_crn_configs.py
```

Use a template directly:

```python
from crn_build_configs import get_config
from crn_example import CRN

template = get_config("see_saw_pairwise_annihilation")
rendered = template.rendered(
    instance_id="o0_i0",
    species_overrides={"PosInput": "Input0", "NegInput": "ZeroInput"},
)
crn = rendered.build(CRN)
```

The default `library_template` backend expands these templates into per-weight
modules and composes their positive/negative rails:

```python
config = CRNBuildConfig(
    config_id="see_saw_pairwise_annihilation",
    backend="library_template",
)
```

Only the source-derived see-saw plus pairwise-annihilation template is marked
as source-derived. The other entries are explicitly marked
`draft_template_unvalidated_chemistry`,
`draft_template_partial_compatibility`, or
`draft_template_incompatible_under_tested_assumptions`. Their reaction
structures and rates must not be treated as experimentally calibrated DNA
designs. Partial and failed table outcomes are preserved rather than hidden.

For example, failed table entries remain selectable and buildable:

```python
failed = get_config("see_saw_cyclical")
assert failed.compatibility_status == "incompatible"
crn = failed.build(CRN)
```

The smaller `signed_linear` backend is available explicitly when a compact
motif-independent baseline is required:

```python
config = CRNBuildConfig(backend="signed_linear")
```

## Kinetics and limitations

The default rates and concentrations are simulation parameters. They are not
experimentally validated DNA strand-displacement constants. Physical
implementation would require motif-specific sequence design, leak analysis,
kinetic calibration, and laboratory validation.

The default `library_template` backend expands the selected multiplier and
rectifier configuration for each non-zero weight, routes the resulting
positive and negative contributions to output rails, and activates the
reporter. Biases are extracted and retained in the XML and metadata, but are
not automatically encoded as constitutive production or threshold reactions.
A bias-aware chemical implementation remains a separate development task.

`backend="library_template"` is the Chapter 3 default composition path for
the packaged templates. It does not turn a draft, partial, or incompatible
template into an experimentally validated motif.

## Repository layout

```text
onnx_crn_pipeline.py       Core ONNX-to-CRN conversion API
crn_cli.py                 Command-line interface
crn_example.py             Local CRN parser and simulator
evaluate_onnx_vs_crn.py    Optional digital-versus-CRN evaluator
validate_crn_configs.py    CRNBuildConfig validation script
crn_build_configs/         Complete 25-entry motif configuration registry
tests/                     Automated tests
simplest_model.onnx        Small reproducible example model
```


## Validation

Run the unit tests from the repository root:

```bash
python -m unittest discover -s tests -v
python validate_crn_configs.py
```

The tests cover ONNX extraction, conversion, initialisation, XML/XPath edits,
simulation, the Chapter 3 CLI output set, and rendering of every registered
build template.

## License

This project is released under the MIT License. See [LICENSE](LICENSE).
