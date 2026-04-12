# -*- coding: utf-8 -*-
"""
This is the :mod:`mpylab.device.communication_debug` module.

   :author: Hans Georg Krauthäuser (main author)

   :license: GPLv3 or higher
"""
from mpylab.device.communication_generic import generic_read, generic_write, generic_query


class CommunicationDebug:
    def __init__(self, idn, fout=None, fin=None):
        """
        :param idn: *str*, device identifier
        :param fout: file name for the write command or None; None means stdout
        :param fin: file name for the read command or None; None means stdin
        """
        if not isinstance(idn, str) or not idn.strip():
            raise ValueError("idn must be a non-empty string")

        self.idn = idn
        self.fout = fout
        self.inlines = None
        self.n_inlines = 0
        self.infile_exhausted = True
        self.next_inline = 0

        if fin is not None:
            with open(fin, "r", encoding="utf-8") as f:
                self.inlines = f.readlines()
            self.n_inlines = len(self.inlines)
            self.infile_exhausted = (self.n_inlines == 0)

    def write(self, cmd):
        """
        :param cmd: *str*, command to send

        :return: *int*: status code; number of bytes sent or 0
        """
        cmd_str = f"{self.idn} out: {cmd}"

        if self.fout:
            with open(self.fout, "a", encoding="utf-8") as f:
                def write_fn(s):
                    return f.write(s + "\n")
                stat = generic_write(write_fn, cmd_str)
        else:
            def write_fn(s):
                print(s)
                return len(s)
            stat = generic_write(write_fn, cmd_str)

        return stat

    def read(self, tmpl=None):
        """
        :param tmpl: *str*, a re pattern for re.match or None

        :return: *str or dict or None*: dict with the parsed result
                                        or raw result as str
                                        or None if no match
        """
        if self.infile_exhausted:
            def read_fn():
                return input(f"{self.idn} in: ({tmpl=}) -> ")
        else:
            def read_fn():
                ans = self.inlines[self.next_inline].rstrip("\\r\\n")
                self.next_inline += 1
                if self.next_inline >= self.n_inlines:
                    self.infile_exhausted = True
                return ans

        return generic_read(read_fn, tmpl)

    def query(self, cmd, tmpl=None, send_opc=False):
        """
        :param cmd: *str*, command to send
        :param tmpl: *str*, a re pattern for re.match or None
        :param send_opc: *bool*, append '; *OPC?' to a non-query command
        :return: *str or dict or None*: dict with the parsed result

        See read function for more explanation regarding the re pattern
        """
        def query_fn(cmd_str):
            self.write(cmd_str)
            return self.read()

        return generic_query(query_fn, cmd, tmpl, send_opc)

if __name__ == '__main__':
    from mpylab.tools.regular_expressions import FP  # float regex, not anchored

    comm_sg = CommunicationDebug(idn='SG')

    print("OPC:", comm_sg.query('RST', send_opc=True))
    dct = comm_sg.query('*IDN?')
    print(dct)
    dct = comm_sg.query('FREQ?', tmpl=fr'FREQUENCY (?P<freq>{FP}) HZ')
    print(dct)