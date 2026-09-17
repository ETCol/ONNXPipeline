"""Buildable CRN templates for non-direct table assignments.

The Chapter 2 table contains 25 multiplier--rectifier pairings.  The first
17 direct pairings have dedicated modules in ``configs/``.  This module
provides the remaining six partial and two incompatible entries so that the
whole table is representable as a :class:`CRNBuildConfig`.

These are deliberately labelled as draft compatibility templates.  Partial
entries include explicit adapter/restoration species, while incompatible
entries retain direct composition so that the reported failure mode remains
visible rather than being silently converted into a successful design.
"""

from __future__ import annotations

from .base import CRNBuildConfig


def _multiplier_fragment(multiplier: str) -> tuple[str, list[str], dict[str, float], dict[str, str]]:
    """Return a two-rail multiplier fragment and its metadata."""

    if multiplier == "see_saw":
        lines = [
            "PosInput + PosGateOutput -> PosInputGate + PosOutput; ss_pos_bind=1",
            "PosInputGate + PosOutput -> PosInput + PosGateOutput; ss_pos_unbind=1",
            "PosInputGate + PosFuel -> PosInput + PosGateFuel; ss_pos_fuel=1",
            "PosInput + PosGateFuel -> PosInputGate + PosFuel; ss_pos_restore=1",
            "PosOutput -> PosWeightedSum; ss_pos_sum=100",
            "NegInput + NegGateOutput -> NegInputGate + NegOutput; ss_neg_bind=1",
            "NegInputGate + NegOutput -> NegInput + NegGateOutput; ss_neg_unbind=1",
            "NegInputGate + NegFuel -> NegInput + NegGateFuel; ss_neg_fuel=1",
            "NegInput + NegGateFuel -> NegInputGate + NegFuel; ss_neg_restore=1",
            "NegOutput -> NegWeightedSum; ss_neg_sum=100",
        ]
        species = [
            "PosInput", "PosGateOutput", "PosInputGate", "PosOutput", "PosFuel",
            "PosGateFuel", "PosWeightedSum", "NegInput", "NegGateOutput",
            "NegInputGate", "NegOutput", "NegFuel", "NegGateFuel", "NegWeightedSum",
        ]
        initial = {
            "PosGateOutput": 1.0, "PosFuel": 10.0, "PosGateFuel": 1.0,
            "NegGateOutput": 1.0, "NegFuel": 10.0, "NegGateFuel": 1.0,
        }
    elif multiplier == "weight_loop":
        lines = [
            "PosInput + PosLoopGate -> PosLoopComplex; wl_pos_bind=1",
            "PosLoopComplex + PosGateOutput -> PosInput + PosLoopGate + PosOutput; wl_pos_output=1",
            "PosLoopComplex + PosFuel -> PosInput + PosLoopFuel; wl_pos_fuel=1",
            "PosLoopFuel -> PosLoopGate; wl_pos_reset=1",
            "PosOutput -> PosWeightedSum; wl_pos_sum=100",
            "NegInput + NegLoopGate -> NegLoopComplex; wl_neg_bind=1",
            "NegLoopComplex + NegGateOutput -> NegInput + NegLoopGate + NegOutput; wl_neg_output=1",
            "NegLoopComplex + NegFuel -> NegInput + NegLoopFuel; wl_neg_fuel=1",
            "NegLoopFuel -> NegLoopGate; wl_neg_reset=1",
            "NegOutput -> NegWeightedSum; wl_neg_sum=100",
        ]
        species = [
            "PosInput", "PosLoopGate", "PosLoopComplex", "PosGateOutput", "PosOutput",
            "PosFuel", "PosLoopFuel", "PosWeightedSum", "NegInput", "NegLoopGate",
            "NegLoopComplex", "NegGateOutput", "NegOutput", "NegFuel", "NegLoopFuel",
            "NegWeightedSum",
        ]
        initial = {
            "PosLoopGate": 1.0, "PosGateOutput": 1.0, "PosFuel": 10.0,
            "PosLoopFuel": 1.0, "NegLoopGate": 1.0, "NegGateOutput": 1.0,
            "NegFuel": 10.0, "NegLoopFuel": 1.0,
        }
    elif multiplier == "weight_race":
        lines = [
            "PosInput + PosRaceGate -> PosRaceComplex; wr_pos_bind=1",
            "PosRaceComplex + PosGateOutput -> PosRaceGate + PosOutput; wr_pos_win=1",
            "PosRaceComplex + PosFuel -> PosInput + PosRaceFuel; wr_pos_fuel=1",
            "PosRaceFuel -> PosRaceGate; wr_pos_reset=1",
            "PosOutput -> PosWeightedSum; wr_pos_sum=100",
            "NegInput + NegRaceGate -> NegRaceComplex; wr_neg_bind=1",
            "NegRaceComplex + NegGateOutput -> NegRaceGate + NegOutput; wr_neg_win=1",
            "NegRaceComplex + NegFuel -> NegInput + NegRaceFuel; wr_neg_fuel=1",
            "NegRaceFuel -> NegRaceGate; wr_neg_reset=1",
            "NegOutput -> NegWeightedSum; wr_neg_sum=100",
        ]
        species = [
            "PosInput", "PosRaceGate", "PosRaceComplex", "PosGateOutput", "PosOutput",
            "PosFuel", "PosRaceFuel", "PosWeightedSum", "NegInput", "NegRaceGate",
            "NegRaceComplex", "NegGateOutput", "NegOutput", "NegFuel", "NegRaceFuel",
            "NegWeightedSum",
        ]
        initial = {
            "PosRaceGate": 1.0, "PosGateOutput": 1.0, "PosFuel": 10.0,
            "PosRaceFuel": 1.0, "NegRaceGate": 1.0, "NegGateOutput": 1.0,
            "NegFuel": 10.0, "NegRaceFuel": 1.0,
        }
    elif multiplier == "switching_gate":
        lines = [
            "PosInput + PosGateOff -> PosGateOn; sw_pos_activate=1",
            "PosGateOn + PosGateOutput -> PosGateOff + PosOutput; sw_pos_output=1",
            "PosGateOn + PosFuel -> PosGateOff + PosGateFuel; sw_pos_fuel=1",
            "PosOutput -> PosWeightedSum; sw_pos_sum=100",
            "NegInput + NegGateOff -> NegGateOn; sw_neg_activate=1",
            "NegGateOn + NegGateOutput -> NegGateOff + NegOutput; sw_neg_output=1",
            "NegGateOn + NegFuel -> NegGateOff + NegGateFuel; sw_neg_fuel=1",
            "NegOutput -> NegWeightedSum; sw_neg_sum=100",
        ]
        species = [
            "PosInput", "PosGateOff", "PosGateOn", "PosGateOutput", "PosOutput",
            "PosFuel", "PosGateFuel", "PosWeightedSum", "NegInput", "NegGateOff",
            "NegGateOn", "NegGateOutput", "NegOutput", "NegFuel", "NegGateFuel",
            "NegWeightedSum",
        ]
        initial = {
            "PosGateOff": 1.0, "PosGateOutput": 1.0, "PosFuel": 10.0,
            "PosGateFuel": 1.0, "NegGateOff": 1.0, "NegGateOutput": 1.0,
            "NegFuel": 10.0, "NegGateFuel": 1.0,
        }
    else:
        raise ValueError(f"unsupported multiplier template: {multiplier}")

    roles = {
        "positive_input": "PosInput",
        "negative_input": "NegInput",
        "positive_weight": "PosGateOutput",
        "negative_weight": "NegGateOutput",
        "positive_weighted_sum": "PosWeightedSum",
        "negative_weighted_sum": "NegWeightedSum",
    }
    return "\n".join(lines), species, initial, roles


