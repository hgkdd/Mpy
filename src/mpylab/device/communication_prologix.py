# -*- coding: utf-8 -*-
"""
This is the :mod:`mpylab.device.communication_prologix` module.

   :author: Hans Georg Krauthäuser (main author)

   :license: GPLv3 or higher
"""
import socket
import select
import threading

from mpylab.device.communication_generic import generic_read, generic_write, generic_query


class CommunicationPrologix:
    """CommunicationPrologix class."""
    def __init__(
        self,
        ip,
        port,
        gpib,
        bufsize=4096,
        TXEOL=b"\n",
        timeout_s=3,
        send_clr=False,
        send_ifc=False,
        encoding="ascii",
    ):
        """
        Kommunikation über einen PROLOGIX GPIB-Ethernet-Adapter.

        :param ip: IP-Adresse des Prologix-Adapters
        :param port: TCP-Port des Prologix-Adapters
        :param gpib: GPIB-Adresse des Zielgeräts
        :param bufsize: TCP-Receive-Buffergröße
        :param TXEOL: Zeilenende für Prologix-Befehle und SCPI-Kommandos
        :param timeout_s: Timeout in Sekunden
        :param send_clr: Wenn True, beim Initialisieren ++clr senden
        :param send_ifc: Wenn True, beim Initialisieren ++ifc senden
        :param encoding: Text-Encoding für Kommandos/Antworten
        """
        if not isinstance(ip, str) or not ip.strip():
            raise ValueError("ip must be a non-empty string")
        if not isinstance(port, int) or port <= 0:
            raise ValueError("port must be a positive integer")
        if not isinstance(gpib, int) or gpib < 0:
            raise ValueError("gpib must be a non-negative integer")
        if timeout_s <= 0:
            raise ValueError("timeout_s must be > 0")
        if bufsize <= 0:
            raise ValueError("bufsize must be > 0")
        if not isinstance(TXEOL, (bytes, bytearray)) or len(TXEOL) == 0:
            raise ValueError("TXEOL must be non-empty bytes")

        self.ip = ip
        self.port = port
        self.gpib = gpib
        self.bufsize = int(bufsize)
        self.TXEOL = bytes(TXEOL)
        self.timeout_s = float(timeout_s)
        self.send_clr = bool(send_clr)
        self.send_ifc = bool(send_ifc)
        self.encoding = encoding

        self._lock = threading.Lock()

        # Adapter einmal initialisieren
        with self._open_socket() as s:
            self._initialize_adapter(s)

    def _open_socket(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
        s.settimeout(self.timeout_s)
        s.connect((self.ip, self.port))
        return s

    def _send_line(self, sock, data):
        """
        Sendet bytes oder str immer mit TXEOL abgeschlossen.
        """
        if isinstance(data, str):
            data = data.encode(self.encoding)
        sock.sendall(data + self.TXEOL)

    def _recv_all_available(self, sock):
        """
        Liest alle verfügbaren Daten robust ein.
        Ende ist erreicht, wenn:
        - select() keine Lesebereitschaft mehr meldet
        - recv() keine Daten mehr liefert
        - weniger als bufsize Bytes empfangen wurden
        """
        chunks = []

        while True:
            ready, _, _ = select.select([sock], [], [], self.timeout_s)
            if not ready:
                break

            chunk = sock.recv(self.bufsize)
            if not chunk:
                break

            chunks.append(chunk)

            # Typischer Hinweis darauf, dass aktuell kein weiterer Block mehr anliegt
            if len(chunk) < self.bufsize:
                break

        return b"".join(chunks)

    def _initialize_adapter(self, sock):
        """
        Initialisiert den Prologix-Adapter.
        """
        self._send_line(sock, "++savecfg 0")  # nichts persistent ins EEPROM schreiben
        self._send_line(sock, "++mode 1")     # Controller-Modus
        self._send_line(sock, "++auto 0")     # kein read-after-write
        self._send_line(sock, f"++read_tmo_ms {int(self.timeout_s * 1000)}")
        self._send_line(sock, f"++addr {self.gpib}")

        if self.send_ifc:
            self._send_line(sock, "++ifc")

        if self.send_clr:
            self._send_line(sock, "++clr")

    def _prepare_transaction(self, sock):
        """
        Setzt vor jeder Transaktion mindestens die Zieladresse und das Read-Timeout.
        Das macht den Zugriff robuster, falls sich der Adapterzustand geändert hat.
        """
        self._send_line(sock, f"++addr {self.gpib}")
        self._send_line(sock, f"++read_tmo_ms {int(self.timeout_s * 1000)}")

    def write(self, cmd):
        """
        :param cmd: str, Kommando an das Instrument

        :return: int, Anzahl der gesendeten Zeichen des Nutzkommandos
        """
        def write_fn(cmd_to_send):
            with self._lock:
                with self._open_socket() as s:
                    self._prepare_transaction(s)
                    self._send_line(s, cmd_to_send)
            return len(cmd_to_send)

        return generic_write(write_fn, cmd)

    def read(self, tmpl=None):
        """
        :param tmpl: str oder None, Regex-Pattern für generic_read

        :return: str oder dict oder None
        """
        def read_fn():
            with self._lock:
                with self._open_socket() as s:
                    self._prepare_transaction(s)
                    self._send_line(s, "++read eoi")
                    raw = self._recv_all_available(s)

            if not raw:
                raise TimeoutError("No response received from device via Prologix adapter.")

            return raw.decode(self.encoding, errors="replace").strip()

        return generic_read(read_fn, tmpl)

    def query(self, cmd, tmpl=None, send_opc=False):
        """
        :param cmd: str, Kommando an das Instrument
        :param tmpl: str oder None, Regex-Pattern für generic_query
        :param send_opc: bool, append ``; *OPC?`` to a non-query command

        :return: str oder dict oder None
        """
        def query_fn(cmd_to_send):
            with self._lock:
                with self._open_socket() as s:
                    self._prepare_transaction(s)
                    self._send_line(s, cmd_to_send)
                    self._send_line(s, "++read eoi")
                    raw = self._recv_all_available(s)

            if not raw:
                raise TimeoutError(
                    f"No response received for query '{cmd_to_send}' from device via Prologix adapter."
                )

            return raw.decode(self.encoding, errors="replace").strip()

        return generic_query(query_fn, cmd, tmpl, send_opc)

    def close(self):
        """close method."""
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()


if __name__ == "__main__":
    import time
    from mpylab.device.prologix_simulator import start_prologix_simulator
    HOST = "127.0.0.1"
    PORT = 1234
    GPIB_ADDR = 5

    print(f"Starte PROLOGIX-Simulator auf {HOST}:{PORT} ...")
    sim = start_prologix_simulator(HOST, PORT)
    time.sleep(0.1)

    try:
        print("Verbinde Test-Client ...")
        comm = CommunicationPrologix(
            ip=HOST,
            port=PORT,
            gpib=GPIB_ADDR,
            timeout_s=1.5,
            send_clr=False,
            send_ifc=False,
        )

        print("\n--- Direkte Tests ---")
        print("IDN:", comm.query("*IDN?"))
        print("MEAS:VOLT?:", comm.query("MEAS:VOLT?"))
        print("MEAS:CURR?:", comm.query("MEAS:CURR?"))
        print("OPC nach CONF:VOLT:", comm.query("CONF:VOLT", send_opc=True))

        comm.write("CONF:VOLT")
        print("READ? nach CONF:VOLT:", comm.query("READ?"))

        comm.write("CONF:CURR")
        print("READ? nach CONF:CURR:", comm.query("READ?"))

        comm.write("OUTP ON")
        print("OUTP?:", comm.query("OUTP?"))

        print("\n--- Regex-Test für generic_read/generic_query ---")
        result = comm.query("MEAS:VOLT?", tmpl=r"(?P<volt>\d+\.\d+)")
        print("Regex-Ergebnis:", result)

        print("\n--- Sicherheits-Test send_opc bei Query ---")
        try:
            comm.query("MEAS:VOLT?", send_opc=True)
        except ValueError as exc:
            print("Erwarteter Fehler:", exc)

        print("\n--- Fehlerfall ---")
        comm.write("FOO:BAR")
        print("SYST:ERR?:", comm.query("SYST:ERR?"))

        print("\n--- Manueller Read-Test ---")
        comm.write("*IDN?")
        print("read():", comm.read())

        print("\nSimulator läuft. Mit Strg+C beenden.")
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nBeende ...")
    finally:
        sim.shutdown()
        sim.server_close()
