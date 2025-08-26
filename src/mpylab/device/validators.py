# -*- coding: utf-8 -*-
"""This is :mod:`mpylab.device.validators`:
    
    Dieses Modul ist eine Sammlung von Validatoren wie sie von der Parameter Klasse in tools.py benötigt werden.
    
    Ein Validator prüft, ob ein Wert (z.B. ein Int) bestimmten Regeln entspricht.

   :author: Christian Albrecht
   :copyright: All rights reserved
   :license: no licence yet


"""


class IN_RANGE(object):
    """ Dieser Validator prüft, ob eine Zahl in einem bestimmten Intervall liegt.
    
    .. rubric:: Verwendung:
    
    Beispiel::
        
        v = IN_RANGE(1,100)
        
        print v(2)
            -> (2,None)
            
        print v(102)
            -> (102,Error Message)
        
    Liegt die Zahl im Intervall, wird ein Tupel mit der Zahl und None zurückgegeben;
    Liegt die Zahl außerhalb, wird ein Tupel mit der Zahl und einer Error Message zurückgegeben.
    
    """

    def __init__(self, mini, maxi, message=''):
        """
        :param mini:  Minimal Wert für die Zahl
        :param maxi:  Maximal Wert für die Zahl
        :param message: Error Message, falls Zahl nicht im gewünschten Intervall liegt.
                        Wird message nicht definiert, wird eine default Error Message verwendet.
        """
        self.min = mini
        self.max = maxi
        if message != '':
            self.message = 'Argument out of Range. Argument must be between %s and %s' % (self.min, self.max)
        else:
            self.message = message

    def __call__(self, value):
        """Mit Hilfe dieses Slots wird das Objekt aufrufbar (callable)
           Der Validator kann somit genauso wie eine Funktion verwendet werden.
           Nähre Infos zur Verwendung, siehe Klassen Beschreibung
           
           :param value: Wert der geprüft werden soll.
        """
        if not isinstance(value, (int, float)):
            return (value, 'The Validator IN_RANGE can only used for int, long or float')
        if value > self.max or value < self.min:
            return (value, self.message)
        return (value, None)


class IS_LOWER_THAN(object):
    """ Dieser Validator prüft, ob eine Zahl kleiner als ein bestimmter Wert ist.
    
    .. rubric:: Verwendung:
    
    Beispiel::
        
        v = IN_RANGE(100)
        
        print v(2)
            -> (2,None)
        
        print v(102)
            -> (102,Error Message)
        
    Ist die Zahl kleiner als der vorgegebende Wert, wird ein Tupel mit der Zahl und None zurückgegeben;
    Ist die Zahl größer oder gleich, wird ein Tupel mit der Zahl und einer Error Message zurückgegeben.
    
    """

    def __init__(self, maxi, message=''):
        """
        :param maxi:  Maximal Wert für die Zahl
        :param message: Error Message, falls Zahl größer oder gleich dem vorgegebenen Wert ist.
                        Wird message nicht definiert, wird eine default Error Message verwendet.
        """
        self.max = maxi
        if message != '':
            self.message = 'Argument is greater than or equal %s. Argument must be lower.' % (self.max)
        else:
            self.message = message

    def __call__(self, value):
        """Mit Hilfe dieses Slots wird das Objekt aufrufbar (callable)
           Der Validator kann somit genauso wie eine Funktion verwendet werden.
           Nähre Infos zur Verwendung, siehe Klassen Beschreibung
           
           :param value: Wert der geprüft werden soll.
        """
        if not isinstance(value, (int, float)):
            return (value, 'The Validator IS_LOWER_THAN can only used for int, long or float')
        if value >= self.max:
            return (value, self.message)
        return (value, None)


class IS_GREATER_THAN(object):
    """ Dieser Validator prüft, ob eine Zahl größer als ein bestimmter Wert ist.
    
    .. rubric:: Verwendung:
    
    Beispiel::
        
        v = IN_RANGE(100)
        
        print v(2)
            -> (2,Error Message)
        
        print v(102)
            -> (102,None)
        
    Ist die Zahl größer als der vorgegebende Wert, wird ein Tupel mit der Zahl und None zurückgegeben;
    Ist die Zahl kleiner oder gleich, wird ein Tupel mit der Zahl und einer Error Message zurückgegeben.
    
    """

    def __init__(self, mini, message=''):
        """
        :param mini:  Minimal Wert für die Zahl
        :param message: Error Message, falls die Zahl kleiner oder gleich dem vorgegebenen Wert ist.
                        Wird message nicht definiert, wird eine default Error Message verwendet.
        """
        self.min = mini
        if message != '':
            self.message = 'Argument is lower than or equal %s. Argument must be greater.' % (self.min)
        else:
            self.message = message

    def __call__(self, value):
        """Mit Hilfe dieses Slots wird das Objekt aufrufbar (callable)
           Der Validator kann somit genauso wie eine Funktion verwendet werden.
           Nähre Infos zur Verwendung, siehe Klassen Beschreibung
           
           :param value: Wert der geprüft werden soll.
        """
        if not isinstance(value, (int, float)):
            return (value, 'The Validator IS_GREATER_THAN can only used for int, long or float')
        if value <= self.min:
            return (value, self.message)
        return (value, None)