def _threshold_fragment() -> tuple[str, list[str], dict[str, float], dict[str, str]]:
    """Threshold rectifier with an explicit signal-transfer adapter."""

    lines = [
        "PosWeightedSum -> PosThresholdSignal; ad_pos_collect=1",
        "PosThresholdSignal + Threshold -> PosThresholdComplex + ThresholdWaste; th_pos_clip=1",
        "PosThresholdComplex -> PosThresholdSignal + Threshold; th_pos_release=0.1",
        "PosThresholdSignal + GateRestorer -> PosWeightedGate + FinalOutput; th_pos_restore=1",
        "PosWeightedGate + FinalOutput -> PosThresholdSignal + GateRestorer; th_pos_reverse=1",
        "PosWeightedGate + BFuel -> PosThresholdSignal + PosWeightedFuel; th_pos_fuel=1",
        "PosThresholdSignal + PosWeightedFuel -> PosWeightedGate + BFuel; th_pos_refuel=1",
        "FinalOutput + Reporter -> ActReporter; th_pos_report=1",
        "NegWeightedSum -> NegThresholdSignal; ad_neg_collect=1",
        "NegThresholdSignal + NegThreshold -> NegThresholdComplex + NegThresholdWaste; th_neg_clip=1",
        "NegThresholdComplex -> NegThresholdSignal + NegThreshold; th_neg_release=0.1",
        "NegThresholdSignal + CGateRestorer -> NegWeightedGate + NegFinalOutput; th_neg_restore=1",
        "NegWeightedGate + NegFinalOutput -> NegThresholdSignal + CGateRestorer; th_neg_reverse=1",
        "NegWeightedGate + CFuel -> NegThresholdSignal + NegWeightedFuel; th_neg_fuel=1",
        "NegThresholdSignal + NegWeightedFuel -> NegWeightedGate + CFuel; th_neg_refuel=1",
        "NegFinalOutput + BReporter -> BActReporter; th_neg_report=1",
    ]
    species = [
        "PosThresholdSignal", "Threshold", "PosThresholdComplex", "ThresholdWaste",
        "GateRestorer", "PosWeightedGate", "FinalOutput", "BFuel", "PosWeightedFuel",
        "Reporter", "ActReporter", "NegThresholdSignal", "NegThreshold",
        "NegThresholdComplex", "NegThresholdWaste", "CGateRestorer", "NegWeightedGate",
        "NegFinalOutput", "CFuel", "NegWeightedFuel", "BReporter", "BActReporter",
    ]
    initial = {
        "Threshold": 1.0, "PosThresholdComplex": 1.0, "ThresholdWaste": 1.0,
        "GateRestorer": 1.0, "BFuel": 1.0, "PosWeightedFuel": 1.0,
        "Reporter": 1.0, "ActReporter": 1.0, "NegThreshold": 1.0,
        "NegThresholdComplex": 1.0, "NegThresholdWaste": 1.0,
        "CGateRestorer": 1.0, "CFuel": 1.0, "NegWeightedFuel": 1.0,
        "BReporter": 1.0, "BActReporter": 1.0,
    }
    roles = {
        "positive_reporter": "ActReporter",
        "negative_reporter": "BActReporter",
        "threshold": "Threshold",
        "negative_threshold": "NegThreshold",
        "reporter": "Reporter",
        "final_output": "FinalOutput",
        "negative_final_output": "NegFinalOutput",
    }
    return "\n".join(lines), species, initial, roles


