from ..table_extension_templates import make_missing_config


CONFIG = make_missing_config(
    config_id="see_saw_cyclical",
    multiplier="see_saw",
    rectifier="cyclical",
    compatibility_status="incompatible",
    table_relative_error=0.8031,
    table_stable_output=False,
    table_threshold_ordering=False,
    table_note="Incompatible under the tested assumptions; direct composition failed to stabilise and preserve threshold ordering.",
)
