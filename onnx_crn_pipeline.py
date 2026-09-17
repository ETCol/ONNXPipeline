"""ONNX-to-CRN conversion pipeline.

The public conversion path implemented here follows the six stages described
in Chapter 3 of the thesis:

1. extract weights and optional biases from an ONNX model;
2. create an editable XML intermediate representation;
3. apply optional XPath weight/neuron/motif edits;
4. synthesise a signed, mass-action CRN;
5. construct an ordered species list and initial concentrations; and
6. optionally simulate the CRN with :class:`crn_example.CRN`.

The default conversion path expands the selected ``CRNBuildConfig`` template
from the plug-and-play registry. It is a computational CRN construction, not
a claim that every packaged motif template is experimentally validated. The
explicit ``signed_linear`` backend remains available as a small inspectable
scaffold when a motif-independent baseline is required.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
from xml.etree import ElementTree as ET

import numpy as np
import onnx
from onnx import numpy_helper


IMPLEMENTED_CONFIG_ID = "linear_perceptron"


@dataclass
class CRNBuildConfig:
    """Configuration for the ONNX-to-CRN conversion scaffold.

    ``config_id`` selects the multiplier--rectifier entry in the packaged
    motif registry. The default ``library_template`` backend expands that
    template into the generated CRN; the selected motif is also preserved in
    the XML and CRN comments so conversions remain inspectable and
    reproducible. The optional ``signed_linear`` backend provides the compact
    motif-independent scaffold described in the implementation notes.
    """

    # Intermediate-representation / motif metadata
    config_id: str = "toehold_exchange_threshold"
    multiplier: str = "toehold_exchange"
    rectifier: str = "threshold"
    reporter: str = "act_reporter"
    weight_initializer: str | None = None
    bias_initializer: str | None = None
    backend: str = "library_template"

    # Species and structural naming
    species_prefix: str = ""
    input_species_prefix: str = "Input"
    fuel_species: str = "Fuel"
    reporter_role: str = "ActReporter"
    include_gate_fuel: bool = True

    # Kinetics and scaling
    fuel_conc: float = 10.0
    gate_conc: float = 1.0
    reporter_conc: float = 1.0
    k_bind: float = 1.0
    k_unbind: float = 0.1
    k_output: float = 1.0
    k_fuel: float = 1.0
    k_annihilate: float = 1.0
    hill_n: float = 1.0
    input_scale: float = 1.0
    weight_scale: float = 1.0
    bias_shift: float = 0.0

    # XPath-driven structural edits
    zero_weights_xpath: str | None = None
    mask_neurons_xpath: str | None = None
    motif_reassignments: list[tuple[str, str]] = field(default_factory=list)

    # Output formatting
    round_weights: int | None = None
    emit_comments: bool = True

    # Extensible options retained in generated metadata
    extras: dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversionResult:
    """Complete result of one conversion."""

    crn_code: str
    species_list: list[str]
    init_cond: np.ndarray
    xml_tree: ET.ElementTree
    config_ids: list[str]
    weights: np.ndarray
    bias: np.ndarray

    def as_tuple(self) -> tuple[str, list[str], np.ndarray]:
        return self.crn_code, self.species_list, self.init_cond


def config_from_dict(values: Mapping[str, Any]) -> CRNBuildConfig:
    """Create a :class:`CRNBuildConfig` while preserving unknown keys.

    JSON configuration files are intentionally allowed to contain additional
    metadata. Known dataclass fields become typed configuration values; any
    remaining keys are retained in ``extras`` rather than causing a fragile
    constructor error.
    """

    known = {item.name for item in fields(CRNBuildConfig)}
    data = dict(values)
    extras = dict(data.pop("extras", {}) or {})
    for key in list(data):
        if key not in known:
            extras[key] = data.pop(key)

    assignments = data.get("motif_reassignments")
    if assignments is not None:
        data["motif_reassignments"] = _normalise_reassignments(assignments)
    data["extras"] = extras
    return CRNBuildConfig(**data)


def _normalise_reassignments(value: Any) -> list[tuple[str, str]]:
    if value is None:
        return []
    if isinstance(value, Mapping):
        return [(str(xpath), str(config_id)) for xpath, config_id in value.items()]
    result: list[tuple[str, str]] = []
    for item in value:
        if isinstance(item, Mapping):
            result.append((str(item["xpath"]), str(item["config_id"])))
        elif isinstance(item, Sequence) and len(item) == 2:
            result.append((str(item[0]), str(item[1])))
        else:
            raise ValueError(
                "motif_reassignments must contain [xpath, config_id] pairs or objects"
            )
    return result


def _config_metadata(config_id: str) -> dict[str, str]:
    """Return registry metadata for an implementation/configuration ID."""

    if config_id == IMPLEMENTED_CONFIG_ID:
        return {
            "config_id": config_id,
            "multiplier": "signed_linear",
            "rectifier": "positive_negative_annihilation",
            "reporter": "act_reporter",
            "status": "implemented_computational_scaffold",
        }

    try:
        from crn_build_configs.registry import get_config

        cfg = get_config(config_id)
    except (ImportError, KeyError) as exc:
        raise ValueError(f"Unknown CRN build configuration: {config_id}") from exc

    return {
        "config_id": cfg.id,
        "multiplier": cfg.multiplier,
        "rectifier": cfg.rectifier,
        "reporter": cfg.reporter,
        "status": cfg.status,
    }


def _as_float_array(tensor: onnx.TensorProto) -> np.ndarray:
    """Decode an ONNX tensor using ONNX's datatype-aware helper."""

    return np.asarray(numpy_helper.to_array(tensor), dtype=np.float64)


