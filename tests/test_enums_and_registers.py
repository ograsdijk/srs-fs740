from srs_fs740 import (
    GPSReceiverStatus,
    OperationStatus,
    QuestionableStatus,
    SerialPollStatus,
    SourceAuxFunction,
    SourcePulseFunction,
    StandardEventStatus,
    get_set_flags,
)


def test_enum_string_values_are_preserved():
    assert str(SourceAuxFunction.SIN) == "SIN"
    assert str(SourcePulseFunction.IRIG) == "IRIG"


def test_get_set_flags_returns_bitflags():
    flags = get_set_flags(
        int(StandardEventStatus.OPC | StandardEventStatus.CME), StandardEventStatus
    )

    assert StandardEventStatus.OPC in flags
    assert StandardEventStatus.CME in flags


def test_register_enums_can_be_constructed_from_integers():
    assert SerialPollStatus(1 << 1) == SerialPollStatus.GPS
    assert OperationStatus(1 << 4) == OperationStatus.MEASURE_FRONT
    assert QuestionableStatus(1 << 0) == QuestionableStatus.TOD_NOT_SET
    assert GPSReceiverStatus(1 << 3) == GPSReceiverStatus.NO_SATELLITES
