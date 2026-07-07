import numpy.typing as npt
import numpy as np


def parse_timestamps(timestamps: str) -> npt.NDArray[np.int32]:
    """Parse timestamps from the SRS FS740.

    A single result consists of 11 comma separated integer values in the following order:
        - timing metric
        - year
        - month
        - day
        - hour
        - minute
        - seconds
        - millisecond
        - microseconds
        - nanoseconds
        - picoseconds

    The timing metric is a copy of the questionable status register at the time of the
    measurement.
    """
    values = timestamps.strip()
    if not values:
        raise ValueError("timestamps cannot be empty")

    try:
        data = np.array(
            [int(value.strip()) for value in values.split(",")], dtype=np.int32
        )
    except ValueError as exc:
        raise ValueError(f"invalid timestamp payload: {timestamps}") from exc

    if data.size % 11 != 0:
        raise ValueError("timestamps invalid, cannot reshape into nx11 array")
    return data.reshape(-1, 11)