def load_linear_parameters(
    path: str | Path,
    *,
    weight_initializer: str | None = None,
    bias_initializer: str | None = None,
) -> tuple[onnx.ModelProto, np.ndarray, np.ndarray]:
    """Load a perceptron-style weight matrix and optional bias from ONNX.

    The first rank-two initializer containing ``weight`` is selected. The
    first initializer containing ``bias`` is selected and flattened. ONNX's
    datatype-aware decoder is used, so models that store values in
    ``float_data`` or another supported representation are handled as well as
    models that use ``raw_data``.
    """

    model_path = Path(path)
    if not model_path.is_file():
        raise FileNotFoundError(f"ONNX model not found: {model_path}")

    model = onnx.load(str(model_path))
    weight_candidates: list[np.ndarray] = []
    bias_candidates: list[np.ndarray] = []

    for initializer in model.graph.initializer:
        name = initializer.name.lower()
        array = _as_float_array(initializer)
        if "weight" in name and array.ndim == 2:
            weight_candidates.append(array)
        elif "bias" in name:
            bias_candidates.append(array.reshape(-1))

    if weight_initializer is not None:
        selected = next(
            (initializer for initializer in model.graph.initializer if initializer.name == weight_initializer),
            None,
        )
        if selected is None:
            raise ValueError(f"Requested weight initializer not found: {weight_initializer}")
        selected_array = _as_float_array(selected)
        if selected_array.ndim != 2:
            raise ValueError(f"Requested weight initializer is not rank two: {weight_initializer}")
        weight_candidates = [selected_array]

    if not weight_candidates:
        raise ValueError(
            "No rank-two ONNX weight initializer containing 'weight' was found. "
            "The public converter currently targets perceptron-style models."
        )

    if len(weight_candidates) > 1:
        names = [initializer.name for initializer in model.graph.initializer if "weight" in initializer.name.lower()]
        raise ValueError(
            "Multiple weight initializers were found ({}). The current public "
            "converter targets a single perceptron layer; set weight_initializer "
            "explicitly only when you intentionally want to convert one layer.".format(", ".join(names))
        )

    weights = np.asarray(weight_candidates[0], dtype=float)
    output_count = weights.shape[0]
    if bias_initializer is not None:
        selected_bias = next(
            (initializer for initializer in model.graph.initializer if initializer.name == bias_initializer),
            None,
        )
        if selected_bias is None:
            raise ValueError(f"Requested bias initializer not found: {bias_initializer}")
        bias = _as_float_array(selected_bias).reshape(-1)
    elif bias_candidates:
        bias = np.asarray(bias_candidates[0], dtype=float)
        if bias.size != output_count:
            raise ValueError(
                f"Bias has {bias.size} values but the weight matrix has "
                f"{output_count} output rows."
            )
    else:
        bias = np.zeros(output_count, dtype=float)

    return model, weights, bias