def _cyclical_fragment(*, adapter: bool) -> tuple[str, list[str], dict[str, float], dict[str, str]]:
    """Cyclical rectifier, optionally preceded by a signal adapter."""

    pos_signal = "PosCycleSignal" if adapter else "PosWeightedSum"
    neg_signal = "NegCycleSignal" if adapter else "NegWeightedSum"
    lines = []
    if adapter:
        lines.extend([
            "PosWeightedSum -> PosCycleSignal; cyc_pos_adapter=1",
            "NegWeightedSum -> NegCycleSignal; cyc_neg_adapter=1",
        ])
    lines.extend([
        f"{pos_signal} + PosCycleGate -> PosCycleOn; cyc_pos_start=1",
        f"PosCycleOn -> PosCycleOff + {pos_signal}; cyc_pos_release=0.1",
        "PosCycleOff + PosCycleFuel -> PosCycleGate; cyc_pos_restore=1",
        "PosCycleGate -> PosCycleOff; cyc_pos_leak=0.01",
        "PosCycleOn + Reporter -> ActReporter; cyc_pos_report=1",
        f"{neg_signal} + NegCycleGate -> NegCycleOn; cyc_neg_start=1",
        f"NegCycleOn -> NegCycleOff + {neg_signal}; cyc_neg_release=0.1",
        "NegCycleOff + NegCycleFuel -> NegCycleGate; cyc_neg_restore=1",
        "NegCycleGate -> NegCycleOff; cyc_neg_leak=0.01",
        "NegCycleOn + BReporter -> BActReporter; cyc_neg_report=1",
    ])
    species = [
        "PosCycleGate", "PosCycleOn", "PosCycleOff", "PosCycleFuel",
        "NegCycleGate", "NegCycleOn", "NegCycleOff", "NegCycleFuel",
        "Reporter", "ActReporter", "BReporter", "BActReporter",
    ]
    if adapter:
        species.extend(["PosCycleSignal", "NegCycleSignal"])
    initial = {
        "PosCycleGate": 1.0, "PosCycleFuel": 1.0, "NegCycleGate": 1.0,
        "NegCycleFuel": 1.0, "Reporter": 1.0, "ActReporter": 1.0,
        "BReporter": 1.0, "BActReporter": 1.0,
    }
    roles = {
        "positive_reporter": "ActReporter",
        "negative_reporter": "BActReporter",
        "reporter": "Reporter",
    }
    return "\n".join(lines), species, initial, roles


