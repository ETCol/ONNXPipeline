from ..table_extension_templates import make_missing_config


CONFIG = make_missing_config(
    config_id="switching_gate_cyclical",
    multiplier="switching_gate",
    rectifier="cyclical",
    compatibility_status="incompatible",
    table_relative_error=0.9470,
    table_stable_output=False,
    table_threshold_ordering=False,
    table_note="Incompatible under the tested assumptions; direct composition failed to stabilise and preserve threshold ordering.",
)
