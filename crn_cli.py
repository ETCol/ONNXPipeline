"""Command-line interface for the Chapter 3 ONNX-to-CRN pipeline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np

from onnx_crn_pipeline import CRNBuildConfig, config_from_dict, convert_onnx_model, simulate_crn


def _key_value(text: str, option: str) -> tuple[str, str]:
    if "=" not in text:
        raise argparse.ArgumentTypeError(f"{option} expects KEY=VALUE, received {text!r}")
    key, value = text.split("=", 1)
    key = key.strip()
    if not key:
        raise argparse.ArgumentTypeError(f"{option} requires a non-empty key")
    return key, value.strip()


def _numeric_key_value(text: str, option: str) -> tuple[str, float]:
    key, value = _key_value(text, option)
    try:
        return key, float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"{option} value for {key!r} must be numeric") from exc


def _coerce_override(value: str) -> Any:
    lowered = value.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if lowered in {"none", "null"}:
        return None
    try:
        if any(char in value for char in ".eE"):
            return float(value)
        return int(value)
    except ValueError:
        return value


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"JSON file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"JSON file must contain an object: {path}")
    return data


def load_inputs(path: Path | None, pairs: Sequence[str]) -> dict[str, float]:
    """Load JSON inputs and apply repeated CLI values as overrides."""

    values: dict[str, float] = {}
    if path is not None:
        raw = _read_json_object(path)
        for key, value in raw.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"Input value for {key!r} must be numeric")
            values[str(key)] = float(value)
    for text in pairs:
        key, value = _numeric_key_value(text, "--input")
        values[key] = value
    return values


def _parse_xpath_config(text: str) -> tuple[str, str]:
    key, value = _key_value(text, "--xpath-config")
    if not value:
        raise argparse.ArgumentTypeError("--xpath-config requires XPATH=CONFIG_ID")
    return key, value


def _run_xpath_query(xml_path: Path, expression: str) -> list[str]:
    try:
        from lxml import etree as LET  # type: ignore

        tree = LET.parse(str(xml_path))
        selected = tree.xpath(expression)
        result: list[str] = []
        for item in selected:
            if hasattr(item, "tag"):
                result.append(LET.tostring(item, encoding="unicode").strip())
            else:
                result.append(str(item))
        return result
    except ImportError:
        from xml.etree import ElementTree as ET

        root = ET.parse(xml_path).getroot()
        expression = "." + expression if expression.startswith("//") else expression
        return [ET.tostring(item, encoding="unicode").strip() for item in root.findall(expression)]


def _write_outputs(
    directory: Path,
    result,
    times: np.ndarray,
    trajectory: np.ndarray,
) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "crn.txt").write_text(result.crn_code + "\n", encoding="utf-8")
    (directory / "species.txt").write_text("\n".join(result.species_list) + "\n", encoding="utf-8")
    np.save(directory / "init.npy", result.init_cond)
    np.save(directory / "times.npy", times)
    np.save(directory / "trajectory.npy", trajectory)
    (directory / "metadata.json").write_text(
        json.dumps(
            {
                "config_ids": result.config_ids,
                "weights_shape": list(result.weights.shape),
                "bias": result.bias.tolist(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert a perceptron-style ONNX model into a mass-action CRN and simulate it."
    )
    parser.add_argument("-m", "--model", required=True, type=Path, help="Path to the ONNX model.")
    parser.add_argument("-j", "--inputs-json", type=Path, help="JSON object mapping input species to concentrations.")
    parser.add_argument("-i", "--input", action="append", default=[], help="Input concentration KEY=VALUE; repeatable.")
    parser.add_argument("--config", type=Path, help="JSON file containing CRNBuildConfig fields.")
    parser.add_argument("--config-id", help="Default motif-registry ID recorded in the XML.")
    parser.add_argument(
        "--xpath-config",
        action="append",
        default=[],
        metavar="XPATH=CONFIG_ID",
        help="Reassign selected XML neurons/implementations to a motif config; repeatable.",
    )
    parser.add_argument("--xpath", dest="xpath_query", help="Query the exported XML with XPath.")
    parser.add_argument("--xpath-mask", help="XPath selecting neuron nodes to keep.")
    parser.add_argument("--zero-weights-xpath", help="XPath selecting weight nodes to suppress.")
    parser.add_argument("--set", dest="overrides", action="append", default=[], metavar="KEY=VALUE", help="Override a config field.")
    parser.add_argument("--fuel-conc", type=float, help="Initial concentration of ordinary fuel species.")
    parser.add_argument("--tmax", type=float, default=100.0, help="Simulation end time (default: 100).")
    parser.add_argument("--steps", type=int, default=101, help="Number of simulation samples (default: 101).")
    parser.add_argument("--plot", dest="plot", action="store_true", help="Plot reporter trajectories (default).")
    parser.add_argument("--no-plot", dest="plot", action="store_false", help="Do not display a plot.")
    parser.set_defaults(plot=True)
    parser.add_argument("--export-xml", type=Path, help="Write the intermediate XML representation to this path.")
    parser.add_argument("--save-dir", type=Path, help="Save CRN, species, initial conditions, and trajectory here.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        input_values = load_inputs(args.inputs_json, args.input)
        if not input_values:
            parser.error("no input concentrations supplied; use --inputs-json or --input Input0=VALUE")

        config_values: dict[str, Any] = {}
        if args.config is not None:
            config_values.update(_read_json_object(args.config))
        for override in args.overrides:
            key, value = _key_value(override, "--set")
            config_values[key] = _coerce_override(value)
        if args.config_id is not None:
            config_values["config_id"] = args.config_id
        if args.xpath_mask is not None:
            config_values["mask_neurons_xpath"] = args.xpath_mask
        if args.zero_weights_xpath is not None:
            config_values["zero_weights_xpath"] = args.zero_weights_xpath
        if args.fuel_conc is not None:
            config_values["fuel_conc"] = args.fuel_conc

        assignments = list(config_values.get("motif_reassignments", []) or [])
        assignments.extend(_parse_xpath_config(item) for item in args.xpath_config)
        config_values["motif_reassignments"] = assignments
        config = config_from_dict(config_values)

        if args.steps < 2:
            parser.error("--steps must be at least 2")
        if args.tmax <= 0:
            parser.error("--tmax must be positive")

        print(f"Loading model: {args.model}")
        result = convert_onnx_model(args.model, input_values, config, args.export_xml)
        print(f"Generated CRN with {len(result.species_list)} species and {len([line for line in result.crn_code.splitlines() if '->' in line])} reactions.")

        times, trajectory = simulate_crn(
            result.crn_code,
            result.species_list,
            result.init_cond,
            tmax=args.tmax,
            steps=args.steps,
        )

        if args.xpath_query:
            if args.export_xml is None:
                parser.error("--xpath requires --export-xml PATH")
            matches = _run_xpath_query(args.export_xml, args.xpath_query)
            for index, match in enumerate(matches, start=1):
                print(f"[{index}] {match}")
            if not matches:
                print("(no matches)")

        if args.save_dir is not None:
            _write_outputs(args.save_dir, result, times, trajectory)
            print(f"Saved outputs to: {args.save_dir}")

        if args.plot:
            import matplotlib.pyplot as plt

            reporter_indices = [
                index
                for index, name in enumerate(result.species_list)
                if name.startswith(config.species_prefix + config.reporter_role)
            ]
            if reporter_indices:
                for index in reporter_indices:
                    plt.plot(times, trajectory[index], label=result.species_list[index])
                plt.xlabel("Time")
                plt.ylabel("Concentration")
                plt.title("Activated reporter trajectories")
                plt.grid(True)
                plt.legend()
                plt.tight_layout()
                plt.show()
            else:
                print("No activated reporter species found to plot.")
        return 0
    except (FileNotFoundError, ValueError, OSError, RuntimeError) as exc:
        parser.error(str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