def _input_name(cfg: CRNBuildConfig, index: int) -> str:
    return f"{cfg.species_prefix}{cfg.input_species_prefix}{index}"


def _reporter_input_name(cfg: CRNBuildConfig, output_index: int, output_count: int) -> str:
    base = "Reporter" if output_count == 1 else f"Reporter_o{output_index}"
    return f"{cfg.species_prefix}{base}"


def _weight_text(value: float, cfg: CRNBuildConfig) -> str:
    if cfg.round_weights is not None:
        return str(round(float(value), cfg.round_weights))
    return repr(float(value))


def build_network_xml(
    weights: np.ndarray,
    bias: np.ndarray,
    cfg: CRNBuildConfig | None = None,
    config_ids: Sequence[str] | None = None,
) -> ET.ElementTree:
    """Build the editable XML intermediate representation."""

    cfg = cfg or CRNBuildConfig()
    weights = np.asarray(weights, dtype=float)
    bias = np.asarray(bias, dtype=float).reshape(-1)
    if weights.ndim != 2:
        raise ValueError("weights must be a rank-two matrix")
    if bias.size != weights.shape[0]:
        raise ValueError("bias length must equal the number of weight rows")

    selected_ids = list(config_ids or [cfg.config_id] * weights.shape[0])
    if len(selected_ids) != weights.shape[0]:
        raise ValueError("config_ids must contain one entry per output row")

    root = ET.Element(
        "network",
        {
            "framework": "onnx",
            "kind": "perceptron",
            "backend": cfg.backend,
        },
    )
    layer = ET.SubElement(
        root,
        "layer",
        {"index": "0", "type": "linear", "inputs": str(weights.shape[1]), "outputs": str(weights.shape[0])},
    )

    for output_index in range(weights.shape[0]):
        config_id = selected_ids[output_index]
        metadata = _config_metadata(config_id)
        neuron = ET.SubElement(
            layer,
            "neuron",
            {"index": str(output_index), "output": str(output_index)},
        )
        bias_node = ET.SubElement(neuron, "bias", {"value": _weight_text(bias[output_index], cfg)})

        implementation = ET.SubElement(
            neuron,
            "implementation",
            {
                "config_id": metadata["config_id"],
                "multiplier": metadata["multiplier"],
                "rectifier": metadata["rectifier"],
                "reporter": metadata["reporter"],
                "status": metadata["status"],
            },
        )
        ET.SubElement(implementation, "multiplier", {"type": metadata["multiplier"]})
        ET.SubElement(implementation, "rectifier", {"type": metadata["rectifier"]})
        ET.SubElement(implementation, "reporter", {"type": metadata["reporter"]})

        for input_index, value in enumerate(weights[output_index]):
            weight = ET.SubElement(
                neuron,
                "weight",
                {"input": f"{cfg.input_species_prefix}{input_index}", "value": _weight_text(value, cfg)},
            )
            species_base = f"{cfg.species_prefix}{cfg.input_species_prefix}{input_index}"
            ET.SubElement(
                neuron,
                "species",
                {"role": "gate", "input_index": str(input_index), "name": f"{species_base}Gate_o{output_index}"},
            )
            ET.SubElement(
                neuron,
                "species",
                {"role": "out", "input_index": str(input_index), "name": f"{species_base}Output_o{output_index}"},
            )
            if cfg.include_gate_fuel:
                ET.SubElement(
                    neuron,
                    "species",
                    {
                        "role": "gate_fuel",
                        "input_index": str(input_index),
                        "name": f"{species_base}GateFuel_o{output_index}",
                    },
                )

        ET.SubElement(
            neuron,
            "species",
            {
                "role": cfg.reporter_role,
                "name": f"{cfg.species_prefix}{cfg.reporter_role}{output_index}",
            },
        )

    return ET.ElementTree(root)


