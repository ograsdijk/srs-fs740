from .config_enums import SourceChannel


def validate_parameter_string_min_max_def_inf(parameter: str) -> str:
    """
    Validates and normalizes a parameter specification string.

    The allowed parameter specification must be one of the following keywords
    (case-insensitive):
            "minimum" / "min"   -> normalized to "MIN"
            "maximum" / "max"   -> normalized to "MAX"
            "default" / "def"   -> normalized to "DEF"
            "infinity" / "inf"  -> normalized to "INF"

    If the normalized (stripped and casefolded) string is not numeric and does not match any
    of the allowed keywords, a ValueError is raised.

    Args:
        parameter (str): The parameter specification string.

    Returns:
        str: The normalized parameter string

    Raises:
        ValueError: If parameter is not in the allowed set.
    """
    allowed = {
        "min": "MIN",
        "minimum": "MIN",
        "max": "MAX",
        "maximum": "MAX",
        "def": "DEF",
        "default": "DEF",
        "inf": "INF",
        "infinity": "INF",
    }

    lowered = parameter.strip().casefold()
    if not lowered:
        raise ValueError("Timeout specification cannot be empty")

    if lowered in allowed:
        return allowed[lowered]
    raise ValueError(f"Invalid parameter specification: {parameter}")


def validate_frequency(frequency: int | float, channel: SourceChannel) -> int | float:
    """
    Validates the frequency value for a given channel.

    Args:
        frequency (float): The frequency value to validate.
        channel (SourceChannel): The channel for which the frequency is being validated.

    Returns:
        frequency: The validated frequency value.

    Raises:
        ValueError: If the frequency is not within the allowed range for the specified channel.
    """
    if channel == SourceChannel.SINE:
        if frequency < 1e-3 or frequency > 30.1e6:
            raise ValueError(f"Frequency {frequency} is out of range for SINE channel.")
    elif channel == SourceChannel.AUX:
        if frequency < 1e-3 or frequency > 10e6:
            raise ValueError(f"Frequency {frequency} is out of range for AUX channel.")
    elif channel == SourceChannel.PULSE:
        if frequency < 1e-3 or frequency > 25e6:
            raise ValueError(
                f"Frequency {frequency} is out of range for PULSE channel."
            )
    else:
        raise ValueError(f"Unknown source channel: {channel}")
    return frequency
