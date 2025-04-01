from enum import IntEnum
from typing import Self, cast

import pyvisa
from pyvisa.resources import TCPIPSocket


class Channel(IntEnum):
    FRONT = 1
    REAR = 2


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

    def set_event_enable(self, value: int) -> None:
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

    def query_event_status(self) -> str:
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
            str: A string representing the ESR contents (usually as a numeric value).

        See page 91 of the FS740 manual.
        """
        return self.query("*ESR?")

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

        Args:
            value (int): The value to set for the PSC flag.

        See page 93 of the FS740 manual.
        """
        self.write(f"*PSC {value}")

    def recall_settings(self, slot: int) -> None:
        """Recalls instrument settings from a specified storage slot.

        Sends the *RCL command to load settings previously saved in the specified slot.
        This command allows quick reconfiguration of the instrument.

        Args:
            slot (int): The storage slot number (typically 0–9).

        See page 93 of the FS740 manual.
        """
        self.write(f"*RCL {slot}")

    def reset(self) -> None:
        """Resets the instrument to its factory default settings.

        Sends the *RST command, which resets the instrument's settings. Some nonvolatile settings
        may persist depending on the instrument's design.

        See page 93 of the FS740 manual.
        """
        self.write("*RST")

    def save_settings(self, slot: int) -> None:
        """Saves the current instrument settings to a specified storage slot.

        Sends the *SAV command with the given slot number, storing the current configuration
        so it can be recalled later using the *RCL command.

        Args:
            slot (int): The storage slot number where settings will be saved.

        See page 93 of the FS740 manual.
        """
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

    def query_serial_poll_status(self) -> str:
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
            str: A string representing the contents of the STB register.

        See page 82 of the FS740 manual for detailed information on the STB.
        """
        return self.query("*STB?")

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

    def measure_frequency(self, channel: Channel = Channel.FRONT) -> str:
        """Queries the current frequency measurement for the specified input.

        Sends the command:
            MEASure{channel}:FREQuency?
        The instrument returns the measured frequency (with 1 μHz resolution, etc.) from the
        specified measurement input.

        Args:
            channel (int, optional): Measurement input channel (1 for front, 2 for rear). Defaults to 1.

        Returns:
            str: The measured frequency as a numeric string.

        See page 96 of the FS740 manual.
        """
        return self.query(f"MEASure{channel}:FREQuency?")

    def measure_time(self, channel: Channel = Channel.FRONT) -> str:
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
        return self.query(f"MEASure{channel}:TIMe?")

    def measure_query_config(self, channel: Channel = Channel.FRONT) -> str:
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
        self, channel: Channel = Channel.FRONT, config: str = ""
    ) -> None:
        """Configures the frequency measurement parameters for the specified input.

        Sends the command:
            CONFigure{channel}:FREQuency {config}
        The configuration string should follow the syntax detailed on page 97 (for example, specifying
        gate time and sample count).

        Args:
            channel (int, optional): Measurement input channel (1 for front, 2 for rear). Defaults to 1.
            config (str): A string with the frequency measurement configuration parameters.

        See page 97 of the FS740 manual.
        """
        self.write(f"CONFigure{channel}:FREQuency {config}")

    def measure_configure_time(
        self, channel: Channel = Channel.FRONT, config: str = ""
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

    def measure_initiate(self, channel: Channel = Channel.FRONT) -> None:
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

    def measure_fetch(self, channel: Channel = Channel.FRONT) -> str:
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

    def measure_abort(self, channel: Channel = Channel.FRONT) -> None:
        """Aborts the ongoing measurement for the specified input.

        Sends the command:
            ABORt{channel}
        This immediately halts an in-progress measurement. Data already captured may remain in the buffer.

        Args:
            channel (int, optional): Measurement input channel (1 or 2). Defaults to 1.

        See page 99 of the FS740 manual.
        """
        self.write(f"ABORt{channel}")

    def measure_stop(self, channel: Channel = Channel.FRONT) -> None:
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

    def data_query_count(self, channel: Channel = Channel.FRONT) -> str:
        """Queries the total number of data measurements completed for a specified channel.

        Sends the command:
            DATA{channel}:COUNt?
        where {channel} is either 1 (front) or 2 (rear).

        Args:
            channel (int, optional): The data channel to query (1 for front, 2 for rear). Defaults to 1.

        Returns:
            str: A numeric string representing the total data count.

        See page 102 of the FS740 manual.
        """
        return self.query(f"DATA{channel}:COUNt?")

    def data_query_points(self, channel: Channel = Channel.FRONT) -> str:
        """Queries the number of valid data points available for reading from internal
        memory for a specified channel.

        Sends the command:
            DATA{channel}:POINts?
        where {channel} is either 1 (front) or 2 (rear).

        Args:
            channel (int, optional): The data channel to query (1 for front, 2 for rear). Defaults to 1.

        Returns:
            str: A numeric string representing the number of available data points.

        See page 102 of the FS740 manual.
        """
        return self.query(f"DATA{channel}:POINts?")

    def data_read(
        self, channel: Channel = Channel.FRONT, index: int = 0, count: int = 1
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

    def data_remove(self, channel: Channel = Channel.FRONT, count: int = 1) -> str:
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

    # --- Sample Subsystem (Pages 111-112) ---

    def sample_set_count(self, count: int = 1) -> None:
        """Sets the number of samples to acquire in a measurement.

        Sends the command:
            SAMPle:COUNt <value>
        where <value> is the desired sample count. This command determines how many samples
        (data points) will be acquired during a measurement before it completes.

        Args:
            count (int): The desired number of samples.

        See page 111 of the FS740 manual.
        """
        self.write(f"SAMPle:COUNt {count}")

    def sample_query_count(self) -> str:
        """Queries the current sample count setting.

        Sends the command:
            SAMPle:COUNt?
        The instrument returns a numeric string indicating the number of samples configured
        for measurement.

        Returns:
            str: A numeric string representing the current sample count.

        See page 111 of the FS740 manual.
        """
        return self.query("SAMPle:COUNt?")
