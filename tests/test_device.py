from srs_fs740 import FS740, MeasureChannel, SourceAuxFunction, SourceChannel
import srs_fs740.device as device_module


class FakeInstrument:
    def __init__(self):
        self.writes = []
        self.queries = {}
        self.closed = 0

    def write(self, cmd):
        self.writes.append(cmd)

    def query(self, cmd):
        self.writes.append(f"QUERY:{cmd}")
        return self.queries.get(cmd, "0")

    def close(self):
        self.closed += 1


class FakeResourceManager:
    def __init__(self, instrument):
        self.instrument = instrument

    def open_resource(self, *args, **kwargs):
        return self.instrument


def make_clock(monkeypatch):
    instrument = FakeInstrument()
    monkeypatch.setattr(
        device_module.pyvisa,
        "ResourceManager",
        lambda: FakeResourceManager(instrument),
    )
    return FS740("10.10.222.4"), instrument


def test_context_manager_closes_once(monkeypatch):
    clock, instrument = make_clock(monkeypatch)

    with clock:
        pass

    assert instrument.closed == 1


def test_status_enable_setters_write_expected_commands(monkeypatch):
    clock, instrument = make_clock(monkeypatch)

    clock.set_status_gps_enable(3)
    clock.set_status_operation_enable(4)
    clock.set_status_questionable_enable(5)

    assert instrument.writes[-3:] == [
        "STATus:GPS:ENABle 3",
        "STATus:OPERation:ENABle 4",
        "STATus:QUEStionable:ENABle 5",
    ]


def test_sample_query_count_uses_channel(monkeypatch):
    clock, instrument = make_clock(monkeypatch)
    instrument.queries["SAMPle2:COUNt?"] = "12"

    assert clock.sample_query_count(MeasureChannel.REAR) == 12


def test_source_phase_and_aux_function_normalize_case(monkeypatch):
    clock, instrument = make_clock(monkeypatch)

    clock.set_source_phase(90, "deg", SourceChannel.SINE)
    clock.set_source_aux_function("tri")

    assert instrument.writes[-2:] == [
        "SOURce1:PHASe 90,DEG",
        f"SOURce2:FUNCtion {SourceAuxFunction.TRI}",
    ]
