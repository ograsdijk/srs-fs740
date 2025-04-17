import time

import numpy as np

from srs_fs740 import FS740, MeasureChannel, parse_timestamps

ip_address = "10.10.222.4"
channel = MeasureChannel.FRONT
count = 1

clock = FS740(ip_address)

# setup for time measurement
clock.measure_configure_time(channel=channel)
clock.sample_set_count(count=count)
clock.measure_initiate(channel=channel)

data = np.empty([], dtype=np.int16)
while True:
    points_in_memory = clock.data_query_points(channel)
    data_raw = clock.data_remove(channel=channel, count=points_in_memory)
    data = np.append(data, parse_timestamps(data_raw))
    time.sleep(0.5)
