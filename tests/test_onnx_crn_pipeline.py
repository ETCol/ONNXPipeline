from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np
import onnx
from onnx import helper, numpy_helper

from crn_cli import main as cli_main
from crn_build_configs.registry import all_configs, config_ids_by_status, list_config_ids
from crn_example import CRN
from onnx_crn_pipeline import (
    CRNBuildConfig,
    convert_onnx_model,
    instantiate_library_config,
    onnx_to_crn_perceptron_multi_output,
    simulate_crn,
)


def make_model(path: Path, weights: np.ndarray, bias: np.ndarray) -> None:
    input_info = helper.make_tensor_value_info("input", onnx.TensorProto.FLOAT, [1, weights.shape[1]])
    output_info = helper.make_tensor_value_info("output", onnx.TensorProto.FLOAT, [1, weights.shape[0]])
    node = helper.make_node("Gemm", ["input", "weight", "bias"], ["output"], name="perceptron")
    graph = helper.make_graph(
        [node],
        "test_graph",
        [input_info],
        [output_info],
        [numpy_helper.from_array(weights.astype(np.float32), name="weight"), numpy_helper.from_array(bias.astype(np.float32), name="bias")],
    )
    onnx.save(helper.make_model(graph, producer_name="onnx-crn-pipeline-tests"), str(path))


class OnnxCrnPipelineTests(unittest.TestCase):
    def test_conversion_simulation_and_initial_conditions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            model_path = Path(tmp) / "model.onnx"
            make_model(model_path, np.asarray([[1.25, -0.75]]), np.asarray([0.2]))
            cfg = CRNBuildConfig(backend="signed_linear")
            result = convert_onnx_model(model_path, {"Input0": 0.8, "Input1": 0.2}, cfg)

            self.assertEqual(result.weights.shape, (1, 2))
            self.assertIn("Input0", result.species_list)
            self.assertIn("ActReporter0", result.species_list)
            self.assertEqual(len(result.init_cond), len(result.species_list))
            crn = CRN.from_string(result.crn_code, species=result.species_list)
            self.assertEqual(len(crn.parameters), 12)

            times, trajectory = simulate_crn(
                result.crn_code, result.species_list, result.init_cond, tmax=5.0, steps=6
            )
            self.assertEqual(trajectory.shape, (len(result.species_list), len(times)))
            self.assertTrue(np.isfinite(trajectory).all())

    def test_chapter3_default_entry_point_and_example_names(self) -> None:
        model_path = Path(__file__).resolve().parents[1] / "simplest_model.onnx"
        self.assertTrue(model_path.is_file())

        crn_code, species_list, init_cond = onnx_to_crn_perceptron_multi_output(
            path=model_path,
            input_vals={"Input0": 0.5, "Input1": 0.5},
        )
        self.assertIn("# Backend: library_template", crn_code)
        self.assertIn("ActReporter0", species_list)
        self.assertEqual(len(species_list), len(init_cond))

    def test_chapter3_cli_writes_complete_output_set(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "outputs"
            xml_path = Path(tmp) / "network.xml"
            exit_code = cli_main(
                [
                    "--model",
                    str(project_root / "simplest_model.onnx"),
                    "--inputs-json",
                    str(project_root / "inputs.json"),
                    "--config",
                    str(project_root / "config.json"),
                    "--no-plot",
                    "--tmax",
                    "0.5",
                    "--steps",
                    "3",
                    "--export-xml",
                    str(xml_path),
                    "--save-dir",
                    str(output_dir),
                ]
            )

            self.assertEqual(exit_code, 0)
            self.assertTrue(xml_path.is_file())
            for filename in ("crn.txt", "species.txt", "init.npy", "times.npy", "trajectory.npy", "metadata.json"):
                self.assertTrue((output_dir / filename).is_file(), filename)

            species = (output_dir / "species.txt").read_text(encoding="utf-8").splitlines()
            times = np.load(output_dir / "times.npy")
            trajectory = np.load(output_dir / "trajectory.npy")
            self.assertEqual(trajectory.shape, (len(species), len(times)))
            self.assertTrue(np.isfinite(trajectory).all())

    def test_xpath_edits_are_applied_to_xml_and_weights(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            model_path = Path(tmp) / "model.onnx"
            make_model(model_path, np.asarray([[1.25, -0.75], [0.5, 0.25]]), np.asarray([0.2, -0.1]))
            cfg = CRNBuildConfig(
                zero_weights_xpath="//weight[@input='Input1']",
                mask_neurons_xpath="//neuron[@index='0']",
                motif_reassignments=[("//neuron[@index='0']/implementation", "see_saw_pairwise_annihilation")],
            )
            result = convert_onnx_model(model_path, {"Input0": 0.5, "Input1": 0.5}, cfg)
            self.assertEqual(result.weights.shape, (1, 2))
            self.assertEqual(float(result.weights[0, 1]), 0.0)
            self.assertEqual(result.config_ids, ["see_saw_pairwise_annihilation"])
            implementation = result.xml_tree.getroot().find(".//implementation")
            assert implementation is not None
            self.assertEqual(implementation.attrib["rectifier"], "pairwise_annihilation")

    def test_library_template_backend(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            model_path = Path(tmp) / "model.onnx"
            make_model(model_path, np.asarray([[1.0, -1.0]]), np.asarray([0.0]))
            cfg = CRNBuildConfig(
                config_id="see_saw_pairwise_annihilation",
                backend="library_template",
            )
            result = convert_onnx_model(model_path, {"Input0": 0.5, "Input1": 0.25}, cfg)
            self.assertGreater(len(result.species_list), 20)
            _, trajectory = simulate_crn(
                result.crn_code, result.species_list, result.init_cond, tmax=1.0, steps=3
            )
            self.assertTrue(np.isfinite(trajectory).all())

    def test_all_library_templates_render_and_parse(self) -> None:
        for cfg in all_configs():
            rendered = instantiate_library_config(cfg.id, instance_id="test")
            crn = CRN.from_string(rendered.crn_template, species=rendered.species)
            self.assertGreater(len(crn.reactions), 0, cfg.id)

    def test_complete_plug_and_play_table_is_registered(self) -> None:
        self.assertEqual(len(list_config_ids()), 25)
        self.assertEqual(len(config_ids_by_status("direct")), 17)
        self.assertEqual(len(config_ids_by_status("partial")), 6)
        self.assertEqual(len(config_ids_by_status("incompatible")), 2)

        self.assertIn("see_saw_threshold", list_config_ids())
        self.assertIn("see_saw_cyclical", list_config_ids())
        self.assertIn("switching_gate_pairwise_annihilation", list_config_ids())
        self.assertIn("switching_gate_cyclical", list_config_ids())

        failed = [cfg for cfg in all_configs() if cfg.compatibility_status == "incompatible"]
        self.assertTrue(all(cfg.table_stable_output is False for cfg in failed))
        self.assertTrue(all(cfg.table_threshold_ordering is False for cfg in failed))


if __name__ == "__main__":
    unittest.main()