def _xpath_matches(root: ET.Element, expression: str) -> list[dict[str, Any]]:
    """Return selected node descriptors, retaining their neuron parent."""

    try:
        from lxml import etree as LET  # type: ignore
    except ImportError:
        normalised = expression
        if normalised.startswith("//"):
            normalised = "." + normalised
        try:
            selected = list(root.findall(normalised))
        except SyntaxError as exc:
            raise ValueError(
                "Full XPath support requires lxml; install the optional 'xpath' dependency."
            ) from exc
        matches: list[dict[str, Any]] = []
        for node in selected:
            parent_index = None
            if node.tag == "neuron":
                parent_index = node.attrib.get("index")
            elif node.tag in {"implementation", "weight"}:
                for neuron in root.iter("neuron"):
                    if any(child is node for child in list(neuron)):
                        parent_index = neuron.attrib.get("index")
                        break
            matches.append({"tag": node.tag, "attrib": dict(node.attrib), "neuron_index": parent_index})
        return matches

    root_lxml = LET.fromstring(ET.tostring(root, encoding="utf-8"))
    selected = root_lxml.xpath(expression)
    matches = []
    for node in selected:
        if not hasattr(node, "tag"):
            continue
        parent = node
        while parent is not None and parent.tag != "neuron":
            parent = parent.getparent()
        matches.append(
            {
                "tag": node.tag,
                "attrib": dict(node.attrib),
                "neuron_index": parent.attrib.get("index") if parent is not None else None,
            }
        )
    return matches


def _set_implementation_metadata(implementation: ET.Element, config_id: str) -> None:
    metadata = _config_metadata(config_id)
    implementation.attrib.update(metadata)
    # Remove and recreate the child descriptors to avoid stale motif labels.
    implementation[:] = []
    ET.SubElement(implementation, "multiplier", {"type": metadata["multiplier"]})
    ET.SubElement(implementation, "rectifier", {"type": metadata["rectifier"]})
    ET.SubElement(implementation, "reporter", {"type": metadata["reporter"]})


def _apply_xpath_to_tree(
    weights: np.ndarray,
    bias: np.ndarray,
    cfg: CRNBuildConfig,
    tree: ET.ElementTree,
) -> tuple[np.ndarray, np.ndarray, ET.ElementTree, list[str]]:
    """Apply structural and motif edits to the XML/parameter representation."""

    root = tree.getroot()
    current_weights = np.asarray(weights, dtype=float).copy()
    current_bias = np.asarray(bias, dtype=float).copy()
    config_ids = [cfg.config_id] * current_weights.shape[0]

    if cfg.zero_weights_xpath:
        selected = _xpath_matches(root, cfg.zero_weights_xpath)
        if not selected:
            raise ValueError(f"zero_weights_xpath matched no nodes: {cfg.zero_weights_xpath}")
        for match in selected:
            if match["tag"] != "weight":
                continue
            out_index_text = match.get("neuron_index")
            if out_index_text is None:
                continue
            out_index = int(out_index_text)
            input_name = match["attrib"].get("input", "")
            if not input_name.startswith(cfg.input_species_prefix):
                continue
            in_index = int(input_name.replace(cfg.input_species_prefix, "", 1))
            if 0 <= out_index < current_weights.shape[0] and 0 <= in_index < current_weights.shape[1]:
                current_weights[out_index, in_index] = 0.0
                for candidate in root.findall(f".//neuron[@index='{out_index}']/weight[@input='{cfg.input_species_prefix}{in_index}']"):
                    candidate.set("value", "0.0")
                    candidate.text = "0.0"

    if cfg.mask_neurons_xpath:
        selected = _xpath_matches(root, cfg.mask_neurons_xpath)
        selected_indices = sorted(
            {
                int(match["attrib"]["index"])
                for match in selected
                if match["tag"] == "neuron" and match["attrib"].get("index", "").isdigit()
            }
        )
        if not selected_indices:
            raise ValueError(f"mask_neurons_xpath matched no neuron nodes: {cfg.mask_neurons_xpath}")
        selected_indices = [i for i in selected_indices if 0 <= i < current_weights.shape[0]]
        current_weights = current_weights[selected_indices, :]
        current_bias = current_bias[selected_indices]
        config_ids = [config_ids[i] for i in selected_indices]
        tree = build_network_xml(current_weights, current_bias, cfg, config_ids)
        root = tree.getroot()

    # Apply motif assignments after masking, so expressions refer to the XML
    # that will be exported and used for CRN generation.
    for expression, config_id in _normalise_reassignments(cfg.motif_reassignments):
        selected = _xpath_matches(root, expression)
        if not selected:
            raise ValueError(f"motif XPath matched no nodes: {expression}")
        for match in selected:
            neuron_index = match.get("neuron_index")
            neuron = root.find(f".//neuron[@index='{neuron_index}']") if neuron_index is not None else None
            implementation = neuron.find("implementation") if neuron is not None else None
            if implementation is None:
                continue
            _set_implementation_metadata(implementation, config_id)
            if neuron_index is not None and neuron_index.isdigit():
                config_ids[int(neuron_index)] = config_id

    return current_weights, current_bias, tree, config_ids


