# -*- coding: utf-8 -*-
"""This is :mod:`mpylab.device.r_types`:

    Von einem Visa Befehl wird immer ein String zurückgegeben, die r_types Klassen
    sind dazu gedacht diese Strings zu verarbeiten und sie z.B. in ein Float Zahl oder eine Liste von Floats
    umzuwandeln.
    
   :author: Christian Albrecht
   :copyright: All rights reserved
   :license: no licence yet


"""
import re

from mpylab.device.mpy_exceptions import *


class R_TYPES(object):
    """Basis Klasse für alle r_types.
    
    Jede r_types Klasse muss von dieser abgeleitet werden.
    """

    def __init__(self):
        pass


class R_DEFAULT(R_TYPES):
    """Diese Klasse ist ein mapper damit auch Python standard type (wie z.B. int) als
    rtype angegeben werden können. Dazu initialisiert sie ein, zu dem standard type passendes,
    objekt aus dem R-Types pool und ruft diese zur Umwandlung auf.
    """

    def __init__(self, typ, command=None):
        """
        :param typ: Python standard type (wie z.B. int).
        :param command: Command in dem der R_Type verwendet wird (Optimal). Wird das Command angegeben, so wird der Name des 
                        Commands in der Execption Nachricht aufgeführt, welche geworfen wird falls ein String nicht 
                        umgewandelt werden kann. 
        """
        super().__init__()
        self.type = typ
        self.command = command
        if typ == float:
            self.validator = R_FLOAT(command=command)
        elif typ == int:
            self.validator = R_INT(command=command)
        elif typ == str:
            self.validator = R_STR(command=command)
        elif typ == bool:
            self.validator = R_BOOL(command=command)
        else:
            mess = ''
            if self.command:
                mess = 'in Command:  %s' % self.command.getName()
            raise Return_TypesError('Return Type %s not defined in R_DEFAULT \n    %s' % (self.type, mess))

    def __call__(self, value):
        """Mit Hilfe dieses Slots wird das Objekt aufrufbar (callable)
           Der Validator kann somit genauso wie eine Funktion verwendet werden.
           Nähre Infos zur Verwendung, siehe Klassen Beschreibung
           
           :param value: Wert der umgewandelt werden soll.
        """
        return self.validator(value)


class R_FLOAT(R_TYPES):
    """ Diese Klasse konvertiert einen String in eine Float Zahl.
    """

    def __init__(self, tmpl=r'[-+]?(\d+(\.\d*)?|\d*\.\d+)([eE][-+]?\d+)?', command=None):
        """
        :param tmpl: Regular expression; mit Hilfe dieses Audrucks wird geprüft ob der String einer Float Zahl entspricht.
                     Wird nichts angegeben, wird eine default expression verwendet, diese sollte für alle standard Fälle genügen.  
        :param command: Command in dem der R_Type verwendet wird (Optimal). Wird das Command angegeben, so wird der Name des 
                        Commands in der Execption Nachricht aufgeführt, welche geworfen wird falls ein String nicht 
                        umgewandelt werden kann. 
        """
        super().__init__()
        self.tmpl = tmpl
        self.command = command

    def __call__(self, value):
        """Mit Hilfe dieses Slots wird das Objekt aufrufbar (callable)
           Der Validator kann somit genauso wie eine Funktion verwendet werden.
           Nähre Infos zur Verwendung, siehe Klassen Beschreibung
           
           :param value: Wert der umgewandelt werden soll.
        """
        # print value

        m = re.match(self.tmpl, value)
        if m:
            ans = m.group(0)
            try:
                value = float(ans)
                return value
            except:
                pass

        mess = ''
        if self.command:
            mess = 'in Command:  %s' % self.command.getName()
        raise Return_TypesError('Can not convert received value to float \n           %s' % mess)
        return None


class R_INT(R_TYPES):
    """ Diese Klasse konvertiert einen String in eine Int Zahl.
    """

    def __init__(self, tmpl=r'^\d+$', command=None):
        """
        :param tmpl: Regular expression; mit Hilfe dieses Audrucks wird geprüft ob der String einer Int Zahl entspricht.
                     Wird nichts angegeben, wird eine default expression verwendet, diese sollte für alle standard Fälle genügen.  
        :param command: Command in dem der R_Type verwendet wird (Optimal). Wird das Command angegeben, so wird der Name des 
                        Commands in der Execption Nachricht aufgeführt, welche geworfen wird falls ein String nicht 
                        umgewandelt werden kann. 
        """
        super().__init__()
        self.tmpl = tmpl
        self.command = command

    def __call__(self, value):
        """Mit Hilfe dieses Slots wird das Objekt aufrufbar (callable)
           Der Validator kann somit genauso wie eine Funktion verwendet werden.
           Nähre Infos zur Verwendung, siehe Klassen Beschreibung
           
           :param value: Wert der umgewandelt werden soll.
        """
        m = re.match(self.tmpl, value)
        if m:
            ans = m.group(0)
            try:
                value = int(ans)
                return value
            except:
                pass

        mess = ''
        if self.command:
            mess = 'Command:  %s' % self.command.getName()
        raise Return_TypesError('Can not convert received value to int \n           %s' % mess)
        return None


