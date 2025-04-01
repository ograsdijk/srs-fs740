import numpy as np
import numpy.typing as npt


def parse_timestamps(timestamps: str) -> npt.NDArray[np.int16]:
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
    dat = np.fromstring(timestamps, np.int16, sep=",")
    assert dat.size % 11 == 0, "timestamps invalid, cannot reshape into nx11 array"
    return dat.reshape(-1, 11)