def generate_initial_conditions(
    species_list: Sequence[str],
    input_vals: Mapping[str, float],
    cfg: CRNBuildConfig,
) -> np.ndarray:
    """Generate concentrations aligned with ``species_list``.

    Explicit user inputs take precedence. Gate and reporter reservoirs use the
    documented unit defaults; ordinary fuel uses ``fuel_conc``; all remaining
    species start at zero.
    """

    input_vals = {str(key): float(value) for key, value in input_vals.items()}
    result: list[float] = []
    for species in species_list:
        unprefixed = species[len(cfg.species_prefix):] if cfg.species_prefix and species.startswith(cfg.species_prefix) else species
        if species in input_vals:
            result.append(input_vals[species] * cfg.input_scale)
        elif unprefixed in input_vals:
            result.append(input_vals[unprefixed] * cfg.input_scale)
        elif unprefixed.startswith(cfg.input_species_prefix):
            result.append(0.0)
        elif unprefixed == cfg.fuel_species or (unprefixed.endswith("Fuel") and "Gate" not in unprefixed):
            result.append(float(cfg.fuel_conc))
        elif "GateOutput" in unprefixed or "GateFuel" in unprefixed or "Gate" in unprefixed and unprefixed.endswith("Gate"):
            result.append(float(cfg.gate_conc))
        elif unprefixed == "Reporter" or unprefixed.startswith("Reporter_o"):
            result.append(float(cfg.reporter_conc))
        else:
            result.append(0.0)
    return np.asarray(result, dtype=float)


def _parameter_name(prefix: str, output_index: int, input_index: int, role: str) -> str:
    return f"{prefix}{role}_o{output_index}_i{input_index}"