def _pairwise_fragment(*, adapter: bool) -> tuple[str, list[str], dict[str, float], dict[str, str]]:
    """Pairwise-annihilation rectifier, optionally with an output adapter."""

    pos_signal = "PosPairSignal" if adapter else "PosWeightedSum"
    neg_signal = "NegPairSignal" if adapter else "NegWeightedSum"
    lines = []
    if adapter:
        lines.extend([
            "PosWeightedSum -> PosPairSignal; ad_pair_pos=1",
            "NegWeightedSum -> NegPairSignal; ad_pair_neg=1",
        ])
    lines.extend([
        f"{pos_signal} + PWAnnihilator -> PosAnnihilator; pwa_pos_bind=100",
        f"PosAnnihilator -> {pos_signal} + PWAnnihilator; pwa_pos_reverse=100",
        f"PosAnnihilator + {neg_signal} -> PosWaste + NegWaste; pwa_annihilate=100",
        f"{pos_signal} + GateRestorer -> PosWeightedGate + FinalOutput; pwa_pos_restore=1",
        f"PosWeightedGate + FinalOutput -> {pos_signal} + GateRestorer; pwa_pos_reverse_gate=1",
        f"PosWeightedGate + BFuel -> {pos_signal} + PosWeightedFuel; pwa_pos_fuel=1",
        f"{pos_signal} + PosWeightedFuel -> PosWeightedGate + BFuel; pwa_pos_refuel=1",
        f"{neg_signal} + CGateRestorer -> NegWeightedGate + NegFinalOutput; pwa_neg_restore=1",
        f"NegWeightedGate + NegFinalOutput -> {neg_signal} + CGateRestorer; pwa_neg_reverse_gate=1",
        f"NegWeightedGate + CFuel -> {neg_signal} + NegWeightedFuel; pwa_neg_fuel=1",
        f"{neg_signal} + NegWeightedFuel -> NegWeightedGate + CFuel; pwa_neg_refuel=1",
        "FinalOutput + Reporter -> ActReporter; pwa_pos_report=1",
        "NegFinalOutput + BReporter -> BActReporter; pwa_neg_report=1",
    ])
    species = [
        "PWAnnihilator", "PosAnnihilator", "PosWaste", "NegWaste", "GateRestorer",
        "PosWeightedGate", "FinalOutput", "BFuel", "PosWeightedFuel", "CGateRestorer",
        "NegWeightedGate", "NegFinalOutput", "CFuel", "NegWeightedFuel", "Reporter",
        "ActReporter", "BReporter", "BActReporter",
    ]
    if adapter:
        species.extend(["PosPairSignal", "NegPairSignal"])
    initial = {
        "PWAnnihilator": 1.0, "GateRestorer": 1.0, "BFuel": 1.0,
        "PosWeightedFuel": 1.0, "CGateRestorer": 1.0, "CFuel": 1.0,
        "NegWeightedFuel": 1.0, "Reporter": 1.0, "ActReporter": 1.0,
        "BReporter": 1.0, "BActReporter": 1.0,
    }
    roles = {
        "positive_reporter": "ActReporter",
        "negative_reporter": "BActReporter",
        "annihilator": "PWAnnihilator",
        "reporter": "Reporter",
        "final_output": "FinalOutput",
        "negative_final_output": "NegFinalOutput",
    }
    return "\n".join(lines), species, initial, roles


