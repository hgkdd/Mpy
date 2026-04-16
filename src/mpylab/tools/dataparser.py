# -*- coding: utf-8 -*-
"""
This is :mod:`mpylab.tools.dataparser`.

   Provides the class DataFile(Parser); used for dat files

   :author: Hans Georg Krauthäuser (main author)

   :license: GPLv3 or higher
"""

from mpylab.tools.plyparser import Parser
import math
from scuq import quantities, ucomponents
from mpylab.tools.uconv import UConv
from mpylab.tools.compare import cplx_key


class DatFile(Parser):
    """
    :class:`DatFile` is the parser for data files, e.g. with S-parameter values.

    A typical usage is like so::

        import sys
        import io
        import scuq
        from mpylab.tools.util import format_block
        from mpylab.tools.dataparser import DatFile

        name=None
        if len(sys.argv)>1:
            name=sys.argv[1]
        else:
            name=io.StringIO(format_block('''
                                                FUNIT: Hz
                                                UNIT: powerratio
                                                ABSERROR: [0.1, 1]
                                                10 [1, 0]
                                                11 1
                                                20 [0.9, 40]
                                                30 [0.8, 70]
                                                40 [0.7, 120]
                                                50 [0.6, 180]
                                                60 [0.5, 260]
                                                70 [0.4, 310]
                                                80 [0.3, 10]
                                                90 [0.2, 50]
                                                '''))

        DF=DatFile(filename=name)
        result=DF.run()
        ctx=scuq.ucomponents.Context()
        for f in sorted(result):
            uq=result[f]
            val,err,unit=ctx.value_uncertainty_unit(uq)
            print f, uq, val, err, unit

    """

    reserved = ('FUNIT',
                'UNIT',
                'RELERROR',
                'ABSERROR')

    tokens = reserved + (
                         'FPNUMBER',
                         'LBRACE',
                         'RBRACE',
                         'LSBRACE',
                         'RSBRACE',
                         'ID',
                         'COMMA',
                         'NEWLINE')

    t_LBRACE = r'\('
    t_RBRACE = r'\)'
    t_LSBRACE = r'\['
    t_RSBRACE = r'\]'
    t_COMMA = r','

    t_ignore_COMMENT = r'\#.*'

    # A string containing ignored characters (spaces and tabs)
    t_ignore = ' \t:'

    def __init__(self, **kw):
        self.funit = None
        self.fromunit = None
        self.tounit = None
        self.relerror = None
        self.abserror = None
        self.data = {}
        Parser.__init__(self, **kw)

    def _freq_conv(self):
        _, conv = UConv.get(self.funit)
        return conv

    def _from_unit(self):
        dim, conv = UConv.get(self.fromunit)
        return dim, conv

    def _from_conv(self):
        _, conv = self._from_unit()
        return conv

    # A regular expression rule with some action code

    def t_FPNUMBER(self, t):
        r'[+-]?[0-9]+(\.[0-9]+)?([eE][+-]?[0-9]+)?'
        try:
            t.value = float(t.value)
        except ValueError:
            print("Line %d: Number %s is too large!" % (t.lineno, t.value))
            t.value = 0
        return t

    def t_FUNIT(self, t):
        r'FUNIT:'
        return t

    def t_ID(self, t):
        r'[a-zA-Z][a-zA-Z0-9/]*'
        if t.value in self.reserved:
            t.type = t.value
        return t

    # Define a rule so we can track line numbers
    def t_NEWLINE(self, t):
        r'[\n\r]'
        t.lexer.lineno += 1
        return t

    # Error handling rule
    def t_error(self, t):
        print("Illegal character '%s'" % t.value[0])
        t.lexer.skip(1)

    # Parser starts here

    def p_lines_line(self, p):
        """lines : line lines
                | line"""
        p[0] = self.data

    def p_line_empty(self, p):
        r'line : NEWLINE'
        pass

    def p_line_funit(self, p):
        r'line : FUNIT idanycase NEWLINE'
        self.funit = p[2]

    def p_line_unit(self, p):
        """line : UNIT idanycase NEWLINE
                | UNIT idanycase idanycase NEWLINE"""
        if len(p) == 4:
            self.fromunit = self.tounit = p[2]
        elif len(p) == 5:
            self.fromunit = p[2]
            self.tounit = p[3]

    def p_idanycase_id(self, p):
        r'idanycase : ID'
        p[0] = p[1].lower()

    def p_line_relerr(self, p):
        r'line : RELERROR FPNUMBER NEWLINE'
        self.abserror = None
        self.relerror = float(p[2])

    def p_line_abserr(self, p):
        r'line : ABSERROR val NEWLINE'
        self.relerror = None
        self.abserror = p[2]

    def p_line_data1(self, p):
        r'line : FPNUMBER val val val NEWLINE'
        freq_conv = self._freq_conv()
        from_dim, _ = self._from_unit()

        freq = freq_conv(p[1])
        uq = self._makeuq(p[2], p[3], p[4], from_dim)

        if freq in self.data:
            raise ValueError(f"Duplicate frequency detected: {freq} (line {p.lineno(1)})")
        self.data[freq] = uq

    def p_line_data2(self, p):
        r'line : FPNUMBER val NEWLINE'
        freq_conv = self._freq_conv()
        from_dim, _ = self._from_unit()

        freq = freq_conv(p[1])
        v = p[2]
        s = 0
        if self.relerror is not None:
            s = v * self.relerror
        if self.abserror is not None:
            s = self.abserror

        ui = ucomponents.UncertainInput(v, s)
        uq = quantities.Quantity(from_dim, ui)

        if freq in self.data:
            raise ValueError(f"Duplicate frequency detected: {freq} (line {p.lineno(1)})")
        self.data[freq] = uq

    def p_val_number(self, p):
        r'val : number'
        p[0] = p[1]

    def p_number_fpnumber(self, p):
        r'number : FPNUMBER'
        from_conv = self._from_conv()
        p[0] = from_conv(p[1])

    def p_val_ri(self, p):
        r'val : LBRACE FPNUMBER COMMA FPNUMBER RBRACE'
        from_conv = self._from_conv()

        p2 = from_conv(p[2])
        p4 = from_conv(p[4])
        p[0] = complex(p2, p4)

    def p_val_ma(self, p):
        r'val : LSBRACE FPNUMBER COMMA FPNUMBER RSBRACE'
        from_conv = self._from_conv()

        m = from_conv(p[2])
        ang = float(p[4]) * math.pi / 180.0
        p[0] = complex(m * math.cos(ang), m * math.sin(ang))

    # Error rule for syntax errors
    def p_error(self, p):
        print("Syntax error in input!")

    def _makeuq(self, a, b, c, unit):
        l, v, u = sorted((a, b, c), key=cplx_key)
        delta = (u - l) * 0.5
        ui = ucomponents.UncertainInput(v, delta)
        return quantities.Quantity(unit, ui)

