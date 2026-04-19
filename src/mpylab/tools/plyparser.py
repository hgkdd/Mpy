#!/usr/bin/env python

import os
import io
import re
import textwrap

import ply.lex as lex
import ply.yacc as yacc

from mpylab.tools.util import format_block, locate
from mpylab.tools.regular_expressions import _INLINE_FILE_RE


class Parser:
    """
    Base class for a lexer/parser that has the rules defined as methods
    """
    tokens = ()
    precedence = ()

    def __init__(self, **kw):
        self.debug = kw.get('debug', 0)
        self.filename = kw.get('filename', None)
        self.SearchPaths = kw.get('SearchPaths', None)
        if self.SearchPaths is None:
            self.SearchPaths = [os.getcwd()]
        self.names = {}
        try:
            modname = os.path.split(os.path.splitext(__file__)[0])[1] + "_" + self.__class__.__name__
        except:
            modname = "parser" + "_" + self.__class__.__name__
        self.debugfile = modname + ".dbg"
        self.tabmodule = modname + "_" + "parsetab"
        # print self.debugfile, self.tabmodule

        # Build the lexer and parser
        lex.lex(module=self, debug=self.debug)
        yacc.yacc(module=self,
                  debug=self.debug,
                  debugfile=self.debugfile,
                  tabmodule=self.tabmodule)

    def _read_input_source(self, source):
        """
        Read parser input from one of these sources:

        - file-like object with .read()
        - direct file path
        - file name resolvable via locate(...)
        - legacy inline StringIO expression of the form
          io.StringIO(format_block(''' ... '''))
        """
        # 1) file-like object
        try:
            return source.read()
        except AttributeError:
            pass

        # 2) direct file path
        if isinstance(source, str) and os.path.isfile(source):
            with open(source, "r", encoding="utf-8") as f:
                return f.read()

        # 3) file name via SearchPaths / locate
        try:
            path = next(locate(source, paths=self.SearchPaths))
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except (OSError, StopIteration, TypeError):
            pass

        # 4) legacy inline data file syntax without eval()
        if isinstance(source, str):
            m = _INLINE_FILE_RE.match(source.strip())
            if m:
                raw_block = m.group(2)
                try:
                    return format_block(raw_block)
                except Exception:
                    import textwrap
                    return textwrap.dedent(raw_block).strip()

        raise ValueError(
            f"Unsupported parser input source: {source!r}. "
            f"Expected file-like object, readable file path, or inline StringIO data block."
        )

    def run(self):
        if self.filename:
            data = self._read_input_source(self.filename)
            self.parseresult = yacc.parse(data)
        else:
            while True:
                try:
                    s = input('input > ')
                except EOFError:
                    break
                if not s:
                    continue
                self.parseresult = yacc.parse(s)
        return self.parseresult
        # parser = yacc.yacc()
        # if self.filename:
            # try:
            #     data = self.filename.read()  # file like object
            # except AttributeError:
            #     try:
            #         # paths=get_var_from_nearest_outerframe('SearchPaths')
            #         # print self.SearchPaths, self.filename, locate(self.filename, paths=self.SearchPaths).next()
            #         data = open(next(locate(self.filename, paths=self.SearchPaths))).read()  # name of an existing file
            #     except (IOError, StopIteration):
            #         data = eval(self.filename).read()  # eval to a file like object
            # self.parseresult = yacc.parse(data)
        # else:
        #     while 1:
        #         try:
        #             s = eval(input('input > '))
        #         except EOFError:
        #             break
        #         if not s:
        #             continue
        #         self.parseresult = yacc.parse(s)
        # return self.parseresult

if __name__ == "__main__":
    import io
    import os
    import tempfile

    class DummyParser(Parser):
        """
        Minimaler Test-Parser nur für _read_input_source().
        PLY wird hier bewusst nicht initialisiert.
        """

        def __init__(self, **kw):
            self.debug = kw.get('debug', 0)
            self.filename = kw.get('filename', None)
            self.SearchPaths = kw.get('SearchPaths', None)
            if self.SearchPaths is None:
                self.SearchPaths = [os.getcwd()]
            self.names = {}
            self.parseresult = None

        def run(self):
            if self.filename:
                data = self._read_input_source(self.filename)
                self.parseresult = data
            else:
                self.parseresult = None
            return self.parseresult

    def test_parser_sources():
        print("=== test_parser_sources ===")

        # 1. echtes file-like Objekt (StringIO)
        src1 = io.StringIO("alpha\nbeta\ngamma\n")
        p = DummyParser(filename=src1)
        out = p.run()
        assert "alpha" in out
        assert "gamma" in out
        print("StringIO test passed")

        # 2. temporäre Datei
        with tempfile.NamedTemporaryFile(
            mode="w",
            delete=False,
            encoding="utf-8"
        ) as tf:
            tf.write("delta\nepsilon\n")
            fname = tf.name

        try:
            p = DummyParser(filename=fname)
            out = p.run()
            assert "delta" in out
            assert "epsilon" in out
            print("file path test passed")
        finally:
            os.unlink(fname)

        # 3. Legacy inline StringIO expression
        legacy = r"""
io.StringIO(format_block('''
one
two
three
'''))
"""
        p = DummyParser(filename=legacy)
        out = p.run()
        assert "one" in out
        assert "three" in out
        print("legacy inline StringIO test passed")

        # 4. Fehlerfall
        try:
            p = DummyParser(filename=12345)
            p.run()
            raise AssertionError("Expected ValueError")
        except ValueError:
            print("invalid source test passed")

        print("test_parser_sources passed")

    test_parser_sources()