def make_missing_config(
    *,
    config_id: str,
    multiplier: str,
    rectifier: str,
    compatibility_status: str,
    table_relative_error: float,
    table_stable_output: bool,
    table_threshold_ordering: bool,
    table_note: str,
) -> CRNBuildConfig:
    """Construct one of the eight non-direct Chapter 2 table entries."""

    multiplier_text, multiplier_species, multiplier_initial, multiplier_roles = _multiplier_fragment(multiplier)

    if rectifier == "threshold":
        rectifier_text, rectifier_species, rectifier_initial, rectifier_roles = _threshold_fragment()
        reporter = "act_reporter"
    elif rectifier == "cyclical":
        rectifier_text, rectifier_species, rectifier_initial, rectifier_roles = _cyclical_fragment(
            adapter=compatibility_status == "partial"
        )
        reporter = "dual_act_reporter"
    elif rectifier == "pairwise_annihilation":
        rectifier_text, rectifier_species, rectifier_initial, rectifier_roles = _pairwise_fragment(
            adapter=compatibility_status == "partial"
        )
        reporter = "dual_act_reporter"
    else:
        raise ValueError(f"unsupported missing rectifier template: {rectifier}")

    species = list(multiplier_species)
    for name in rectifier_species:
        if name not in species:
            species.append(name)
    initial: dict[str, float] = dict(multiplier_initial)
    initial.update(rectifier_initial)
    roles: dict[str, str] = dict(multiplier_roles)
    roles.update(rectifier_roles)

    status = (
        "draft_template_partial_compatibility"
        if compatibility_status == "partial"
        else "draft_template_incompatible_under_tested_assumptions"
    )
    description = (
        f"Buildable template-level CRN for {multiplier} multiplier with {rectifier} rectifier. "
        f"Table assignment: {compatibility_status}; {table_note}"
    )
    return CRNBuildConfig(
        id=config_id,
        multiplier=multiplier,
        rectifier=rectifier,
        reporter=reporter,
        crn_template=f"{multiplier_text}\n\n{rectifier_text}\n",
        species_template=species,
        default_initial_conditions=initial,
        role_map=roles,
        status=status,
        description=description,
        compatibility_status=compatibility_status,
        table_relative_error=table_relative_error,
        table_stable_output=table_stable_output,
        table_threshold_ordering=table_threshold_ordering,
        table_note=table_note,
    )