class IS_LOWER_EQUAL_THAN(object):
    """ Dieser Validator prüft, ob eine Zahl kleiner oder gleich als ein bestimmter Wert ist.
    
    .. rubric:: Verwendung:
    
    Beispiel::
        
        v = IN_RANGE(100)
        
        print v(2)
            -> (2,None)
        
        print v(102)
            -> (102,Error Message)
        
    Ist die Zahl kleiner oder gleich als der vorgegebende Wert, wird ein Tupel mit der Zahl und None zurückgegeben;
    Ist die Zahl größer, wird ein Tupel mit der Zahl und einer Error Message zurückgegeben.
    
    """

    def __init__(self, maxi, message=''):
        """
        :param maxi:  Maximal Wert für die Zahl
        :param message: Error Message, falls Zahl größer als der vorgegebenen Wert ist.
                        Wird message nicht definiert, wird eine default Error Message verwendet.
        """
        self.max = maxi
        if message != '':
            self.message = 'Argument is greater than %s. Argument must be lower or equal.' % (self.max)
        else:
            self.message = message

    def __call__(self, value):
        if not isinstance(value, (int, float)):
            return (value, 'The Validator IS_LOWER_THAN can only used for int, long or float')
        if value > self.max:
            return (value, self.message)
        return (value, None)


class IS_GREATER_EQUAL_THAN(object):
    """ Dieser Validator prüft, ob eine Zahl größer oder gleich als ein bestimmter Wert ist.
    
    .. rubric:: Verwendung:
    
    Beispiel::
        
        v = IN_RANGE(100)
        
        print v(2)
            -> (2,Error Message)
        
        print v(102)
            -> (102,None)
        
    Ist die Zahl größer oder gleich als der vorgegebende Wert, wird ein Tupel mit der Zahl und None zurückgegeben;
    Ist die Zahl kleiner, wird ein Tupel mit der Zahl und einer Error Message zurückgegeben.
    
    """

    def __init__(self, mini, message=''):
        """
        :param mini:  Minimal Wert für die Zahl
        :param message: Error Message, falls Zahl kleiner als vorgegebenen Wert ist.
                        Wird message nicht definiert, wird eine default Error Message verwendet.
        """
        self.min = mini
        if message != '':
            self.message = 'Argument is lower than %s. Argument must be greater or equal.' % (self.min)
        else:
            self.message = message

    def __call__(self, value):
        """Mit Hilfe dieses Slots wird das Objekt aufrufbar (callable)
           Der Validator kann somit genauso wie eine Funktion verwendet werden.
           Nähre Infos zur Verwendung, siehe Klassen Beschreibung
           
           :param value: Wert der geprüft werden soll.
        """
        if not isinstance(value, (int, float)):
            return (value, 'The Validator IS_GREATER_THAN can only used for int, long or float')
        if value < self.min:
            return (value, self.message)
        return (value, None)


class IS_IN_SET(object):
    """ Dieser Validator prüft, ob ein Argument (z.B. ein String) in einer Menge vorhanden ist.
    
    .. rubric:: Verwendung:
    
    Beispiel::
        
        v = IN_RANGE(('aaa','bbb','ccc'))
        
        print v('ddd')
           -> (2,Error Message)
        
        print v('aaa')
           -> (102,None)
        
    Ist der Wert in der Menge vorhanden, wird ein Tupel mit der Zahl und None zurückgegeben;
    Ist der Wert nicht in der Menge vorhanden, wird ein Tupel mit der Zahl und einer Error Message zurückgegeben.
    
    """

    def __init__(self, seti, message=''):
        """
        :param seti:  Menge gegen die der Wert geprüft werden soll.
        :param message: Error Message, falls Argument nicht in der vorgegebenen Menge vorhanden ist.
                        Wird message nicht definiert, wird eine default Error Message verwendet.
        """
        self.set = seti
        if message != '':
            self.message = 'Argument must be in Set %s.' % (self.set)
        else:
            self.message = message

    def __call__(self, value):
        """Mit Hilfe dieses Slots wird das Objekt aufrufbar (callable)
           Der Validator kann somit genauso wie eine Funktion verwendet werden.
           Nähre Infos zur Verwendung, siehe Klassen Beschreibung
           
           :param value: Wert der geprüft werden soll.
        """
        if not value in self.set:
            return (value, self.message)
        return (value, None)
