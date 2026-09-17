from __future__ import annotations

from importlib import import_module
from typing import Iterable

from .base import CRNBuildConfig


COMPATIBILITY: dict[str, list[str]] = {'toehold_exchange': ['threshold', 'decoy', 'cyclical', 'weighted_subtraction', 'pairwise_annihilation'], 'see_saw': ['decoy', 'weighted_subtraction', 'pairwise_annihilation'], 'weight_loop': ['decoy', 'weighted_subtraction', 'pairwise_annihilation'], 'weight_race': ['decoy', 'weighted_subtraction', 'pairwise_annihilation'], 'switching_gate': ['threshold', 'decoy', 'weighted_subtraction']}

# The direct-compatible entries above are the 17 ``checkmark`` rows.  These
# assignments preserve the complete 25-row Chapter 2 table, including the
# six interface-modified rows and the two failed rows.
TABLE_ASSIGNMENTS: dict[tuple[str, str], str] = {
    ("toehold_exchange", "threshold"): "direct",
    ("toehold_exchange", "decoy"): "direct",
    ("toehold_exchange", "cyclical"): "direct",
    ("toehold_exchange", "weighted_subtraction"): "direct",
    ("toehold_exchange", "pairwise_annihilation"): "direct",
    ("see_saw", "threshold"): "partial",
    ("see_saw", "decoy"): "direct",
    ("see_saw", "cyclical"): "incompatible",
    ("see_saw", "weighted_subtraction"): "direct",
    ("see_saw", "pairwise_annihilation"): "direct",
    ("weight_loop", "threshold"): "partial",
    ("weight_loop", "decoy"): "direct",
    ("weight_loop", "cyclical"): "partial",
    ("weight_loop", "weighted_subtraction"): "direct",
    ("weight_loop", "pairwise_annihilation"): "direct",
    ("weight_race", "threshold"): "partial",
    ("weight_race", "decoy"): "direct",
    ("weight_race", "cyclical"): "partial",
    ("weight_race", "weighted_subtraction"): "direct",
    ("weight_race", "pairwise_annihilation"): "direct",
    ("switching_gate", "threshold"): "direct",
    ("switching_gate", "decoy"): "direct",
    ("switching_gate", "cyclical"): "incompatible",
    ("switching_gate", "weighted_subtraction"): "direct",
    ("switching_gate", "pairwise_annihilation"): "partial",
}

CONFIG_MODULES: dict[str, str] = {
    'toehold_exchange_threshold': 'crn_build_configs.configs.toehold_exchange_threshold',
    'toehold_exchange_decoy': 'crn_build_configs.configs.toehold_exchange_decoy',
    'toehold_exchange_cyclical': 'crn_build_configs.configs.toehold_exchange_cyclical',
    'toehold_exchange_weighted_subtraction': 'crn_build_configs.configs.toehold_exchange_weighted_subtraction',
    'toehold_exchange_pairwise_annihilation': 'crn_build_configs.configs.toehold_exchange_pairwise_annihilation',
    'see_saw_decoy': 'crn_build_configs.configs.see_saw_decoy',
    'see_saw_threshold': 'crn_build_configs.configs.see_saw_threshold',
    'see_saw_cyclical': 'crn_build_configs.configs.see_saw_cyclical',
    'see_saw_weighted_subtraction': 'crn_build_configs.configs.see_saw_weighted_subtraction',
    'see_saw_pairwise_annihilation': 'crn_build_configs.configs.see_saw_pairwise_annihilation',
    'weight_loop_threshold': 'crn_build_configs.configs.weight_loop_threshold',
    'weight_loop_decoy': 'crn_build_configs.configs.weight_loop_decoy',
    'weight_loop_cyclical': 'crn_build_configs.configs.weight_loop_cyclical',
    'weight_loop_weighted_subtraction': 'crn_build_configs.configs.weight_loop_weighted_subtraction',
    'weight_loop_pairwise_annihilation': 'crn_build_configs.configs.weight_loop_pairwise_annihilation',
    'weight_race_threshold': 'crn_build_configs.configs.weight_race_threshold',
    'weight_race_decoy': 'crn_build_configs.configs.weight_race_decoy',
    'weight_race_cyclical': 'crn_build_configs.configs.weight_race_cyclical',
    'weight_race_weighted_subtraction': 'crn_build_configs.configs.weight_race_weighted_subtraction',
    'weight_race_pairwise_annihilation': 'crn_build_configs.configs.weight_race_pairwise_annihilation',
    'switching_gate_threshold': 'crn_build_configs.configs.switching_gate_threshold',
    'switching_gate_decoy': 'crn_build_configs.configs.switching_gate_decoy',
    'switching_gate_cyclical': 'crn_build_configs.configs.switching_gate_cyclical',
    'switching_gate_weighted_subtraction': 'crn_build_configs.configs.switching_gate_weighted_subtraction',
    'switching_gate_pairwise_annihilation': 'crn_build_configs.configs.switching_gate_pairwise_annihilation',
}


def list_config_ids() -> list[str]:
    return list(CONFIG_MODULES)


def get_config(config_id: str) -> CRNBuildConfig:
    try:
        module_name = CONFIG_MODULES[config_id]
    except KeyError as exc:
        valid = ', '.join(CONFIG_MODULES)
        raise KeyError(f"Unknown CRNBuildConfig {config_id!r}. Valid ids: {valid}") from exc
    module = import_module(module_name)
    return module.CONFIG


def all_configs() -> list[CRNBuildConfig]:
    return [get_config(config_id) for config_id in list_config_ids()]


def config_ids_by_status(status: str) -> list[str]:
    """Return registry IDs with a direct, partial, or failed table assignment."""

    return [
        config_id
        for config_id in list_config_ids()
        if get_config(config_id).compatibility_status == status
    ]


def compatible_config_ids(multiplier: str | None = None, rectifier: str | None = None) -> list[str]:
    ids = []
    for config_id in CONFIG_MODULES:
        cfg = get_config(config_id)
        if multiplier is not None and cfg.multiplier != multiplier:
            continue
        if rectifier is not None and cfg.rectifier != rectifier:
            continue
        ids.append(config_id)
    return ids
