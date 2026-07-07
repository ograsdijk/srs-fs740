import time

import numpy as np

from srs_fs740 import FS740, MeasureChannel, parse_timestamps

ip_address = "10.10.222.4"
channel = MeasureChannel.FRONT
count = 100

clock = FS740(ip_address)

# setup for time measurement
clock.measure_configure_time(channel=channel)
clock.sample_set_count(count=count)
while not clock.query_operation_complete():
    pass
clock.measure_initiate(channel=channel)

data = np.empty(shape=(0, 11), dtype=np.int32)
while True:
    points_in_memory = clock.data_query_points(channel)
    if not points_in_memory:
        continue
    data_raw = clock.data_remove(channel=channel, count=points_in_memory)
    data = np.vstack((data, parse_timestamps(data_raw)))
    # check if all samples are retrieved
    if len(data) >= count:
        break
    time.sleep(0.5)
