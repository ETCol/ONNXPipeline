"""Reusable CRN motif fragments.

These are useful for documentation and for deriving future CRNBuildConfig files.
The complete buildable objects live in ``crn_build_configs.configs``.
"""

SEE_SAW_MULTIPLIER = """
    Input + GateOutput -> InputGate + Output; k11=1
    InputGate + Output -> Input + GateOutput; m11=1
    InputGate + Fuel -> Input + GateFuel; l11=1
    Input + GateFuel -> InputGate + Fuel; n11=1
"""

SEE_SAW_MULTIPLIER_SPECIES = [
    "Input", "GateOutput", "InputGate", "Output", "Fuel", "GateFuel"
]

DECOY_RECTIFIER = """
    Input + Threshold -> InputThreshold + ActThresh; o11=10
    InputThreshold + ActThresh -> Input + Threshold; p11=0
"""

DECOY_RECTIFIER_SPECIES = [
    "Input", "Threshold", "InputThreshold", "ActThresh"
]
