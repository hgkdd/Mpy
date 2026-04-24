"""mpylab.device.prologix_simulator module."""
import socketserver
import threading

class _FakeGpibInstrument:
    """
    Simuliert ein einfaches SCPI/GPIB-Instrument.
    """

    def __init__(self):
        self.reset()

    def reset(self):
        self.mode = "VOLT"
        self.last_error = '0,"No error"'
        self.output_enabled = False

    def handle(self, cmd: str):
        cmd = cmd.strip()
        if not cmd:
            return None

        upper = cmd.upper()

        if upper == "*IDN?":
            return "FAKE,MODEL-1234,SN0001,1.0"

        if upper == "*OPC?":
            return "1"

        if upper == "*RST":
            self.reset()
            return None

        if upper == "SYST:ERR?":
            return self.last_error

        if upper == "MEAS:VOLT?":
            return "5.123"

        if upper == "MEAS:CURR?":
            return "0.456"

        if upper == "READ?":
            if self.mode == "VOLT":
                return "5.123"
            if self.mode == "CURR":
                return "0.456"
            return "0"

        if upper == "CONF:VOLT":
            self.mode = "VOLT"
            return None

        if upper == "CONF:CURR":
            self.mode = "CURR"
            return None

        if upper == "OUTP ON":
            self.output_enabled = True
            return None

        if upper == "OUTP OFF":
            self.output_enabled = False
            return None

        if upper == "OUTP?":
            return "1" if self.output_enabled else "0"

        self.last_error = f'-100,"Unknown command: {cmd}"'
        return None


class _ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


class _PrologixSimulatorHandler(socketserver.StreamRequestHandler):
    def setup(self):
        super().setup()
        self.server_state = self.server.shared_state
        self.addr = self.server_state["default_addr"]
        self.read_tmo_ms = self.server_state["default_read_tmo_ms"]
        self.auto = 0
        self.mode = 1

    def handle(self):
        while True:
            raw = self.rfile.readline()
            if not raw:
                break

            line = raw.decode("ascii", errors="replace").strip()
            if not line:
                continue

            if line.startswith("++"):
                self._handle_prologix_command(line)
            else:
                self._handle_instrument_command(line)

    def _handle_prologix_command(self, line: str):
        parts = line.split()
        cmd = parts[0].lower()

        if cmd == "++savecfg":
            return

        if cmd == "++mode":
            if len(parts) >= 2:
                try:
                    self.mode = int(parts[1])
                except ValueError:
                    pass
            return

        if cmd == "++auto":
            if len(parts) >= 2:
                try:
                    self.auto = int(parts[1])
                except ValueError:
                    pass
            return

        if cmd == "++read_tmo_ms":
            if len(parts) >= 2:
                try:
                    self.read_tmo_ms = int(parts[1])
                except ValueError:
                    pass
            return

        if cmd == "++addr":
            if len(parts) >= 2:
                try:
                    self.addr = int(parts[1])
                except ValueError:
                    pass
            return

        if cmd == "++clr":
            instr = self.server_state["devices"].setdefault(self.addr, _FakeGpibInstrument())
            instr.reset()
            self.server_state["pending_responses"][self.addr] = b""
            return

        if cmd == "++ifc":
            self.server_state["pending_responses"].clear()
            return

        if cmd == "++read":
            pending = self.server_state["pending_responses"].get(self.addr, b"")
            if pending:
                self.wfile.write(pending + b"\n")
                self.wfile.flush()
                self.server_state["pending_responses"][self.addr] = b""
            return

    def _handle_instrument_command(self, line: str):
        instr = self.server_state["devices"].setdefault(self.addr, _FakeGpibInstrument())
        response = instr.handle(line)

        if response is not None:
            pending = response.encode("ascii", errors="replace")
            self.server_state["pending_responses"][self.addr] = pending

            if self.auto:
                self.wfile.write(pending + b"\n")
                self.wfile.flush()
                self.server_state["pending_responses"][self.addr] = b""
        else:
            self.server_state["pending_responses"][self.addr] = b""


def start_prologix_simulator(host="127.0.0.1", port=1234):
    """start_prologix_simulator function."""
    server = _ThreadedTCPServer((host, port), _PrologixSimulatorHandler)
    server.shared_state = {
        "default_addr": 5,
        "default_read_tmo_ms": 3000,
        "devices": {
            5: _FakeGpibInstrument(),
            12: _FakeGpibInstrument(),
        },
        "pending_responses": {},
    }

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server

