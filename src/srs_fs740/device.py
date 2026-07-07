import math
from typing import Self, cast

import pyvisa
from pyvisa.resources import TCPIPSocket

from .config_enums import (
    MeasureChannel,
    SourceAuxFunction,
    SourceChannel,
    SourcePulseFunction,
)
from .helper_functions import (
    validate_frequency,
    validate_parameter_string_min_max_def_inf,
)
from .registers import (
    GPSReceiverStatus,
    OperationStatus,
    QuestionableStatus,
    SerialPollStatus,
    StandardEventStatus,
)


def _normalize_choice(value: str, allowed: set[str], label: str) -> str:
    normalized = value.strip().casefold()
    if normalized not in allowed:
        raise ValueError(f"{label} must be one of {sorted(allowed)}")
    return normalized.upper()


class FS740:
    def __init__(self, resource_name: str) -> None:
        rm = pyvisa.ResourceManager()
        self.instr = cast(
            TCPIPSocket,
            rm.open_resource(
                f"TCPIP0::{resource_name}::5025::SOCKET", read_termination="\r\n"
            ),
        )

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc) -> None:
        self.instr.close()

    def write(self, cmd: str) -> None:
        """Sends a command to the instrument without waiting for a reply.

        Args:
            command (str): The command string to be sent.
        """
        self.instr.write(cmd)

    def query(self, cmd: str) -> str:
        """Sends a query command to the instrument and returns its response.

        Args:
            command (str): The command string to be sent.

        Returns:
            str: The response from the instrument.
        """
        return self.instr.query(cmd)

    # --- IEEE-488.2 Common Commands (Pages 91-94) ---

    def clear_status(self) -> None:
        """Clears all status registers and the error queue.

        Sends the *CLS command to clear:
          - The Standard Event Status Register (ESR)
          - The Questionable Status Register
          - The Operation Status Register
          - The error queue

        See page 91 of the FS740 manual.
        """
        self.write("*CLS")

    def set_event_enable(self, value: int | StandardEventStatus) -> None:
        """Sets the Standard Event Status Enable (ESE) register.

        Sends the *ESE command with the specified value. The ESE register is a bit mask (0–255)
        that enables notification of events in the Standard Event Status Register (ESR). The ESR
        (documented on page 91) has the following bit definitions:

          - Bit 0: OPC – Operation Complete (set when the previous command has finished)
          - Bit 1: Reserved
          - Bit 2: QYE – Query Error (set when a query error occurs)
          - Bit 3: DDE – Device-Dependent Error (set for instrument-specific errors)
          - Bit 4: EXE – Execution Error (set when a command could not execute properly)
          - Bit 5: CME – Command Error (set when an invalid command is received)
          - Bit 6: Reserved
          - Bit 7: PON – Power On (set at power-up)

        The value passed to *ESE should be constructed so that the bits you want to enable match
        the above definitions.

        Args:
            value (int): The bit mask value to set in the ESE register.

        See page 91 of the FS740 manual.
        """
        self.write(f"*ESE {value}")

    def query_event_status(self) -> StandardEventStatus:
        """Queries the Standard Event Status Register (ESR).

        Sends the *ESR? command to retrieve the contents of the ESR. The ESR is an 8-bit register
        whose bits are defined as follows (see page 91 of the FS740 manual):

          - Bit 0: OPC – Operation Complete (set when the last command is finished)
          - Bit 1: Reserved
          - Bit 2: QYE – Query Error (set if a query error occurred)
          - Bit 3: DDE – Device-Dependent Error (set if an instrument-specific error occurred)
          - Bit 4: EXE – Execution Error (set if an error occurred during command execution)
          - Bit 5: CME – Command Error (set if the command was not recognized or was invalid)
          - Bit 6: Reserved
          - Bit 7: PON – Power On (set when the instrument is powered on)

        Reading this register typically clears it.

        Returns:
            int: An integer representing the ESR contents (usually as a numeric value).

        See page 91 of the FS740 manual.
        """
        return StandardEventStatus(int(self.query("*ESR?")))

    def query_identification(self) -> str:
        """Queries the instrument identification string.

        Sends the *IDN? command to retrieve the identification string. This string typically
        contains the manufacturer, model number, serial number, and firmware version.

        Returns:
            str: The instrument identification string.

        See page 92 of the FS740 manual.
        """
        return self.query("*IDN?")

    def operation_complete(self) -> None:
        """Signals that all prior commands have completed.

        Sends the *OPC command. The instrument sets the OPC bit in the ESR when all previous commands
        have finished. (The query form *OPC? returns '1' when complete without affecting the ESR.)

        See page 92 of the FS740 manual.
        """
        self.write("*OPC")

    def query_operation_complete(self) -> bool:
        """Queries the Operation Complete (OPC) bit in the ESR.

        Sends the *OPC? command to check if all previous commands have completed. The instrument
        returns '1' if complete, '0' otherwise.

        Returns:
            bool: True if all commands are complete, False otherwise.

        See page 92 of the FS740 manual.
        """
        return self.query("*OPC?") == "1"

    def query_options(self) -> str:
        """Queries the installed options on the instrument.

        Sends the *OPT? command to obtain a comma-separated string representing the installed options.
        The returned format is typically:
          "<Timebase>,*<OPTIONS>"

        Timebases available:
          - 1 TCXO
          - 2 OCXO
          - 3 Rb
        Options available:
          - A (10 MHz Distribution): Provides 5 outputs identical to the motherboard 10 MHz output.
          - B (Sine/Aux Distribution): Provides 5 outputs for sine or aux output.
          - C (Pulse Distribution): Provides 5 outputs for pulse output.

        Returns:
            str: A comma-separated string representing the installed options.

        See page 92 of the FS740 manual.
        """
        return self.query("*OPT?")

    def power_on_status_clear(self, value: int) -> None:
        """Sets the Power-on Status Clear (PSC) flag.

        Sends the *PSC command with the given value to clear any status flags set at power-on.
        This helps ensure a known starting state for the status registers.

        If the value of the flag is 0, then the Service Request Enable and Standard
        Event Status Enable  Registers (*SRE, *ESE) are stored in non-volatile memory,
        and retain their values through powercycle events.
        If the value of the flag is 1, then these two registers are cleared upon
        power-cycle.

        Args:
            value (int): The value to set for the PSC flag. 0 or 1.

        See page 93 of the FS740 manual.
        """
        if value not in (0, 1):
            raise ValueError("PSC value must be 0 or 1")
        self.write(f"*PSC {value}")

    def recall_settings(self, slot: int) -> None:
        """Recalls instrument settings from a specified storage slot.

        Sends the *RCL command to load settings previously saved in the specified slot.
        This command allows quick reconfiguration of the instrument. Locations 1 to 9
        are for arbitrary use, while location 0 is reserved for factory settings.

        Args:
            slot (int): The storage slot number (typically 0–9).

        See page 93 of the FS740 manual.
        """
        if not 0 <= slot <= 9:
            raise ValueError("Slot must be between 0 and 9")
        self.write(f"*RCL {slot}")

    def reset(self) -> None:
        """Resets the instrument to its factory default settings.

        Sends the *RST command, which resets the instrument's settings. Some nonvolatile
        settings may persist depending on the instrument's design.

        See page 93 of the FS740 manual.
        """
        self.write("*RST")

    def save_settings(self, slot: int) -> None:
        """Saves the current instrument settings to a specified storage slot.

        Sends the *SAV command with the given slot number, storing the current
        configuration so it can be recalled later using the *RCL command. Locations 1
        to 9 are for arbitrary use, while location 0 is reserved for factory settings.

        Args:
            slot (int): The storage slot number where settings will be saved.

        See page 93 of the FS740 manual.
        """
        if not 1 <= slot <= 9:
            raise ValueError("Slot must be between 1 and 9")
        self.write(f"*SAV {slot}")

    def service_request_enable(self, value: int) -> None:
        """Sets the Service Request Enable (SRE) register.

        Sends the *SRE command with the specified value. The SRE register is a bit mask that
        determines which events will cause the instrument to assert a service request. Although
        the detailed bit definitions for SRE are documented on page 94 of the FS740 manual, they
        generally correspond to the events indicated in the ESR.

        Args:
            value (int): The bit mask (0–255) to set in the SRE register.

        See page 94 of the FS740 manual.
        """
        self.write(f"*SRE {value}")

    def query_serial_poll_status(self) -> SerialPollStatus:
        """Queries the Serial Poll Status Byte (STB).

        Sends the *STB? command to retrieve the standard IEEE 488.2 serial poll status byte.
        The STB register is defined (see page 82 of the FS740 manual) as follows:

          - Bit 0: Reserved
          - Bit 1: GPS status summary bit
          - Bit 2: Error queue is not empty
          - Bit 3: Questionable status summary bit
          - Bit 4: Message available (MAV)
          - Bit 5: ESR status summary bit
          - Bit 6: MSS – master summary bit
          - Bit 7: Operational status summary bit

        Returns:
            int: An integer representing the contents of the STB register.

        See page 82 of the FS740 manual for detailed information on the STB.
        """
        return SerialPollStatus(int(self.query("*STB?")))

    def wait_for_completion(self) -> None:
        """Waits for all previous commands to complete.

        Sends the *WAI command, which blocks further processing until all prior commands
        have finished executing.

        See page 94 of the FS740 manual.
        """
        self.write("*WAI")

    # --- Remote and Local commands (Page 95) ---

    def set_local(self) -> None:
        """Switches the instrument to local mode.

        Sends the LOCal command. This command places the instrument in local mode,
        where the remote interface is disabled and the front-panel interface becomes active.

        See page 95 of the FS740 manual.
        """
        self.write("LOCal")

    def go_local(self) -> None:
        """Enables front-panel access ("Go to Local").

        Sends the LOCal:KEY command. This command is equivalent to pressing the
        "Go to Local" key on the front panel. Once sent, front-panel access is allowed
        until the next remote command is received.

        See page 95 of the FS740 manual.
        """
        self.write("LOCal:KEY")

    def set_remote(self) -> None:
        """Switches the instrument to remote mode.

        Sends the REMote command to disable front-panel (local) access, causing the instrument
        to accept only remote commands.

        See page 95 of the FS740 manual.
        """
        self.write("REMote")

    # --- Measurement commands (Pages 96-99) ---

    def measure_frequency(
        self, channel: MeasureChannel = MeasureChannel.FRONT
    ) -> float:
        """Queries the current frequency measurement for the specified input.

        Sends the command:
            MEASure{channel}:FREQuency?
        The instrument returns the measured frequency (with 1 μHz resolution, etc.) from the
        specified measurement input.

        Args:
            channel (int, optional): Measurement input channel (1 for front, 2 for rear). Defaults to 1.

        Returns:
            float: The measured frequency.

        See page 96 of the FS740 manual.
        """
        return float(self.query(f"MEASure{channel}:FREQuency?"))

    def measure_time(
        self, channel: MeasureChannel = MeasureChannel.FRONT
    ) -> tuple[int, int, int, int, int, int, int, int, int, int, int]:
        """Queries the current time measurement for the specified input.

        Sends the command:
            MEASure{channel}:TIMe?
        The instrument returns the measured time interval (with 1 ps resolution and <50 ps jitter rms)
        from the specified measurement input.

        Args:
            channel (int, optional): Measurement input channel (1 for front, 2 for rear). Defaults to 1.

        Returns:
            str: The measured time interval as a numeric string.

        See page 96 of the FS740 manual.
        """
        measured_time = tuple(
            [int(val) for val in self.query(f"MEASure{channel}:TIMe?").split(",")]
        )
        if len(measured_time) != 11:
            raise ValueError(f"expected 11 values, got {len(measured_time)}")
        return cast(
            tuple[int, int, int, int, int, int, int, int, int, int, int], measured_time
        )

    def measure_query_config(
        self, channel: MeasureChannel = MeasureChannel.FRONT
    ) -> str:
        """Queries the current measurement configuration for the specified input.

        Sends the command:
            CONFigure{channel}?
        The returned configuration typically includes parameters such as measurement type,
        gate time, sample count, and trigger level.

        Args:
            channel (int, optional): Measurement input channel (1 or 2). Defaults to 1.

        Returns:
            str: A string representing the current measurement configuration.

        See page 97 of the FS740 manual.
        """
        return self.query(f"CONFigure{channel}?")

    def measure_configure_frequency(
        self, channel: MeasureChannel = MeasureChannel.FRONT, config: str = ""
    ) -> None:
        """Configures the frequency measurement parameters for the specified input.

        Sends the command:
            CONFigure{channel}:FREQuency {config}
        The configuration string should follow the syntax detailed on page 97 (for
        example, specifying gate time and sample count).

        Args:
            channel (int, optional): Measurement input channel (1 for front, 2 for rear). Defaults to 1.
            config (str): A string with the frequency measurement configuration parameters.

        See page 97 of the FS740 manual.
        """
        self.write(f"CONFigure{channel}:FREQuency {config}")

    def measure_configure_time(
        self, channel: MeasureChannel = MeasureChannel.FRONT, config: str = ""
    ) -> None:
        """Configures the time measurement parameters for the specified input.

        Sends the command:
            CONFigure{channel}:TIMe {config}
        The configuration string should follow the syntax defined on page 97 (for example, specifying gate
        duration or trigger mode).

        Args:
            channel (int, optional): Measurement input channel (1 for front, 2 for rear). Defaults to 1.
            config (str): A string with the time measurement configuration parameters.

        See page 97 of the FS740 manual.
        """
        self.write(f"CONFigure{channel}:TIMe {config}")

    def measure_initiate(self, channel: MeasureChannel = MeasureChannel.FRONT) -> None:
        """Initiates the measurement process for the specified input.

        Sends the command:
            INITiate{channel}
        The measurement starts based on the current configuration and continues until the sample count
        is reached or an abort/stop command is issued.

        Args:
            channel (int, optional): Measurement input channel (1 or 2). Defaults to 1.

        See page 98 of the FS740 manual.
        """
        self.write(f"INITiate{channel}")

    def measure_fetch(self, channel: MeasureChannel = MeasureChannel.FRONT) -> str:
        """Fetches the measurement results from the specified input.

        Sends the command:
            FETCh?{channel}
        The instrument returns the acquired measurement data from the output buffer once the measurement
        is complete.

        Args:
            channel (int, optional): Measurement input channel (1 or 2). Defaults to 1.

        Returns:
            str: A string containing the measurement results.

        See page 99 of the FS740 manual.
        """
        return self.query(f"FETCh?{channel}")

    def measure_abort(self, channel: MeasureChannel = MeasureChannel.FRONT) -> None:
        """Aborts the ongoing measurement for the specified input.

        Sends the command:
            ABORt{channel}
        This immediately halts an in-progress measurement. Data already captured may remain in the buffer.

        Args:
            channel (int, optional): Measurement input channel (1 or 2). Defaults to 1.

        See page 99 of the FS740 manual.
        """
        self.write(f"ABORt{channel}")

    def measure_stop(self, channel: MeasureChannel = MeasureChannel.FRONT) -> None:
        """Stops the measurement process for the specified input.

        Sends the command:
            STOP{channel}
        This halts data acquisition without discarding any captured data.

        Args:
            channel (int, optional): Measurement input channel (1 or 2). Defaults to 1.

        See page 99 of the FS740 manual.
        """
        self.write(f"STOP{channel}")

    # --- Data Subsystem (Pages 102-104) ---

    def data_query_count(self, channel: MeasureChannel = MeasureChannel.FRONT) -> int:
        """Queries the total number of data measurements completed for a specified channel.

        Sends the command:
            DATA{channel}:COUNt?
        where {channel} is either 1 (front) or 2 (rear).

        Args:
            channel (int, optional): The data channel to query (1 for front, 2 for rear). Defaults to 1.

        Returns:
            int: A integer representing the total completed measurements.

        See page 102 of the FS740 manual.
        """
        return int(self.query(f"DATA{channel}:COUNt?"))

    def data_query_points(self, channel: MeasureChannel = MeasureChannel.FRONT) -> int:
        """Queries the number of valid data points available for reading from internal
        memory for a specified channel.

        Sends the command:
            DATA{channel}:POINts?
        where {channel} is either 1 (front) or 2 (rear).

        Args:
            channel (int, optional): The data channel to query (1 for front, 2 for rear). Defaults to 1.

        Returns:
            int: A integer representing the number of available data points.

        See page 102 of the FS740 manual.
        """
        return int(self.query(f"DATA{channel}:POINts?"))

    def data_read(
        self,
        channel: MeasureChannel = MeasureChannel.FRONT,
        index: int = 0,
        count: int = 1,
    ) -> str:
        """Reads measurement data from the instrument’s memory for a specified channel.

        Sends the command:
            DATA{channel}:READ? [<index>][,<count>]
        where {channel} is 1 (front) or 2 (rear). The optional <index> specifies the starting data point,
        and the optional <count> specifies the number of data points to retrieve. If <count> is provided without
        an <index>, the instrument defaults to index 0.

        Args:
            channel (int, optional): The data channel to read from (1 for front, 2 for rear). Defaults to 1.
            index (int): The starting index for data retrieval. Defaults to 0.
            count (int): The number of data points to read. Defaults to 1.

        Returns:
            str: A formatted string containing the measurement data (typically comma-separated).

        See page 103 of the FS740 manual.
        """
        command = f"DATA{channel}:READ? {index},{count}"
        return self.query(command)

    def data_remove(
        self, channel: MeasureChannel = MeasureChannel.FRONT, count: int = 1
    ) -> str:
        """Clears measurement data from the instrument’s memory for a specified channel.

        Sends the command:
            DATA{channel}:REMove? <count>
        where {channel} is 1 (front) or 2 (rear) and <count> is the number of data points to remove from the buffer.

        Args:
            channel (int, optional): The data channel to clear (1 for front, 2 for rear). Defaults to 1.
            count (int): The number of data points to remove. Defaults to 1.

        Returns:
            str: A confirmation message or status as a string.

        See page 103 of the FS740 manual.
        """
        command = f"DATA{channel}:REMove? {count}"
        return self.query(command)

    # -- Input Subsystem (Pages 110-111) ---
    def set_input_level(
        self, channel: MeasureChannel = MeasureChannel.FRONT, level: float = 0.0
    ) -> None:
        """Sets the input level for the specified channel.

        Sends the command:
            INPut{channel}:LEVel {level}
        where {channel} is either 1 (front) or 2 (rear). The <level> parameter specifies the desired input level.

        Args:
            channel (int): The measurement channel (1 for front, 2 for rear).
            level (float): The desired input level in volts.

        See page 110 of the FS740 manual.
        """
        self.write(f"INPut{channel}:LEVel {level}")

    def query_input_level(
        self, channel: MeasureChannel = MeasureChannel.FRONT
    ) -> float:
        """Queries the current input level for the specified channel.

        Sends the command:
            INPut{channel}:LEVel?
        where {channel} is either 1 (front) or 2 (rear). The instrument returns the current input level.

        Args:
            channel (int): The measurement channel (1 for front, 2 for rear).

        Returns:
            float: The current input level in volts.

        See page 110 of the FS740 manual.
        """
        return float(self.query(f"INPut{channel}:LEVel?"))

    def set_input_slope(
        self, channel: MeasureChannel = MeasureChannel.FRONT, slope: str = "POS"
    ) -> None:
        """Sets the input slope for the specified channel.

        Sends the command:
            INPut{channel}:SLOPe POSitive
        where {channel} is either 1 (front) or 2 (rear). The instrument sets the input slope to positive.

        Args:
            channel (int): The measurement channel (1 for front, 2 for rear).
            slope (str): The desired slope ("POS" for positive, "NEG" for negative, "DEF" for default ("POS")). Defaults to "POS".

        See page 110 of the FS740 manual.
        """
        slope = _normalize_choice(slope, {"pos", "neg", "def"}, "slope")
        self.write(f"INPut{channel}:SLOPe {slope}")

    # --- Sample Subsystem (Pages 111-112) ---

    def sample_set_count(
        self, channel: MeasureChannel = MeasureChannel.FRONT, count: int = 1
    ) -> None:
        """Sets the number of samples to acquire in a measurement.

        Sends the command:
            SAMPle:COUNt <value>
        where <value> is the desired sample count. This command determines how many samples
        (data points) will be acquired during a measurement before it completes.

        Args:
            count (int): The desired number of samples.

        See page 111 of the FS740 manual.
        """
        self.write(f"SAMPle{channel}:COUNt {count}")

    def sample_query_count(self, channel: MeasureChannel = MeasureChannel.FRONT) -> int:
        """Queries the current sample count setting.

        Sends the command:
            SAMPle{channel}:COUNt?
        The instrument returns a integer indicating the number of samples configured
        for measurement.

        Returns:
            str: A numeric string representing the current sample count.

        See page 111 of the FS740 manual.
        """
        return int(self.query(f"SAMPle{channel}:COUNt?"))

    # --- Sense Subsystem (Pages 112-113) ---

    def set_sense_frequency_gate(
        self, value: float, channel: MeasureChannel = MeasureChannel.FRONT
    ) -> None:
        """Sets the frequency gate time for the measurement.

        Sends the command:
            SENSe<channel>:FREQuency:GATe <value>
        where <value> is the desired gate time in seconds. This command configures the
        duration for which the instrument will measure frequency.

        Args:
            value (int): The desired gate time in seconds.
            channel (Channel): The measurement channel (1 for front, 2 for rear).
                                Defaults to 1

        See page 112 of the FS740 manual.
        """
        self.write(f"SENSe{channel}:FREQuency:GATe {value}")

    def query_sense_frequency_gate(
        self, channel: MeasureChannel = MeasureChannel.FRONT
    ) -> float:
        """Queries the current frequency gate time setting.

        Sends the command:
            SENSe<channel>:FREQuency:GATe?
        The instrument returns a numeric string indicating the current gate time.

        Args:
            channel (Channel): The measurement channel (1 for front, 2 for rear).
                                Defaults to 1

        Returns:
            float: The current frequency gate time in seconds.

        See page 112 of the FS740 manual.
        """
        return float(self.query(f"SENSe{channel}:FREQuency:GATe?"))

    def set_sense_frequency_timeout(
        self, timeout: float | str, channel: MeasureChannel = MeasureChannel.FRONT
    ) -> None:
        """Sets the frequency measurement timeout.

        Sends the command:
            SENSe<channel>:FREQuency:TIMEout <value>
        where <value> is the desired timeout in seconds. This command configures the
        maximum time allowed for a frequency measurement before it is considered to have failed.

        Args:
            timeout (float | str): The desired timeout in seconds or MIN, MAX, DEF or INF.
            channel (Channel): The measurement channel (1 for front, 2 for rear).
                                Defaults to 1

        See page 112 of the FS740 manual.
        """
        if isinstance(timeout, str):
            timeout = validate_parameter_string_min_max_def_inf(timeout)
        else:
            if not (10e-3 <= timeout <= 2_000):
                raise ValueError("timeout must be >= 10 ms and <= 2000 s")
        self.write(f"SENSe{channel}:FREQuency:TIMEout {timeout}")

    def get_sense_frequency_timeout(
        self, channel: MeasureChannel = MeasureChannel.FRONT
    ) -> float:
        """Queries the frequency measurement timeout.

        Sends the command:
            SENSe<channel>:FREQuency:TIMEout?
        The instrument returns a numeric string indicating the current timeout setting.

        Args:
            channel (Channel, optional): Channel to query. Defaults to Channel.FRONT.

        Returns:
            float: timeout in seconds.
        """
        return float(self.query(f"SENSe{channel}:FREQuency:TIMEout?"))

    def set_sense_time_buffer_mode(
        self, mode: str, channel: MeasureChannel = MeasureChannel.FRONT
    ) -> None:
        """Sets the time measurement buffer mode.

        Sends the command:
            SENSe<channel>:TIMe:BUFFer:MODE <mode>
        where <mode> is either "KFIR" or "KLAS". This command configures how the instrument
        handles the data buffer during time measurements. "KFIR" keeps first, "KLAS" keeps last.
        The default mode is "KLAS".

        Args:
            mode (str): The desired buffer mode ("KFIR" or "KLAS").

        See page 113 of the FS740 manual.
        """
        mode = _normalize_choice(mode, {"kfir", "klas"}, "mode")
        self.write(f"SENSe{channel}:TIMe:BUFFer:MODE {mode}")

    def get_sense_time_buffer_mode(
        self, channel: MeasureChannel = MeasureChannel.FRONT
    ) -> str:
        """Queries the current time measurement buffer mode.

        Sends the command:
            SENSe<channel>:TIMe:BUFFer:MODE?
        The instrument returns a string indicating the current buffer mode.

        Args:
            channel (Channel, optional): Channel to query. Defaults to Channel.FRONT.

        Returns:
            str: The current buffer mode ("KFIR" or "KLAS").

        See page 113 of the FS740 manual.
        """
        return self.query(f"SENSe{channel}:TIMe:BUFFer:MODE?")

    # --- Source Subsystem (Pages 114-119) ---

    def set_source_frequency(
        self, frequency: int | float | str, channel: SourceChannel = SourceChannel.SINE
    ) -> None:
        """Sets the frequency of the sine wave output.

        Sends the command:
            SOURce{channel}:FREQuency <value>
        where <value> is the desired frequency in Hz. This command configures the output frequency
        for the specified source channel.

        Args:
            frequency (float): The desired frequency in Hz.
            channel (SourceChannel): The source channel (1 for sine, 2 for aux, 3 for pulse).

        See page 114 of the FS740 manual.
        """
        if isinstance(frequency, str):
            frequency = validate_parameter_string_min_max_def_inf(frequency)
        elif isinstance(frequency, float | int):
            frequency = validate_frequency(frequency, channel)
        else:
            raise TypeError(
                f"frequency must be a float, int or str, not {type(frequency)}"
            )
        self.write(f"SOURce{channel}:FREQuency {frequency}")

    def get_source_frequency(
        self, channel: SourceChannel = SourceChannel.SINE
    ) -> float:
        """Queries the current frequency setting for the specified source channel.

        Sends the command:
            SOURce{channel}:FREQuency?
        The instrument returns a numeric string indicating the current frequency.

        Args:
            channel (SourceChannel): The source channel (1 for sine, 2 for aux, 3 for pulse).

        Returns:
            float: The current frequency in Hz.

        See page 114 of the FS740 manual.
        """
        return float(self.query(f"SOURce{channel}:FREQuency?"))

    def set_source_aux_function(self, function: str | SourceAuxFunction):
        """Sets the function of the auxiliary output.

        Sends the command:
            SOURce2:FUNCtion <function>
        where <function> is the desired function (e.g., "SIN", "TRI", "SQU", etc.). This command configures
        the output function for the auxiliary source channel.

        Args:
            function (SourceAuxWaveform): The desired source function.

        See page 115 of the FS740 manual.
        """
        if isinstance(function, str):
            function = _normalize_choice(
                function, {"sin", "tri", "squ", "hmhz", "irig"}, "function"
            )
        elif isinstance(function, SourceAuxFunction):
            function = str(function)
        else:
            raise TypeError("function must be of type str or SourceAuxFunction")
        self.write(f"SOURce2:FUNCtion {function}")

    def get_source_aux_function(self) -> SourceAuxFunction:
        """Queries the current function setting for the auxiliary output.

        Sends the command:
            SOURce2:FUNCtion?
        The instrument returns a string indicating the current function.

        Returns:
            str: The current function of the auxiliary output.

        See page 115 of the FS740 manual.
        """
        return SourceAuxFunction(self.query("SOURce2:FUNCtion?").upper())

    def set_source_pulse_function(self, function: str | SourcePulseFunction):
        """Sets the function of the pulse output.

        Sends the command:
            SOURce3:FUNCtion <function>
        where <function> is the desired function (e.g., "PULS", "IRIG"). This command configures
        the output function for the pulse source channel.

        Args:
            function (SourcePulseWaveform): The desired source function.

        See page 115 of the FS740 manual.
        """
        if isinstance(function, str):
            function = _normalize_choice(function, {"puls", "irig"}, "function")
        elif isinstance(function, SourcePulseFunction):
            function = str(function)
        else:
            raise TypeError("function must be of type str or SourcePulseFunction")
        self.write(f"SOURce3:FUNCtion {function}")

    def get_source_pulse_function(self) -> SourcePulseFunction:
        """Queries the current function setting for the pulse output.

        Sends the command:
            SOURce3:FUNCtion?
        The instrument returns a string indicating the current function.

        Returns:
            str: The current function of the pulse output.

        See page 115 of the FS740 manual.
        """
        return SourcePulseFunction(self.query("SOURce3:FUNCtion?").upper())

    def set_source_phase(
        self,
        phase: int | float | str,
        unit: str,
        channel: SourceChannel = SourceChannel.SINE,
    ) -> None:
        """Sets the phase of the sine wave output.

        Sends the command:
            SOURce{channel}:PHASe <value>
        where <value> is the desired phase in degrees. This command configures the output phase
        for the specified source channel.

        Args:
            phase (float): The desired phase.
            unit (str): The units of the phase, case insensitive (e.g., "DEG", "RAD", "SEC").
            channel (SourceChannel): The source channel (1 for sine, 2 for aux, 3 for pulse).

        See page 115 of the FS740 manual.
        """
        unit_token = _normalize_choice(unit, {"deg", "rad", "sec"}, "unit")
        if isinstance(phase, str):
            phase = validate_parameter_string_min_max_def_inf(phase)
            if phase == "INF":
                raise ValueError("phase cannot be INF")
        elif unit_token == "DEG" and isinstance(phase, (float, int)):
            if not (-360 <= phase <= 360):
                raise ValueError("phase must be >= -360 and <= 360 degrees")
        elif unit_token == "RAD" and isinstance(phase, (float, int)):
            if not (-2 * math.pi <= phase <= 2 * math.pi):
                raise ValueError("phase must be >= -2 * pi and <= 2 * pi radians")
        elif unit_token == "SEC" and isinstance(phase, (float, int)):
            pass
        else:
            raise TypeError(f"phase must be a float, int or str, not {type(phase)}")
        self.write(f"SOURce{channel}:PHASe {phase},{unit_token}")

    def get_source_phase(self, channel: SourceChannel = SourceChannel.SINE) -> float:
        """Queries the current phase setting for the specified source channel.

        Sends the command:
            SOURce{channel}:PHASe?
        The instrument returns a numeric string indicating the current phase.

        Args:
            channel (SourceChannel): The source channel (1 for sine, 2 for aux, 3 for pulse).

        Returns:
            float: The current phase in degrees.

        See page 115 of the FS740 manual.
        """
        return float(self.query(f"SOURce{channel}:PHASe?"))

    # --- Status Subsystem (Pages 119-122) ---

    def query_status_gps_condition(self) -> GPSReceiverStatus:
        """Queries the GPS receiver status.

        Sends the command:
            STATus:GPS:CONDition?
        The instrument returns a string indicating the current status of the GPS receiver.

        Returns:
            str: The current GPS receiver status.

        See page 119 of the FS740 manual.
        """
        return GPSReceiverStatus(int(self.query("STATus:GPS:CONDition?")))

    def set_status_gps_enable(self, enable: int) -> None:
        if not 0 <= enable <= 0xFFFF:
            raise ValueError("enable mask must be between 0 and 65535")
        self.write(f"STATus:GPS:ENABle {enable}")

    def query_status_gps_enable(self) -> int:
        """Queries the GPS receiver enable status.

        Sends the command:
            STATus:GPS:ENABle?
        Queries the current mask. See section GPS Receiver Status on page 87 for
        detailed information on the interpretation of GPS receiver status. See section
        Status Reporting on page 80 for more information about enable registers.

        Returns:
            int: mask.

        See page 120 of the FS740 manual.
        """
        return int(self.query("STATus:GPS:ENABle?"))

    def query_status_gps_event(self) -> GPSReceiverStatus:
        """Queries the GPS receiver event status.

        Sends the command:
            STATus:GPS:EVENt?
        The instrument returns a string indicating the current event status of the GPS receiver.

        Returns:
            str: The current GPS receiver event status.

        See page 120 of the FS740 manual.
        """
        return GPSReceiverStatus(int(self.query("STATus:GPS:EVENt?")))

    def query_status_operation_condition(self) -> OperationStatus:
        """Queries the operation status.

        Sends the command:
            STATus:OPERation:CONDition?
        The instrument returns a string indicating the current operation status.

        Returns:
            str: The current operation status.

        See page 120 of the FS740 manual.
        """
        return OperationStatus(int(self.query("STATus:OPERation:CONDition?")))

    def set_status_operation_enable(self, mask: int) -> None:
        if not 0 <= mask <= 0xFFFF:
            raise ValueError("mask must be between 0 and 65535")
        self.write(f"STATus:OPERation:ENABle {mask}")

    def query_status_operation_enable(self) -> int:
        """Queries the operation status enable mask.

        Sends the command:
            STATus:OPERation:ENABle?
        Queries the current mask. See section Operation Status on page 86 for detailed
        information on the interpretation of operation status. See section Status Reporting
        on page 80 for more information about enable registers.

        Returns:
            int: mask.

        See page 121 of the FS740 manual.
        """
        return int(self.query("STATus:OPERation:ENABle?"))

    def query_status_operation_event(self) -> OperationStatus:
        """Queries the operation event status.

        Sends the command:
            STATus:OPERation:EVENt?
        The instrument returns a string indicating the current event status of the operation.

        Returns:
            str: The current operation event status.

        See page 121 of the FS740 manual.
        """
        return OperationStatus(int(self.query("STATus:OPERation:EVENt?")))

    def query_status_questionable_condition(self) -> QuestionableStatus:
        """Queries the questionable status.

        Sends the command:
            STATus:QUEStionable:CONDition?
        The instrument returns a string indicating the current questionable status.

        Returns:
            str: The current questionable status.

        See page 121 of the FS740 manual.
        """
        return QuestionableStatus(int(self.query("STATus:QUEStionable:CONDition?")))

    def set_status_questionable_enable(self, mask: int) -> None:
        if not 0 <= mask <= 0xFFFF:
            raise ValueError("mask must be between 0 and 65535")
        self.write(f"STATus:QUEStionable:ENABle {mask}")

    def query_status_questionable_enable(self) -> int:
        """Queries the questionable status enable mask.

        Sends the command:
            STATus:QUEStionable:ENABle?
        Queries the current mask. See section Questionable Status on page 85 for detailed
        information on the interpretation of questionable status. See section Status Reporting
        on page 80 for more information about enable registers.

        Returns:
            int: mask.

        See page 122 of the FS740 manual.
        """
        return int(self.query("STATus:QUEStionable:ENABle?"))

    def query_status_questionable_event(self) -> QuestionableStatus:
        """Queries the questionable event status.

        Sends the command:
            STATus:QUEStionable:EVENt?
        The instrument returns a string indicating the current event status of the questionable status.

        Returns:
            str: The current questionable event status.

        See page 122 of the FS740 manual.
        """
        return QuestionableStatus(int(self.query("STATus:QUEStionable:EVENt?")))

    # --- System Subsystem (Pages 122-132) ---

    def query_system_alarm(self) -> bool:
        """Queries the system alarm status.

        Sends the command:
            SYSTem:ALARm?
        The instrument returns a string indicating whether an alarm condition is present.

        Returns:
            bool: True if an alarm condition is present, False otherwise.

        See page 122 of the FS740 manual.
        """
        return bool(int(self.query("SYSTem:ALARm?")))

    def clear_system_alarm(self) -> None:
        """Clears the system alarm condition.

        Sends the command:
            SYSTem:ALARm:CLEar
        This command resets the alarm condition in the instrument.

        See page 123 of the FS740 manual.
        """
        self.write("SYSTem:ALARm:CLEar")

    # --- Timebase Subsystem (Pages 132-138) ---

    def set_timebase_config_bandwidth(self, bandwidth: str) -> None:
        """Sets the timebase bandwidth.

        Sends the command:
            TBASe:CONFig:BWIDth <value>
        where <value> is the desired bandwidth. This command configures the bandwidth of the timebase.

        Args:
            bandwidth (str): The desired bandwidth, either AUTo or MANual.

        See page 132 of the FS740 manual.
        """
        bandwidth = _normalize_choice(
            bandwidth, {"aut", "man", "auto", "manual"}, "bandwidth"
        )
        self.write(f"TBASe:CONFig:BWIDth {bandwidth}")

    def query_timebase_config_bandwidth(self) -> str:
        """Queries the timebase bandwidth.

        Sends the command:
            TBASe:CONFig:BWIDth?
        The instrument returns a string indicating the current timebase bandwidth.

        Returns:
            str: AUTo or MANual
        """
        return self.query("TBASe:CONFig:BWIDth?")

    def set_timebase_config_hmode(self, hmode: str) -> None:
        """
        Set the timebase holdover mode.
        Sends the command:
            TBASe:CONFig:HMODE <hmode>
        where <hmode> is the desired holdover mode. This command configures the holdover mode of the timebase.

        See page 133 of the manual.
        Args:
            hmode (str): WAIT, JUMP or SLEW
        """
        hmode = _normalize_choice(hmode, {"wait", "jump", "slew"}, "hmode")
        self.write(f"TBASe:CONFig:HMODE {hmode}")

    def query_timebase_config_hmode(self) -> str:
        """Queries the timebase holdover mode.

        Sends the command:
            TBASe:CONFig:HMODE?
        The instrument returns a string indicating the current holdover mode.

        Returns:
            str: The current holdover mode (WAIT, JUMP, SLEW).

        See page 133 of the FS740 manual.
        """
        return self.query("TBASe:CONFig:HMODE?")

    def set_timebase_config_lock(self, lock: int | bool | str) -> None:
        """
        Set the timebase lock status.
        Sends the command:
            TBASe:CONFig:LOCK <lock>
        where <lock> is the desired lock status. This command configures the lock status of the timebase.

        Args:
            lock (int | bool | str): Lock status, either 0 (unlocked), 1 (locked) or "ON" / "OFF".
        """
        if isinstance(lock, (int, bool)):
            if lock not in [0, 1]:
                raise ValueError("lock must be 0 (unlocked) or 1 (locked)")
            lock = "ON" if lock else "OFF"
        else:
            lock = _normalize_choice(lock, {"on", "off"}, "lock")
        self.write(f"TBASe:CONFig:LOCK {lock}")

    def query_timebase_config_lock(self) -> bool:
        """Queries the timebase lock status.

        Sends the command:
            TBASe:CONFig:LOCK?
        The instrument returns a string indicating whether the timebase is locked or unlocked.

        Returns:
            bool: True if the timebase is locked, False otherwise.

        See page 133 of the FS740 manual.
        """
        return bool(int(self.query("TBASe:CONFig:LOCK?")))

    def set_timebase_config_interval_limit(self, limit: float) -> None:
        """Sets the timebase interval limit.

        Sends the command:
            TBASe:CONFig:LIMit <limit>
        where <limit> is the desired interval limit in seconds. This command configures the maximum
        allowable time interval for the timebase.

        Args:
            limit (float): The desired interval limit in seconds.

        See page 133 of the FS740 manual.
        """
        if not (50e-9 <= limit <= 1):
            raise ValueError("limit must be >= 50 ns and <= 1 second")
        self.write(f"TBASe:CONFig:LIMit {limit}")

    def query_timebase_config_interval_limit(self) -> float:
        """Queries the timebase interval limit.

        Sends the command:
            TBASe:CONFig:LIMit?
        The instrument returns a numeric string indicating the current interval limit.

        Returns:
            float: The current interval limit in seconds.

        See page 133 of the FS740 manual.
        """
        return float(self.query("TBASe:CONFig:LIMit?"))

    def timebase_event_clear(self) -> None:
        """Clears the timebase event status.

        Sends the command:
            TBASe:EVENt:CLEar
        This command resets the timebase event status in the instrument.

        See page 134 of the FS740 manual.
        """
        self.write("TBASe:EVENt:CLEar")

    def query_timebase_event_count(self) -> int:
        """Queries the timebase event count.

        Sends the command:
            TBASe:EVENt:COUNt?
        The instrument returns a integer indicating the number of timebase events that have occurred.

        Returns:
            int: The current timebase event count.

        See page 134 of the FS740 manual.
        """
        return int(self.query("TBASe:EVENt:COUNt?"))
