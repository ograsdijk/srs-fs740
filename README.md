# srs-fs740

Python helpers for the Stanford Research Systems FS740 time and frequency instrument.

## Install

```bash
uv sync --locked
```

The package depends on `numpy` only. It connects directly to the instrument over
TCP port `5025`, so you do not need a VISA backend.

## Interface

`FS740` is a thin wrapper around the instrument's SCPI commands. It exposes:

- Common IEEE-488.2 commands such as `*IDN?`, `*RST`, `*CLS`, `*SRE`, and `*ESE`
- Measurement helpers for frequency, time, configuration, start/stop, fetch, and buffer queries
- Data helpers for reading and removing timestamp payloads
- Input, sample, sense, source, status, and timebase commands
- A `parse_timestamps()` helper that converts the instrument's 11-field payloads into a `numpy` array

Most methods are direct pass-throughs to the instrument, so the API mirrors the FS740 manual
pretty closely. The package also exports the enums and register helpers used by the interface:
`MeasureChannel`, `SourceChannel`, `SourceAuxFunction`, `SourcePulseFunction`, the status
register enums, `get_set_flags`, `validate_frequency`, and
`validate_parameter_string_min_max_def_inf`.

## Quick Start

```python
from srs_fs740 import FS740, MeasureChannel, parse_timestamps

with FS740("10.10.222.4") as clock:
    ident = clock.query_identification()
    freq = clock.measure_frequency(MeasureChannel.FRONT)
    points = clock.data_query_points(MeasureChannel.FRONT)
    payload = clock.data_read(MeasureChannel.FRONT, index=0, count=min(1, points))

timestamps = parse_timestamps(payload)
```

## Development

Run the local checks with:

```bash
uv run --with pytest pytest
uv run --with ruff ruff check .
uv run --with ruff ruff format --check .
uv run --with mypy --with pytest mypy src tests
uv build
```

## Repository Layout

- `src/srs_fs740/`: package code
- `tests/`: unit tests
- `examples/`: small usage scripts

## Notes

- The example scripts assume you have a reachable FS740 on the network.
- The test suite uses a fake instrument and does not require hardware.
- Publishing to PyPI is handled by GitHub Actions when a `v*` tag is pushed.

## Functions

- `FS740(...)`: opens a TCP connection to the instrument and exposes the command interface.
- `query_identification()`: reads the instrument identity string.
- `measure_frequency(channel)`: measures frequency on the selected input channel.
- `measure_time(channel)`: reads the 11-field time measurement payload.
- `measure_query_config(channel)`: returns the current measurement configuration.
- `measure_configure_frequency(channel, config)`: configures frequency measurement settings.
- `measure_configure_time(channel, config)`: configures time measurement settings.
- `measure_initiate(channel)`, `measure_fetch(channel)`, `measure_abort(channel)`, `measure_stop(channel)`: control a measurement cycle.
- `data_query_count(channel)`, `data_query_points(channel)`: report how much measurement data is available.
- `data_read(channel, index, count)` and `data_remove(channel, index, count)`: read or remove timestamp records from internal memory.
- `set_input_level(channel, level)` and `query_input_level(channel)`: set or read the input trigger level.
- `set_input_slope(channel, slope)`: set the input slope to positive, negative, or default.
- `sample_set_count(channel, count)` and `sample_query_count(channel)`: set or read the sample count.
- `set_sense_frequency_gate(channel, value)` and `query_sense_frequency_gate(channel)`: control the frequency gate time.
- `set_sense_frequency_timeout(channel, timeout)` and `get_sense_frequency_timeout(channel)`: control the frequency timeout.
- `set_sense_time_buffer_mode(channel, mode)` and `get_sense_time_buffer_mode(channel)`: control the time buffer mode.
- `set_source_frequency(channel, frequency)` and `get_source_frequency(channel)`: set or read the source frequency.
- `set_source_aux_function(function)` and `get_source_aux_function()`: configure the auxiliary output function.
- `set_source_pulse_function(function)` and `get_source_pulse_function()`: configure the pulse output function.
- `set_source_phase(channel, phase, unit)` and `get_source_phase(channel)`: set or read source phase.
- `query_status_gps_condition()`, `query_status_gps_enable()`, `query_status_gps_event()`: inspect GPS status registers.
- `set_status_gps_enable(mask)`: set the GPS enable mask.
- `query_status_operation_condition()`, `query_status_operation_enable()`, `query_status_operation_event()`: inspect operation status registers.
- `set_status_operation_enable(mask)`: set the operation enable mask.
- `query_status_questionable_condition()`, `query_status_questionable_enable()`, `query_status_questionable_event()`: inspect questionable status registers.
- `set_status_questionable_enable(mask)`: set the questionable enable mask.
- `query_system_alarm()` and `clear_system_alarm()`: read or clear the system alarm state.
- `set_timebase_config_bandwidth(bandwidth)`, `query_timebase_config_bandwidth()`: read or change the timebase bandwidth.
- `set_timebase_config_hmode(hmode)`, `query_timebase_config_hmode()`: read or change the holdover mode.
- `set_timebase_config_lock(lock)`, `query_timebase_config_lock()`: read or change timebase lock state.
- `set_timebase_config_interval_limit(limit)`, `query_timebase_config_interval_limit()`: read or change the interval limit.
- `timebase_event_clear()` and `query_timebase_event_count()`: clear or inspect timebase events.
- `parse_timestamps(payload)`: convert raw timestamp text into a `numpy.ndarray`.
