from ..table_extension_templates import make_missing_config


CONFIG = make_missing_config(
    config_id="switching_gate_pairwise_annihilation",
    multiplier="switching_gate",
    rectifier="pairwise_annihilation",
    compatibility_status="partial",
    table_relative_error=0.0295,
    table_stable_output=True,
    table_threshold_ordering=True,
    table_note="Partial compatibility; the table result was recovered after adding an output-conversion interface before annihilation.",
)
