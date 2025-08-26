#!/usr/bin/env python

import os
import io

import ply.lex as lex
import ply.yacc as yacc

from mpylab.tools.util import locate
from mpylab.tools.util import format_block

class Parser(object):
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

    def run(self):
        # parser = yacc.yacc()
        if self.filename:
            try:
                data = self.filename.read()  # file like object
            except AttributeError:
                try:
                    # paths=get_var_from_nearest_outerframe('SearchPaths')
                    # print self.SearchPaths, self.filename, locate(self.filename, paths=self.SearchPaths).next()
                    data = open(next(locate(self.filename, paths=self.SearchPaths))).read()  # name of an existing file
                except (IOError, StopIteration):
                    data = eval(self.filename).read()  # eval to a file like object
            self.parseresult = yacc.parse(data)
        else:
            while 1:
                try:
                    s = eval(input('input > '))
                except EOFError:
                    break
                if not s:
                    continue
                self.parseresult = yacc.parse(s)
        return self.parseresult
