"""Optional comparison of digital ONNX outputs and generated CRN reporters.

Install ``onnxruntime`` from ``requirements-optional.txt`` before using this
script. Input rows are JSON objects in JSONL format with keys ``Input0``,
``Input1``, and so on.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

import numpy as np

from onnx_crn_pipeline import CRNBuildConfig, convert_onnx_model, simulate_crn


def load_jsonl(path: Path) -> list[dict[str, float]]:
    rows: list[dict[str, float]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON on line {line_number}: {exc}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"Line {line_number} must contain a JSON object")
        rows.append({str(key): float(number) for key, number in value.items()})
    return rows


def infer_onnx(session, inputs: dict[str, float]) -> np.ndarray:
    metadata = session.get_inputs()
    if len(metadata) != 1:
        raise ValueError(f"Expected one ONNX graph input, found {len(metadata)}")
    input_metadata = metadata[0]
    shape = input_metadata.shape
    try:
        feature_count = int(shape[-1])
    except (TypeError, ValueError):
        feature_count = max(
            [int(key.removeprefix("Input")) for key in inputs if key.startswith("Input")] or [-1]
        ) + 1
    if feature_count <= 0:
        raise ValueError("Could not infer the ONNX feature count")
    vector = np.asarray(
        [[float(inputs.get(f"Input{index}", 0.0)) for index in range(feature_count)]],
        dtype=np.float32,
    )
    outputs = session.run(None, {input_metadata.name: vector})
    return np.concatenate([np.asarray(output).reshape(-1) for output in outputs])


def reporter_output(result, trajectory: np.ndarray) -> np.ndarray:
    indices = [
        index
        for index, name in enumerate(result.species_list)
        if name.startswith("ActReporter")
    ]
    if not indices:
        raise ValueError("Generated CRN contains no ActReporter species")
    names = [result.species_list[index] for index in indices]
    order = np.argsort([int(name.removeprefix("ActReporter")) for name in names])
    return np.asarray([trajectory[indices[index], -1] for index in order], dtype=float)


def affine_calibration(y_true: np.ndarray, y_raw: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    scales = np.zeros(y_true.shape[1], dtype=float)
    offsets = np.zeros(y_true.shape[1], dtype=float)
    for output_index in range(y_true.shape[1]):
        design = np.column_stack([y_raw[:, output_index], np.ones(y_raw.shape[0])])
        scales[output_index], offsets[output_index] = np.linalg.lstsq(
            design, y_true[:, output_index], rcond=None
        )[0]
    return scales, offsets


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--inputs", type=Path, required=True, help="JSONL file of Input* rows")
    parser.add_argument("--fuel-conc", type=float, default=10.0)
    parser.add_argument("--tmax", type=float, default=100.0)
    parser.add_argument("--steps", type=int, default=101)
    parser.add_argument("--backend", choices=["signed_linear", "library_template"], default="library_template")
    parser.add_argument("--config-id", default="toehold_exchange_threshold")
    parser.add_argument("--calib-frac", type=float, default=0.3)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args(argv)

    try:
        import onnxruntime as ort
    except ImportError as exc:
        parser.error("onnxruntime is required; install requirements-optional.txt")
        raise exc

    rows = load_jsonl(args.inputs)
    if len(rows) < 2:
        parser.error("at least two JSONL input rows are required")

    session = ort.InferenceSession(str(args.model), providers=["CPUExecutionProvider"])
    config = CRNBuildConfig(
        fuel_conc=args.fuel_conc,
        backend=args.backend,
        config_id=args.config_id,
    )
    y_onnx: list[np.ndarray] = []
    y_crn: list[np.ndarray] = []
    for inputs in rows:
        y_onnx.append(infer_onnx(session, inputs))
        result = convert_onnx_model(args.model, inputs, config)
        _, trajectory = simulate_crn(
            result.crn_code,
            result.species_list,
            result.init_cond,
            tmax=args.tmax,
            steps=args.steps,
        )
        y_crn.append(reporter_output(result, trajectory))

    digital = np.vstack(y_onnx)
    chemical = np.vstack(y_crn)
    rng = np.random.default_rng(args.seed)
    order = rng.permutation(len(rows))
    calibration_count = max(1, min(len(rows) - 1, int(round(args.calib_frac * len(rows)))))
    calibration = order[:calibration_count]
    evaluation = order[calibration_count:]
    scales, offsets = affine_calibration(digital[calibration], chemical[calibration])
    calibrated = chemical * scales + offsets

    def mae(left, right):
        return float(np.mean(np.abs(left - right)))

    def rmse(left, right):
        return float(np.sqrt(np.mean((left - right) ** 2)))

    print(f"samples={len(rows)} calibration={len(calibration)} evaluation={len(evaluation)}")
    print("raw_mae=", mae(digital[evaluation], chemical[evaluation]))
    print("raw_rmse=", rmse(digital[evaluation], chemical[evaluation]))
    print("calibrated_mae=", mae(digital[evaluation], calibrated[evaluation]))
    print("calibrated_rmse=", rmse(digital[evaluation], calibrated[evaluation]))
    print("calibration_scales=", scales)
    print("calibration_offsets=", offsets)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
