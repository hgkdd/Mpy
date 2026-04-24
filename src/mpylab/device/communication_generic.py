# -*- coding: utf-8 -*-
"""
This is the :mod:`mpylab.device.communication_generic` module.

   :author: Hans Georg Krauthäuser (main author)

   :license: GPLv3 or higher
"""
import re


def generic_write(write_fn, cmd):
    """
    :param write_fn: function to write to the device
    :param cmd: *str*, command to send

    :return: *int*: status code; number of bytes sent or 0
    """
    stat = 0  # 0 is returned if no write_fn or cmd isn't a str
    if write_fn and isinstance(cmd, str):
        cmd_str = cmd.strip()
        if cmd_str:
            stat = write_fn(cmd_str)
    return stat


def generic_read(read_fn, tmpl=None):
    r"""
    :param read_fn: device read function
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
    dct = None
    if read_fn:
        ans = read_fn()
        if tmpl is None:
            return ans   # tmpl None -> return whatever read() had given
        if ans is None:
            return None
        m = re.match(tmpl, ans)  # parse the answer
        if m:
            dct = m.groupdict()
    return dct


def generic_query(query_fn, cmd, tmpl=None, send_opc=False):
    """
    :param query_fn: device query function
    :param cmd: *str*, command to send
    :param tmpl: *str*, a re pattern for re.match or None
    :param send_opc: *bool*, append ``; *OPC?`` to a non-query command
                            and return the resulting response (usually '1')
    :return: *str or dict or None*: dict with the parsed result

    Safety rule:
    send_opc=True is only allowed for commands that do not already contain
    a query marker '?', because ``<query>; *OPC?`` may create multiple responses
    and is transport- / instrument-dependent.
    """
    dct = None
    if query_fn and isinstance(cmd, str):
        cmd_str = cmd.strip()
        if not cmd_str:
            return None

        if send_opc:
            if "?" in cmd_str:
                raise ValueError(
                    "send_opc=True is not allowed for query commands containing '?'. "
                    "Use send_opc only with non-query commands."
                )
            cmd_str = f"{cmd_str}; *OPC?"

        ans = query_fn(cmd_str)
        if tmpl is None:
            return ans
        if ans is None:
            return None
        m = re.match(tmpl, ans)
        if m:
            dct = m.groupdict()
    return dct

if __name__ == "__main__":
    print("--- communication_generic Selbsttest ---")

    written_commands = []
    read_queue = ["Voltage: 5.123 V", "READY", None]
    query_answers = {
        "*IDN?": "FAKE,MODEL-1234,SN0001,1.0",
        "CONF:VOLT; *OPC?": "1",
        "MEAS:VOLT?": "5.123",
    }

    def fake_write(cmd):
        written_commands.append(cmd)
        return len(cmd)

    def fake_read():
        if not read_queue:
            return None
        return read_queue.pop(0)

    def fake_query(cmd):
        return query_answers.get(cmd, '0,"Unknown command"')

    print("\nWrite-Test")
    stat = generic_write(fake_write, "CONF:VOLT")
    print("Status:", stat)
    print("Gesendete Kommandos:", written_commands)

    print("\nRead-Test ohne Regex")
    ans = generic_read(fake_read)
    print("Antwort:", ans)

    print("\nRead-Test mit Regex")
    dct = generic_read(fake_read, tmpl=r"(?P<state>READY)")
    print("Regex-Ergebnis:", dct)

    print("\nRead-Test auf None")
    dct = generic_read(fake_read, tmpl=r"(?P<any>.*)")
    print("Regex-Ergebnis:", dct)

    print("\nQuery-Test ohne Regex")
    ans = generic_query(fake_query, "*IDN?")
    print("Antwort:", ans)

    print("\nQuery-Test mit Regex")
    dct = generic_query(fake_query, "MEAS:VOLT?", tmpl=r"(?P<volt>\d+\.\d+)")
    print("Regex-Ergebnis:", dct)

    print("\nQuery-Test mit send_opc für Nicht-Query")
    ans = generic_query(fake_query, "CONF:VOLT", send_opc=True)
    print("Antwort:", ans)

    print("\nSicherheitstest: send_opc bei Query muss fehlschlagen")
    try:
        generic_query(fake_query, "MEAS:VOLT?", send_opc=True)
    except ValueError as exc:
        print("Erwarteter Fehler:", exc)

    print("\nSelbsttest abgeschlossen.")
