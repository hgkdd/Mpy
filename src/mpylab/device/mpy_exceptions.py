# -*- coding: utf-8 -*-
"""This is :mod:`mpylab.device.mpy_exceptions`: 
    In diesem Modul werden verschiedene Exceptions definiert welche in dem myp.device Modul verwendet werden.
"""


class InitError(Exception):
    def __init__(self, message='Before Commands can be executed, the DRIVER.Init method must be called'):
        self.message = message

    def __str__(self):
        return self.message


class ValidateError(Exception):
    def __init__(self, message='Validators Error', parameter=None, command=None):
        self.message = message
        self.parameter = parameter
        self.command = command

    def __str__(self):
        m = ''
        if self.parameter:
            m = m + "    Parameter: %s" % self.parameter
        if self.parameter and self.command:
            m = m + "    of the"
        if self.command:
            m = m + "    Command: %s" % self.command
        return "%s \n%s" % (self.message, m)


class Return_TypesError(Exception):
    def __init__(self, message=''):
        self.message = message

    def __str__(self):
        return self.message


class DriverImplementedError(Exception):
    def __init__(self, message=''):
        self.message = message

    def __str__(self):
        return self.message


class GeneralDriverError(Exception):
    def __init__(self, message=''):
        self.message = message

    def __str__(self):
        return self.message