def linear_to_crn(
    weights: Sequence[float],
    bias: float,
    cfg: CRNBuildConfig,
    output_index: int,
    output_count: int,
) -> tuple[list[str], set[str]]:
    """Generate the signed mass-action scaffold for one output row.

    Positive and negative weighted contributions are routed to separate rails.
    The rails annihilate before the positive rail activates the output reporter.
    Biases are retained in the XML and metadata but are not silently encoded as
    chemical reactions; this matches the limitation documented in Chapter 3.
    """

    lines: list[str] = []
    species: set[str] = set()
    prefix = cfg.species_prefix
    reporter_input = _reporter_input_name(cfg, output_index, output_count)
    reporter_output = f"{prefix}{cfg.reporter_role}{output_index}"
    positive_sum = f"{prefix}PosWeightedSum_o{output_index}"
    negative_sum = f"{prefix}NegWeightedSum_o{output_index}"
    waste = f"{prefix}SignedWaste_o{output_index}"
    fuel = f"{prefix}{cfg.fuel_species}"
    species.update({reporter_input, reporter_output, positive_sum, negative_sum, waste, fuel})

    if cfg.emit_comments:
        lines.append(
            f"# output={output_index} config_id={cfg.config_id} "
            f"bias={float(bias):.17g} (bias retained in XML; not encoded)"
        )

    for input_index, raw_weight in enumerate(weights):
        # ``convert_onnx_model`` applies weight_scale once before this helper;
        # keeping this helper on effective weights also makes its standalone
        # behaviour explicit.
        weight = float(raw_weight)
        if np.isclose(weight, 0.0):
            if cfg.emit_comments:
                lines.append(f"# suppressed zero weight: output={output_index}, input={input_index}")
            continue

        inp = _input_name(cfg, input_index)
        gate = f"{prefix}GateOutput{input_index}_o{output_index}"
        inp_gate = f"{prefix}InputGate{input_index}_o{output_index}"
        gate_fuel = f"{prefix}GateFuel{input_index}_o{output_index}"
        contribution = f"{prefix}{'Pos' if weight > 0 else 'Neg'}Output{input_index}_o{output_index}"
        target_sum = positive_sum if weight > 0 else negative_sum
        magnitude = abs(weight)
        bind = max(float(cfg.k_bind) * magnitude, np.finfo(float).eps)
        unbind = max(float(cfg.k_unbind), 0.0)
        fuel_rate = max(float(cfg.k_fuel), 0.0)
        route_rate = max(float(cfg.k_output) * magnitude, np.finfo(float).eps)

        species.update({inp, gate, inp_gate, contribution})
        if cfg.include_gate_fuel:
            species.add(gate_fuel)

        lines.extend(
            [
                f"{inp} + {gate} -> {inp_gate} + {contribution}; "
                f"{_parameter_name('bind', output_index, input_index, 'pos' if weight > 0 else 'neg')}={bind:.17g}",
                f"{inp_gate} + {contribution} -> {inp} + {gate}; "
                f"{_parameter_name('unbind', output_index, input_index, 'pos' if weight > 0 else 'neg')}={unbind:.17g}",
                f"{contribution} -> {target_sum}; "
                f"{_parameter_name('route', output_index, input_index, 'pos' if weight > 0 else 'neg')}={route_rate:.17g}",
            ]
        )

        if cfg.include_gate_fuel:
            lines.extend(
                [
                    f"{inp_gate} + {fuel} -> {inp} + {gate_fuel}; "
                    f"{_parameter_name('fuel', output_index, input_index, 'pos' if weight > 0 else 'neg')}={fuel_rate:.17g}",
                    f"{inp} + {gate_fuel} -> {inp_gate} + {fuel}; "
                    f"{_parameter_name('refuel', output_index, input_index, 'pos' if weight > 0 else 'neg')}={fuel_rate:.17g}",
                ]
            )

    lines.extend(
        [
            f"{positive_sum} + {negative_sum} -> {waste}; annihilate_o{output_index}={max(float(cfg.k_annihilate), 0.0):.17g}",
            f"{positive_sum} + {reporter_input} -> {reporter_output}; report_o{output_index}={max(float(cfg.k_output), 0.0):.17g}",
        ]
    )
    return lines, species


