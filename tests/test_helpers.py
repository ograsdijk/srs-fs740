import pytest
from typing import cast

from srs_fs740.config_enums import SourceChannel
from srs_fs740.helper_functions import (
    validate_frequency,
    validate_parameter_string_min_max_def_inf,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("min", "MIN"),
        (" Maximum ", "MAX"),
        ("def", "DEF"),
        ("INF", "INF"),
    ],
)
def test_validate_parameter_string_min_max_def_inf(value, expected):
    assert validate_parameter_string_min_max_def_inf(value) == expected


def test_validate_parameter_string_min_max_def_inf_rejects_unknown_value():
    with pytest.raises(ValueError):
        validate_parameter_string_min_max_def_inf("banana")


@pytest.mark.parametrize(
    ("frequency", "channel"),
    [
        (1e-3, SourceChannel.SINE),
        (10e6, SourceChannel.AUX),
        (25e6, SourceChannel.PULSE),
    ],
)
def test_validate_frequency_accepts_supported_ranges(frequency, channel):
    assert validate_frequency(frequency, channel) == frequency


def test_validate_frequency_rejects_out_of_range_values():
    with pytest.raises(ValueError):
        validate_frequency(0.0, SourceChannel.SINE)


def test_validate_frequency_rejects_unknown_channel():
    with pytest.raises(ValueError):
        validate_frequency(1.0, cast(SourceChannel, 999))
