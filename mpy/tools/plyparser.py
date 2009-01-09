#!/usr/bin/env python

import ply.lex as lex
import ply.yacc as yacc
import os
import StringIO # for evaluation of a string containing a file like object
from mpy.tools.util import format_block

class Parser(object):
    """
    Base class for a lexer/parser that has the rules defined as methods
    """
    tokens = ()
    precedence = ()

    def __init__(self, **kw):
        self.debug = kw.get('debug', 0)
        self.filename = kw.get('filename', None)
        self.names = { }
        try:
            modname = os.path.split(os.path.splitext(__file__)[0])[1] + "_" + self.__class__.__name__
        except:
            modname = "parser"+"_"+self.__class__.__name__
        self.debugfile = modname + ".dbg"
        self.tabmodule = modname + "_" + "parsetab"
        #print self.debugfile, self.tabmodule

        # Build the lexer and parser
        lex.lex(module=self, debug=self.debug)
        yacc.yacc(module=self,
                  debug=self.debug,
                  debugfile=self.debugfile,
                  tabmodule=self.tabmodule)

    def run(self):
        if self.filename:
            try:
                data=self.filename.read()  # file like object
            except AttributeError:
                try:
                    data=file(self.filename).read() # name of an existing file
                except IOError:
                    data=eval(self.filename).read() # eval to a file like object
            self.parseresult=yacc.parse(data)
        else:
            while 1:
                try:
                    s = raw_input('input > ')
                except EOFError:
                    break
                if not s:
                    continue     
                self.parseresult=yacc.parse(s)
        return self.parseresult

