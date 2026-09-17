from ..base import CRNBuildConfig


CONFIG = CRNBuildConfig(
    id='switching_gate_threshold',
    multiplier='switching_gate',
    rectifier='threshold',
    reporter='act_reporter',
    status='draft_template_unvalidated_chemistry',
    description='Buildable template-level CRN structure for switching-gate multiplier with threshold rectifier. Replace/refine rates and reaction lines after motif-specific validation.',
    crn_template='\n    PosInput + PosGateOff -> PosGateOn; sw_pos_activate=1\n    PosGateOn + PosGateOutput -> PosGateOff + PosOutput; sw_pos_output=1\n    PosGateOn + PosFuel -> PosGateOff + PosGateFuel; sw_pos_fuel=1\n    PosOutput -> PosWeightedSum; sw_pos_sum=100\n\n    NegInput + NegGateOff -> NegGateOn; sw_neg_activate=1\n    NegGateOn + NegGateOutput -> NegGateOff + NegOutput; sw_neg_output=1\n    NegGateOn + NegFuel -> NegGateOff + NegGateFuel; sw_neg_fuel=1\n    NegOutput -> NegWeightedSum; sw_neg_sum=100\n\n\n    PosWeightedSum + Threshold -> PosThresholdComplex + ThresholdWaste; th_pos_clip=1\n    PosWeightedSum + GateRestorer -> PosWeightedGate + FinalOutput; th_pos_restore=1\n    PosWeightedGate + FinalOutput -> PosWeightedSum + GateRestorer; th_pos_reverse=1\n    PosWeightedGate + BFuel -> PosWeightedSum + PosWeightedFuel; th_pos_fuel=1\n    PosWeightedSum + PosWeightedFuel -> PosWeightedGate + BFuel; th_pos_refuel=1\n    FinalOutput + Reporter -> ActReporter; th_report=1\n\n    NegWeightedSum + NegThreshold -> NegThresholdComplex + NegThresholdWaste; th_neg_clip=1\n',
    species_template=['PosInput', 'PosGateOff', 'PosGateOn', 'PosGateOutput', 'PosOutput', 'PosFuel', 'PosGateFuel', 'PosWeightedSum', 'NegInput', 'NegGateOff', 'NegGateOn', 'NegGateOutput', 'NegOutput', 'NegFuel', 'NegGateFuel', 'NegWeightedSum', 'Threshold', 'PosThresholdComplex', 'ThresholdWaste', 'GateRestorer', 'PosWeightedGate', 'FinalOutput', 'BFuel', 'PosWeightedFuel', 'Reporter', 'ActReporter', 'NegThreshold', 'NegThresholdComplex', 'NegThresholdWaste'],
    default_initial_conditions={'PosGateOff': 1.0, 'PosGateOutput': 1.0, 'PosFuel': 10.0, 'PosGateFuel': 1.0, 'NegGateOff': 1.0, 'NegGateOutput': 1.0, 'NegFuel': 10.0, 'NegGateFuel': 1.0, 'Threshold': 1.0, 'PosThresholdComplex': 1.0, 'ThresholdWaste': 1.0, 'GateRestorer': 1.0, 'BFuel': 1.0, 'PosWeightedFuel': 1.0, 'Reporter': 1.0, 'ActReporter': 1.0, 'NegThreshold': 1.0, 'NegThresholdComplex': 1.0, 'NegThresholdWaste': 1.0},
    role_map={'positive_input': 'PosInput', 'negative_input': 'NegInput', 'positive_weight': 'PosGateOutput', 'negative_weight': 'NegGateOutput', 'positive_weighted_sum': 'PosWeightedSum', 'negative_weighted_sum': 'NegWeightedSum', 'positive_reporter': 'ActReporter', 'positive_fuel': 'PosFuel', 'negative_fuel': 'NegFuel', 'threshold': 'Threshold', 'negative_threshold': 'NegThreshold', 'reporter': 'Reporter', 'final_output': 'FinalOutput'},
)
