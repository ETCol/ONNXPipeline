from ..base import CRNBuildConfig


CONFIG = CRNBuildConfig(
    id='toehold_exchange_cyclical',
    multiplier='toehold_exchange',
    rectifier='cyclical',
    reporter='dual_act_reporter',
    status='draft_template_unvalidated_chemistry',
    description='Buildable template-level CRN structure for toehold-exchange multiplier with cyclical rectifier. Replace/refine rates and reaction lines after motif-specific validation.',
    crn_template='\n    PosInput + PosGateOutput -> PosInputGate; tex_pos_bind=1\n    PosInputGate + PosFuel -> PosInput + PosGateFuel + PosOutput; tex_pos_release=1\n    PosInputGate -> PosInput + PosGateOutput; tex_pos_unbind=0.1\n    PosOutput -> PosWeightedSum; tex_pos_sum=100\n\n    NegInput + NegGateOutput -> NegInputGate; tex_neg_bind=1\n    NegInputGate + NegFuel -> NegInput + NegGateFuel + NegOutput; tex_neg_release=1\n    NegInputGate -> NegInput + NegGateOutput; tex_neg_unbind=0.1\n    NegOutput -> NegWeightedSum; tex_neg_sum=100\n\n\n    PosWeightedSum + CycleGate -> CycleIntermediate + FinalOutput; cyc_pos_gate=1\n    CycleIntermediate + CycleFuel -> CycleGate + CycleWaste; cyc_pos_reset=1\n    FinalOutput + Reporter -> ActReporter; cyc_pos_report=1\n    ActReporter + CycleReset -> Reporter + CycleWaste; cyc_pos_report_reset=0.1\n\n    NegWeightedSum + NegCycleGate -> NegCycleIntermediate + NegFinalOutput; cyc_neg_gate=1\n    NegCycleIntermediate + NegCycleFuel -> NegCycleGate + NegCycleWaste; cyc_neg_reset=1\n    NegFinalOutput + BReporter -> BActReporter; cyc_neg_report=1\n    BActReporter + NegCycleReset -> BReporter + NegCycleWaste; cyc_neg_report_reset=0.1\n',
    species_template=['PosInput', 'PosGateOutput', 'PosInputGate', 'PosFuel', 'PosGateFuel', 'PosOutput', 'PosWeightedSum', 'NegInput', 'NegGateOutput', 'NegInputGate', 'NegFuel', 'NegGateFuel', 'NegOutput', 'NegWeightedSum', 'CycleGate', 'CycleIntermediate', 'FinalOutput', 'CycleFuel', 'CycleWaste', 'Reporter', 'ActReporter', 'CycleReset', 'NegCycleGate', 'NegCycleIntermediate', 'NegFinalOutput', 'NegCycleFuel', 'NegCycleWaste', 'BReporter', 'BActReporter', 'NegCycleReset'],
    default_initial_conditions={'PosGateOutput': 1.0, 'PosFuel': 10.0, 'PosGateFuel': 1.0, 'NegGateOutput': 1.0, 'NegFuel': 10.0, 'NegGateFuel': 1.0, 'CycleGate': 1.0, 'CycleFuel': 1.0, 'Reporter': 1.0, 'ActReporter': 1.0, 'CycleReset': 1.0, 'NegCycleGate': 1.0, 'NegCycleFuel': 1.0, 'BReporter': 1.0, 'BActReporter': 1.0, 'NegCycleReset': 1.0},
    role_map={'positive_input': 'PosInput', 'negative_input': 'NegInput', 'positive_weight': 'PosGateOutput', 'negative_weight': 'NegGateOutput', 'positive_weighted_sum': 'PosWeightedSum', 'negative_weighted_sum': 'NegWeightedSum', 'positive_reporter': 'ActReporter', 'negative_reporter': 'BActReporter', 'positive_fuel': 'PosFuel', 'negative_fuel': 'NegFuel', 'reporter': 'Reporter', 'negative_reporter_gate': 'BReporter', 'final_output': 'FinalOutput', 'negative_final_output': 'NegFinalOutput'},
)
