import srs_fs740.device as device_module

from srs_fs740 import FS740, MeasureChannel, SourceAuxFunction, SourceChannel


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


def make_clock():
    instrument = FakeInstrument()
    return FS740("10.10.222.4", transport=instrument), instrument


def test_context_manager_closes_once():
    clock, instrument = make_clock()

    with clock:
        pass

    assert instrument.closed == 1


def test_status_enable_setters_write_expected_commands():
    clock, instrument = make_clock()

    clock.set_status_gps_enable(3)
    clock.set_status_operation_enable(4)
    clock.set_status_questionable_enable(5)

    assert instrument.writes[-3:] == [
        "STATus:GPS:ENABle 3",
        "STATus:OPERation:ENABle 4",
        "STATus:QUEStionable:ENABle 5",
    ]


def test_sample_query_count_uses_channel():
    clock, instrument = make_clock()
    instrument.queries["SAMPle2:COUNt?"] = "12"

    assert clock.sample_query_count(MeasureChannel.REAR) == 12


def test_source_phase_and_aux_function_normalize_case():
    clock, instrument = make_clock()

    clock.set_source_phase(90, "deg", SourceChannel.SINE)
    clock.set_source_aux_function("tri")

    assert instrument.writes[-2:] == [
        "SOURce1:PHASe 90,DEG",
        f"SOURce2:FUNCtion {SourceAuxFunction.TRI}",
    ]


class FakeStream:
    def __init__(self):
        self.writes = []
        self.responses = [b"MEAS,1,2\r\n"]

    def write(self, data):
        self.writes.append(data)

    def flush(self):
        pass

    def readline(self):
        return self.responses.pop(0)

    def close(self):
        pass


class FakeSocket:
    def __init__(self):
        self.timeout = None
        self.stream = FakeStream()
        self.closed = 0

    def settimeout(self, timeout):
        self.timeout = timeout

    def makefile(self, *args, **kwargs):
        return self.stream

    def close(self):
        self.closed += 1


def test_socket_transport_resolves_legacy_tcpip_string(monkeypatch):
    fake_socket = FakeSocket()
    calls = []

    def fake_create_connection(address, timeout):
        calls.append((address, timeout))
        return fake_socket

    monkeypatch.setattr(
        device_module.socket, "create_connection", fake_create_connection
    )

    transport = device_module._SocketInstrument("TCPIP0::10.10.222.4::5025::SOCKET")

    assert calls == [(("10.10.222.4", 5025), 5.0)]

    transport.write("TEST")
    assert fake_socket.stream.writes[-1] == b"TEST\r\n"
    assert transport.query("MEAS?") == "MEAS,1,2"

    transport.close()
    transport.close()
    assert fake_socket.closed == 1
