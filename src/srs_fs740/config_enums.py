from enum import Enum, IntEnum
from typing import Literal


class MeasureChannel(IntEnum):
    FRONT = 1
    REAR = 2


class SourceChannel(IntEnum):
    SINE = 1
    AUX = 2
    PULSE = 3


class SourceAuxFunction(str, Enum):
    SIN = "SIN"
    TRI = "TRI"
    SQU = "SQU"
    HMHZ = "HMHZ"
    IRIG = "IRIG"

    def __str__(
        self,
    ) -> (
        Literal["SIN"]
        | Literal["TRI"]
        | Literal["SQU"]
        | Literal["HMHZ"]
        | Literal["IRIG"]
    ):
        return self.value


class SourcePulseFunction(str, Enum):
    PULS = "PULS"
    IRIG = "IRIG"

    def __str__(self) -> Literal["PULS"] | Literal["IRIG"]:
        return self.value
