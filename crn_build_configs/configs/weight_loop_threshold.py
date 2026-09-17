from ..table_extension_templates import make_missing_config


CONFIG = make_missing_config(
    config_id="weight_loop_threshold",
    multiplier="weight_loop",
    rectifier="threshold",
    compatibility_status="partial",
    table_relative_error=0.0852,
    table_stable_output=True,
    table_threshold_ordering=True,
    table_note="Partial compatibility; the table result was recovered after adding an interface modification to protect the weight-restoration cycle.",
)
