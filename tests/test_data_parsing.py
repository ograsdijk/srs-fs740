import numpy as np
import pytest

from srs_fs740.data_parsing import parse_timestamps


def test_parse_timestamps_returns_rows_of_eleven():
    payload = "1,2026,7,7,12,34,56,78,90,12,345,2,2025,1,2,3,4,5,6,7,8,9"

    result = parse_timestamps(payload)

    assert result.dtype == np.int32
    assert result.shape == (2, 11)
    assert result[0, 1] == 2026


@pytest.mark.parametrize("payload", ["", "1,2,3", "1,2,3,4,5,6,7,8,9,10"])
def test_parse_timestamps_rejects_bad_payloads(payload):
    with pytest.raises(ValueError):
        parse_timestamps(payload)