def _library_template_to_crn(
    weights: np.ndarray,
    input_vals: Mapping[str, float],
    config_ids: Sequence[str],
    cfg: CRNBuildConfig,
) -> tuple[list[str], set[str], dict[str, float]]:
    """Expand packaged motif templates into per-weight modules.

    A library template exposes positive and negative rails. Each input weight
    gets one independently named template instance; one rail receives the
    actual input and the opposing rail receives a zero-concentration species.
    The template reporter outputs are then routed to output-level positive and
    negative rails, which are annihilated before the shared output reporter is
    activated. This is an explicit computational composition layer, not a
    claim that the draft templates have been experimentally validated.
    """

    from crn_build_configs.registry import get_config

    lines: list[str] = []
    species: set[str] = set()
    initial: dict[str, float] = {}
    output_count = weights.shape[0]

    for output_index, row in enumerate(weights):
        positive_sum = f"{cfg.species_prefix}PosWeightedSum_o{output_index}"
        negative_sum = f"{cfg.species_prefix}NegWeightedSum_o{output_index}"
        waste = f"{cfg.species_prefix}SignedWaste_o{output_index}"
        reporter_input = _reporter_input_name(cfg, output_index, output_count)
        reporter_output = f"{cfg.species_prefix}{cfg.reporter_role}{output_index}"
        species.update({positive_sum, negative_sum, waste, reporter_input, reporter_output})
        initial.setdefault(positive_sum, 0.0)
        initial.setdefault(negative_sum, 0.0)
        initial.setdefault(waste, 0.0)
        initial[reporter_input] = float(cfg.reporter_conc)
        initial[reporter_output] = 0.0

        for input_index, raw_weight in enumerate(row):
            weight = float(raw_weight)
            if np.isclose(weight, 0.0):
                continue

            config_id = config_ids[output_index]
            motif = get_config(config_id)
            instance_id = f"o{output_index}_i{input_index}"
            actual_input = _input_name(cfg, input_index)
            zero_input = f"{cfg.species_prefix}ZeroInput_o{output_index}_i{input_index}"
            positive_contribution = f"{cfg.species_prefix}PosContribution_o{output_index}_i{input_index}"
            negative_contribution = f"{cfg.species_prefix}NegContribution_o{output_index}_i{input_index}"

            overrides: dict[str, str] = {}
            if "PosInput" in motif.species_template:
                overrides["PosInput"] = actual_input if weight > 0 else zero_input
            if "NegInput" in motif.species_template:
                overrides["NegInput"] = zero_input if weight > 0 else actual_input
            if "ActReporter" in motif.species_template:
                overrides["ActReporter"] = positive_contribution
            if "BActReporter" in motif.species_template:
                overrides["BActReporter"] = negative_contribution

            rendered = motif.rendered(instance_id=instance_id, species_overrides=overrides)
            lines.append(f"# motif instance={instance_id} config_id={config_id} weight={weight:.17g}")
            lines.append(rendered.crn_template.strip())
            species.update(rendered.species)
            initial.update(rendered.initial_conditions)
            species.update({actual_input, zero_input, positive_contribution, negative_contribution})
            initial.setdefault(actual_input, 0.0)
            initial[actual_input] = float(
                input_vals.get(actual_input, input_vals.get(f"{cfg.input_species_prefix}{input_index}", 0.0))
            ) * cfg.input_scale
            initial[zero_input] = 0.0

            # The rendered defaults include reporter pools at one unit. They
            # are contributions here, so they must begin unactivated.
            initial[positive_contribution] = 0.0
            initial[negative_contribution] = 0.0
            for role in ("positive_fuel", "negative_fuel"):
                role_species = rendered.role_map.get(role)
                if role_species is not None:
                    initial[role_species] = float(cfg.fuel_conc)

            positive_reporter = rendered.role_map.get("positive_reporter")
            if positive_reporter in rendered.species:
                lines.append(
                    f"{positive_reporter} -> {positive_sum}; "
                    f"library_pos_route_o{output_index}_i{input_index}="
                    f"{max(abs(weight) * cfg.k_output, np.finfo(float).eps):.17g}"
                )
            negative_reporter = rendered.role_map.get("negative_reporter")
            if negative_reporter in rendered.species:
                lines.append(
                    f"{negative_reporter} -> {negative_sum}; "
                    f"library_neg_route_o{output_index}_i{input_index}="
                    f"{max(abs(weight) * cfg.k_output, np.finfo(float).eps):.17g}"
                )

        lines.extend(
            [
                f"{positive_sum} + {negative_sum} -> {waste}; library_annihilate_o{output_index}={max(float(cfg.k_annihilate), 0.0):.17g}",
                f"{positive_sum} + {reporter_input} -> {reporter_output}; library_report_o{output_index}={max(float(cfg.k_output), 0.0):.17g}",
            ]
        )

    return lines, species, initial