if __name__ == '__main__':
    import sys
    import io
    from mpylab.tools.util import format_block

    name = None
    if len(sys.argv) > 1:
        name = sys.argv[1]
    else:
        name = io.StringIO(format_block("""
                                            FUNIT: Hz
                                            UNIT: powerratio
                                            ABSERROR: [0.1, 1]
                                            10 [1, 0]
                                            11 1
                                            20 [0.9, 40]
                                            30 [0.8, 70]
                                            40 [0.7, 120]
                                            50 [0.6, 180]
                                            60 [0.5, 260]
                                            70 [0.4, 310]
                                            80 [0.3, 10]
                                            90 [0.2, 50]
                                            """))

    DF = DatFile(filename=name)
    result = DF.run()
    ctx = ucomponents.Context()
    for f in sorted(result):
        uq = result[f]
        val, err, unit = ctx.value_uncertainty_unit(uq)
        print(f, uq, val, err, unit)


    test_input = """FUNIT: Hz
    UNIT: powerratio
    ABSERROR: [0.1, 1]
    10 [1, 0]
    """

    DF = DatFile(filename=io.StringIO(test_input))
    result = DF.run()

    print("funit:", DF.funit)
    print("fromunit:", DF.fromunit)
    print("tounit:", DF.tounit)
    print("abserror:", DF.abserror)
    print("data keys:", sorted(result.keys()))