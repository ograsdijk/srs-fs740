# srs-fs740

Python helpers for the Stanford Research Systems FS740 time and frequency instrument.

## Features

- Connect to an FS740 over direct TCP/IP
- Query measurements, status registers, and system state
- Parse timestamp payloads returned by the instrument
- Keep instrument commands in a Pythonic interface

## Install

```bash
uv sync --locked
```

The package depends on `numpy` only. It connects directly to the instrument over
TCP port `5025`, so you do not need a VISA backend.

## Quick Start

```python
from srs_fs740 import FS740, MeasureChannel, parse_timestamps

with FS740("10.10.222.4") as clock:
    ident = clock.query_identification()
    freq = clock.measure_frequency(MeasureChannel.FRONT)
    payload = clock.data_read(MeasureChannel.FRONT, index=0, count=1)

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