class R_STR(R_TYPES):
    """ Diese Klasse konvertiert einen String in einen String.
        
        Diese Klasse wird hauptsächlich dafür benötig, dass in den Commands alle Python standard Typen angegenben werden können.
        Desweitern kann man, in dam eine Regular expression angibt, den String auf bestimmte Regeln prüfen.
    """

    def __init__(self, tmpl=r'.*', command=None):
        """
        :param tmpl: Regular expression; mit Hilfe dieses Audrucks wird geprüft ob der String bestimmten Regeln entspricht.
                     Wird nichts angegeben, wird eine default expression verwendet, in dieser sind alle Zeichen erlaubt.  
        :param command: Command in dem der R_Type verwendet wird (Optimal). Wird das Command angegeben, so wird der Name des 
                        Commands in der Execption Nachricht aufgeführt, welche geworfen wird falls ein String nicht 
                        umgewandelt werden kann. 
        """
        super().__init__()
        self.tmpl = tmpl
        self.command = command

    def __call__(self, value):
        """Mit Hilfe dieses Slots wird das Objekt aufrufbar (callable)
           Der Validator kann somit genauso wie eine Funktion verwendet werden.
           Nähre Infos zur Verwendung, siehe Klassen Beschreibung
           
           :param value: Wert der umgewandelt werden soll.
        """
        m = re.match(self.tmpl, value)
        if m:
            ans = m.group(0)
            try:
                value = str(ans)
                return value
            except:
                pass

        mess = ''
        if self.command:
            mess = 'Command:  %s' % self.command.getName()
        raise Return_TypesError('Can not convert received value to str \n           %s' % mess)
        return None


class R_BOOL(R_TYPES):
    """ Diese Klasse konvertiert einen String in einen Boolen Typ.
        
        Wird den Konstruktor nichts weiter angegeben, werden die Strings 'off', '0' und 'false' zu False gewandelt,
        die Strings 'on', '1' und 'true' zu True.
    """

    def __init__(self, values_false=('off', '0', 'false'), values_true=('on', '1', 'true'), command=None):
        """
        :param values_false: Eine Liste oder Tupel mit Strings welche dem Wert False entsprechen sollen. Default: ('off', '0','false')
        :param values_true: Eine Liste oder Tupel mit Strings welche dem Wert True entsprechen sollen. Default: ('on','1','true')
        :param command: Command in dem der R_Type verwendet wird (Optimal). Wird das Command angegeben, so wird der Name des 
                        Commands in der Execption Nachricht aufgeführt, welche geworfen wird falls ein String nicht 
                        umgewandelt werden kann. 
        """
        super().__init__()
        self.values_true = values_true
        self.values_false = values_false
        self.command = command

    def __call__(self, value):
        """Mit Hilfe dieses Slots wird das Objekt aufrufbar (callable)
           Der Validator kann somit genauso wie eine Funktion verwendet werden.
           Nähre Infos zur Verwendung, siehe Klassen Beschreibung
           
           :param value: Wert der umgewandelt werden soll.
        """
        # print value
        ans = str(value).lower()
        if ans in self.values_false:
            return False
        elif ans in self.values_true:
            return True

        mess = ''
        if self.command:
            mess = 'Command:  %s' % self.command.getName()
        raise Return_TypesError('Can not convert received value to boolean \n           %s' % mess)
        return None


class TUPLE_OF_FLOAT(R_TYPES):
    """ Diese Klasse konvertiert einen String, in der mehrere Floats aufgeführt sind, in ein Tuple von Float Zahlen.
    """

    def __init__(self, tmpl=r'([-+]?(\d+(\.\d*)?|\d*\.\d+)([eE][-+]?\d+)?,?)+', command=None):
        """
        :param tmpl: Regular expression; mit Hilfe dieses Audrucks wird geprüft ob der String einer Liste von Floats entspricht.
                     Wird nichts angegeben, wird eine default expression verwendet, diese sollte für alle standard Fälle genügen.  
        :param command: Command in dem der R_Type verwendet wird (Optimal). Wird das Command angegeben, so wird der Name des 
                        Commands in der Execption Nachricht aufgeführt, welche geworfen wird falls ein String nicht 
                        umgewandelt werden kann. 
        """
        super().__init__()
        self.tmpl = tmpl
        self.command = command

    def __call__(self, value):
        """Mit Hilfe dieses Slots wird das Objekt aufrufbar (callable)
           Der Validator kann somit genauso wie eine Funktion verwendet werden.
           Nähre Infos zur Verwendung, siehe Klassen Beschreibung
           
           :param value: Wert der umgewandelt werden soll.
        """

        m = re.match(self.tmpl, value)
        if m:
            ans = m.group(0)
            try:
                temp = re.split(',', ans)
                temp2 = []
                for i in temp:
                    temp2.append(float(i))
                return tuple(temp2)
            except:
                pass

        mess = ''
        if self.command:
            mess = 'Command:  %s' % self.command.getName()
        raise Return_TypesError('Can not convert received value to a tuple of float \n           %s' % mess)
        return None
