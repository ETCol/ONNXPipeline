from ..table_extension_templates import make_missing_config


CONFIG = make_missing_config(
    config_id="weight_race_threshold",
    multiplier="weight_race",
    rectifier="threshold",
    compatibility_status="partial",
    table_relative_error=0.0492,
    table_stable_output=True,
    table_threshold_ordering=True,
    table_note="Partial compatibility; the table result was recovered after collecting the rate-based winner through an interface species before thresholding.",
)
