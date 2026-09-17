from ..base import CRNBuildConfig


CONFIG = CRNBuildConfig(
    id='toehold_exchange_threshold',
    multiplier='toehold_exchange',
    rectifier='threshold',
    reporter='act_reporter',
    status='draft_template_unvalidated_chemistry',
    description='Buildable template-level CRN structure for toehold-exchange multiplier with threshold rectifier. Replace/refine rates and reaction lines after motif-specific validation.',
    crn_template='\n    PosInput + PosGateOutput -> PosInputGate; tex_pos_bind=1\n    PosInputGate + PosFuel -> PosInput + PosGateFuel + PosOutput; tex_pos_release=1\n    PosInputGate -> PosInput + PosGateOutput; tex_pos_unbind=0.1\n    PosOutput -> PosWeightedSum; tex_pos_sum=100\n\n    NegInput + NegGateOutput -> NegInputGate; tex_neg_bind=1\n    NegInputGate + NegFuel -> NegInput + NegGateFuel + NegOutput; tex_neg_release=1\n    NegInputGate -> NegInput + NegGateOutput; tex_neg_unbind=0.1\n    NegOutput -> NegWeightedSum; tex_neg_sum=100\n\n\n    PosWeightedSum + Threshold -> PosThresholdComplex + ThresholdWaste; th_pos_clip=1\n    PosWeightedSum + GateRestorer -> PosWeightedGate + FinalOutput; th_pos_restore=1\n    PosWeightedGate + FinalOutput -> PosWeightedSum + GateRestorer; th_pos_reverse=1\n    PosWeightedGate + BFuel -> PosWeightedSum + PosWeightedFuel; th_pos_fuel=1\n    PosWeightedSum + PosWeightedFuel -> PosWeightedGate + BFuel; th_pos_refuel=1\n    FinalOutput + Reporter -> ActReporter; th_report=1\n\n    NegWeightedSum + NegThreshold -> NegThresholdComplex + NegThresholdWaste; th_neg_clip=1\n',
    species_template=['PosInput', 'PosGateOutput', 'PosInputGate', 'PosFuel', 'PosGateFuel', 'PosOutput', 'PosWeightedSum', 'NegInput', 'NegGateOutput', 'NegInputGate', 'NegFuel', 'NegGateFuel', 'NegOutput', 'NegWeightedSum', 'Threshold', 'PosThresholdComplex', 'ThresholdWaste', 'GateRestorer', 'PosWeightedGate', 'FinalOutput', 'BFuel', 'PosWeightedFuel', 'Reporter', 'ActReporter', 'NegThreshold', 'NegThresholdComplex', 'NegThresholdWaste'],
    default_initial_conditions={'PosGateOutput': 1.0, 'PosFuel': 10.0, 'PosGateFuel': 1.0, 'NegGateOutput': 1.0, 'NegFuel': 10.0, 'NegGateFuel': 1.0, 'Threshold': 1.0, 'PosThresholdComplex': 1.0, 'ThresholdWaste': 1.0, 'GateRestorer': 1.0, 'BFuel': 1.0, 'PosWeightedFuel': 1.0, 'Reporter': 1.0, 'ActReporter': 1.0, 'NegThreshold': 1.0, 'NegThresholdComplex': 1.0, 'NegThresholdWaste': 1.0},
    role_map={'positive_input': 'PosInput', 'negative_input': 'NegInput', 'positive_weight': 'PosGateOutput', 'negative_weight': 'NegGateOutput', 'positive_weighted_sum': 'PosWeightedSum', 'negative_weighted_sum': 'NegWeightedSum', 'positive_reporter': 'ActReporter', 'positive_fuel': 'PosFuel', 'negative_fuel': 'NegFuel', 'threshold': 'Threshold', 'negative_threshold': 'NegThreshold', 'reporter': 'Reporter', 'final_output': 'FinalOutput'},
)
