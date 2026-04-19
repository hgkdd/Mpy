# -*- coding: utf-8 -*-
"""
This is the :mod:`mpylab.device.communication_gpib` module.

   :author: Hans Georg Krauthäuser (main author)

   :license: GPLv3 or higher
"""
import pyvisa
import pyvisa.constants

from mpylab.device.communication_generic import generic_read, generic_write, generic_query


class CommunicationGpib:
    def __init__(self, res_name,
                 lock=None,
                 timeout_s=3,
                 chunk_size=20480,
                 query_delay_s=0,
                 send_end=True,
                 read_term=None,
                 write_term=None):
        """
        :param res_name: pyvisa resource name string, e.g. "GPIB::22::INSTR"
        :param lock: pyvisa.constants.AccessModes, default is no_lock
        :param timeout_s: *float*, timeout in seconds, default is 3
        :param chunk_size: *int*, chunk size in bytes, default is 20480
        :param query_delay_s: *float*, query delay in seconds, default is 0
        :param send_end: *bool*, send end command (EOI) after command, default is True
        :param read_term: *str*, read termination character, default is None
        :param write_term: *str*, write termination character, default is None
        """
        if lock is None:
            lock = pyvisa.constants.AccessModes.no_lock
        if not isinstance(res_name, str) or not res_name.strip():
            raise ValueError("res_name must be a non-empty string")
        if timeout_s <= 0:
            raise ValueError("timeout_s must be > 0")
        if chunk_size <= 0:
            raise ValueError("chunk_size must be > 0")
        if query_delay_s < 0:
            raise ValueError("query_delay_s must be >= 0")

        self.rm = pyvisa.ResourceManager()  # configure backend in .pyvisarc in your home dir
        self.dev = self.rm.open_resource(res_name, access_mode=lock, send_end=send_end)
        self.dev.timeout = int(timeout_s * 1000)
        self.dev.chunk_size = int(chunk_size)
        self.dev.query_delay = float(query_delay_s)

        if write_term is not None:
            self.dev.write_termination = write_term
        if read_term is not None:
            self.dev.read_termination = read_term

    def write(self, cmd):
        """
        :param cmd: *str*, command to send

        :return: *int*: status code; number of bytes sent or 0
        """
        return generic_write(self.dev.write, cmd)

    def read(self, tmpl=None):
        """
        :param tmpl: *str*, a re pattern for re.match or None

        :return: *str or dict or None*: dict with the parsed result
                                        or raw result as str
                                        or None if no match

        This is how the pattern works:
        tmpl = r'Test (?P<dbval>\d+) dB'  # \d+ matches decimals; here 3 and 0; this is stored with key dbval
        m = re.match(tmpl, 'Test 30 dB')
        m['dbval']  ->  '30'   # access only one 'named' match
        m.groupdict()  ->  {'dbval': '30'}  # access all 'named' matches
        """
        return generic_read(self.dev.read, tmpl)

    def query(self, cmd, tmpl=None, send_opc=False):
        """
        :param cmd: *str*, command to send
        :param tmpl: *str*, a re pattern for re.match or None
        :param send_opc: *bool*, append '; *OPC?' to a non-query command
        :return: *str or dict or None*: dict with the parsed result

        See read function for more explanation regarding the re pattern
        """
        return generic_query(self.dev.query, cmd, tmpl, send_opc)

if __name__ == "__main__":
    print("--- communication_gpib Demo mit Fake-VISA-Device ---")

    class _FakeVisaDevice:
        def __init__(self):
            self.timeout = None
            self.chunk_size = None
            self.query_delay = None
            self.write_termination = None
            self.read_termination = None
            self.written = []
            self.mode = "VOLT"
            self.output_enabled = False
            self.last_error = '0,"No error"'

        def write(self, cmd):
            self.written.append(cmd)
            upper = cmd.strip().upper()

            if upper == "CONF:VOLT":
                self.mode = "VOLT"
            elif upper == "CONF:CURR":
                self.mode = "CURR"
            elif upper == "OUTP ON":
                self.output_enabled = True
            elif upper == "OUTP OFF":
                self.output_enabled = False
            elif upper.startswith("FOO"):
                self.last_error = f'-100,"Unknown command: {cmd}"'

            return len(cmd)

        def read(self):
            return "READBACK"

        def query(self, cmd):
            upper = cmd.strip().upper()

            if upper == "*IDN?":
                return "FAKE,MODEL-1234,SN0001,1.0"
            if upper == "MEAS:VOLT?":
                return "5.123"
            if upper == "MEAS:CURR?":
                return "0.456"
            if upper == "READ?":
                return "5.123" if self.mode == "VOLT" else "0.456"
            if upper == "OUTP?":
                return "1" if self.output_enabled else "0"
            if upper == "SYST:ERR?":
                return self.last_error
            if upper == "CONF:VOLT; *OPC?":
                self.mode = "VOLT"
                return "1"
            if upper == "CONF:CURR; *OPC?":
                self.mode = "CURR"
                return "1"

            return '-100,"Unknown command"'

    class _FakeResourceManager:
        def __init__(self):
            self.last_resource = None
            self.last_access_mode = None
            self.last_send_end = None
            self.dev = _FakeVisaDevice()

        def open_resource(self, res_name, access_mode=None, send_end=True):
            self.last_resource = res_name
            self.last_access_mode = access_mode
            self.last_send_end = send_end
            return self.dev

    original_rm = pyvisa.ResourceManager
    fake_rm = _FakeResourceManager()

    try:
        pyvisa.ResourceManager = lambda: fake_rm

        comm = CommunicationGpib(
            "GPIB::22::INSTR",
            timeout_s=1.5,
            chunk_size=8192,
            query_delay_s=0.1,
            send_end=True,
            read_term="\n",
            write_term="\n",
        )

        print("\nInitialisierung")
        print("Resource:", fake_rm.last_resource)
        print("Timeout [ms]:", comm.dev.timeout)
        print("Chunk size:", comm.dev.chunk_size)
        print("Query delay [s]:", comm.dev.query_delay)
        print("Write termination:", repr(comm.dev.write_termination))
        print("Read termination:", repr(comm.dev.read_termination))

        print("\nDirekte Tests")
        print("IDN:", comm.query("*IDN?"))
        print("MEAS:VOLT?:", comm.query("MEAS:VOLT?"))
        print("MEAS:CURR?:", comm.query("MEAS:CURR?"))
        print("OPC nach CONF:VOLT:", comm.query("CONF:VOLT", send_opc=True))

        comm.write("CONF:CURR")
        print("READ? nach CONF:CURR:", comm.query("READ?"))

        comm.write("OUTP ON")
        print("OUTP?:", comm.query("OUTP?"))

        print("\nRegex-Test")
        result = comm.query("MEAS:VOLT?", tmpl=r"(?P<volt>\d+\.\d+)")
        print("Regex-Ergebnis:", result)

        print("\nSicherheitstest: send_opc bei Query muss fehlschlagen")
        try:
            comm.query("MEAS:VOLT?", send_opc=True)
        except ValueError as exc:
            print("Erwarteter Fehler:", exc)

        print("\nFehlerfall")
        comm.write("FOO:BAR")
        print("SYST:ERR?:", comm.query("SYST:ERR?"))

        print("\nGesendete write-Kommandos:", comm.dev.written)

    finally:
        pyvisa.ResourceManager = original_rm