def convert_onnx_model(
    path: str | Path,
    input_vals: Mapping[str, float],
    config: CRNBuildConfig | None = None,
    export_xml_path: str | Path | None = None,
) -> ConversionResult:
    """Convert one ONNX perceptron-style model into a CRN."""

    cfg = config or CRNBuildConfig()
    _, weights, bias = load_linear_parameters(
        path,
        weight_initializer=cfg.weight_initializer,
        bias_initializer=cfg.bias_initializer,
    )
    weights = weights * float(cfg.weight_scale)
    bias = bias + float(cfg.bias_shift)

    tree = build_network_xml(weights, bias, cfg)
    weights, bias, tree, config_ids = _apply_xpath_to_tree(weights, bias, cfg, tree)
    root = tree.getroot()
    # The XML is authoritative after XPath reassignment. Keep the effective
    # per-output configuration in CRN comments without mutating the dataclass.
    effective_ids = [
        node.find("implementation").attrib.get("config_id", cfg.config_id)
        for node in root.findall(".//neuron")
        if node.find("implementation") is not None
    ]
    if len(effective_ids) == weights.shape[0]:
        config_ids = effective_ids

    if export_xml_path:
        output_path = Path(export_xml_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        tree.write(str(output_path), encoding="utf-8", xml_declaration=True)

    lines: list[str] = []
    species: set[str] = set()
    if cfg.emit_comments:
        lines.extend(
            [
                "# Auto-generated by onnx_crn_pipeline.py",
                f"# Backend: {cfg.backend}",
                f"# model_weight_shape={weights.shape[0]}x{weights.shape[1]}",
                f"# config_ids={','.join(config_ids)}",
            ]
        )
    if cfg.backend == "library_template":
        library_lines, library_species, library_initial = _library_template_to_crn(
            weights, input_vals, config_ids, cfg
        )
        lines.extend(library_lines)
        species.update(library_species)
        species_list = sorted(species)
        init_cond = np.asarray([library_initial.get(name, 0.0) for name in species_list], dtype=float)
    elif cfg.backend == "signed_linear":
        for output_index, row in enumerate(weights):
            row_cfg = CRNBuildConfig(**{**asdict(cfg), "config_id": config_ids[output_index]})
            row_lines, row_species = linear_to_crn(
                row,
                float(bias[output_index]),
                row_cfg,
                output_index,
                weights.shape[0],
            )
            lines.extend(row_lines)
            species.update(row_species)
        species_list = sorted(species)
        init_cond = generate_initial_conditions(species_list, input_vals, cfg)
    else:
        raise ValueError(f"Unknown CRN conversion backend: {cfg.backend}")
    return ConversionResult(
        crn_code="\n".join(lines),
        species_list=species_list,
        init_cond=init_cond,
        xml_tree=tree,
        config_ids=config_ids,
        weights=weights,
        bias=bias,
    )


def onnx_to_crn_perceptron_multi_output(
    path: str | Path,
    input_vals: Mapping[str, float],
    config: CRNBuildConfig | None = None,
    export_xml_path: str | Path | None = None,
) -> tuple[str, list[str], np.ndarray]:
    """Backward-compatible three-value public entry point."""

    return convert_onnx_model(path, input_vals, config, export_xml_path).as_tuple()


def simulate_crn(
    crn_code: str,
    species_list: Sequence[str],
    init_cond: np.ndarray,
    tmax: float = 100.0,
    steps: int = 101,
) -> tuple[np.ndarray, np.ndarray]:
    """Integrate a generated CRN and return ``(times, trajectory)``."""

    if steps < 2:
        raise ValueError("steps must be at least 2")
    if tmax <= 0:
        raise ValueError("tmax must be positive")
    from crn_example import CRN

    times = np.linspace(0.0, float(tmax), int(steps))
    crn = CRN.from_string(crn_code, species=list(species_list))
    trajectory = crn.integrate(np.asarray(init_cond, dtype=float), t_eval=times)
    return times, trajectory


def instantiate_library_config(
    config_id: str,
    *,
    instance_id: str | None = None,
    species_overrides: Mapping[str, str] | None = None,
    initial_overrides: Mapping[str, float] | None = None,
):
    """Render one packaged motif template for direct inspection or testing."""

    from crn_build_configs.registry import get_config

    cfg = get_config(config_id)
    return cfg.rendered(
        instance_id=instance_id,
        species_overrides=species_overrides,
        initial_overrides=initial_overrides,
    )


__all__ = [
    "CRNBuildConfig",
    "ConversionResult",
    "IMPLEMENTED_CONFIG_ID",
    "build_network_xml",
    "config_from_dict",
    "convert_onnx_model",
    "generate_initial_conditions",
    "instantiate_library_config",
    "load_linear_parameters",
    "onnx_to_crn_perceptron_multi_output",
    "simulate_crn",
]
