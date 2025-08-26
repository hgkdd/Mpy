# -*- coding: utf-8 -*-
"""This is :mod:`mpylab.device.tools`:

   :author: Christian Albrecht, Hans Georg Krauthaeuser
   :copyright: All rights reserved
   :license: no licence yet
"""

import inspect
import copy
from mpylab.device.r_types import *
from mpylab.tools.Configuration import fstrcmp
from mpylab.device.driver_new import DRIVER


class Meta_Driver(type):
    """ Meta-Klasse für Driver.
        
        In der Beschreibung wird von Driver-Klassen und Super-Klassen gesprochen.
        Mit Dirver-Klasse ist eine konkrete Implemntiereung eines Drivers gemeint, wie z.B. die Klasse :mod:`mpylab.device.nw_rs_zlv`.
        Mit Super-Klasse ist somit die dazugehörende Super-Kasse bezeichnet, im falle des :mod:`mpylab.device.nw_rs_zlv` wäre das die Klasse networkanalyzer.py. 
    
        .. rubric:: Die Meta-Klasse hat mehrere Aufgaben:

        Sie baut anhand des _cmds dict der Driver Klasse Methoden für diese Klasse. 

        Die geschaffenen Methoden haben den gleichen Namen wie das jeweilige "Command" bzw. die 
        jeweilige "Function" im _cmds dict. Als Parameter sind diejenigen vorhanden, welche in der "Function" 
        bzw. in dem "Command" definiert wurden. (Eine Methode, welche durch die Meta-Klasse gebaut wurde, 
        ruft im Grund nur das ihr zugewiesene Command oder Function Objekt auf).


        Weiterhin führt die Meta-Klasse einen Syntax Check für Methoden durch, die auch im 
        _commands dict der Super Klasse definiert wurden. Die Parameter einer Driver-Methode,
        deren Name ebenfalls im _commands dict der Super-Klasse vorhanden ist, müssen mit den dort 
        angegeben Parametern übereinstimmen! 
        Sind in _commands Methoden definiert, welche nicht in der Klasse implementiert sind, 
        wird eine Methode gebaut die eine NotImplementedError Exception wirft.


        Durch die Meta-Klasse ist es auch möglich, globale return_maps für commands und globale 
        possibilities_maps für Parameter zu definieren. 
        Für eine genaure Beschreibung zu return_maps, siehe Command().
        Für eine genaure Beschreibung zu possibilities, siehe Parameter()

        .. rubric:: possibilities:
        
        Possibilities sind mögliche Werte für einen Parameter. Werden andere Werte übergeben, wird mit Hilfe eines
        Fuzzy-string-compares, der übergebene Wert auf einen den in der Posssibilites-Liste vorhandenen zurückgeführt. 

        Possibilities dürfen sowohl in der Super-Klasse des Driver als auch in der Driver-Klasse selbst definiert werden.
        Wird in beiden Klassen eine Possibilities-Liste  erzeugt, welche den gleichen Parameter anspricht, wird die 
        diejenige der Superklasse verwendet.
        Beispiel::
        
            _cmds= CommandsStorage( NETWORKAN,
                                    Command('SetSparameter',"VISA Command String",(
                                            ...
                                            Parameter('measParam',ptype=str) 
                                             )   ),

        Will man für den Parameter 'measParam' eine Possibilites-Liste erzeugen, dann muss diese folgenden Namen 
        besitzen: Name-des-Parameters_possib (unabhängig davon ob die Liste in der Super-Klasse oder in der Driver-Klasse 
        selbst definiert wurde):
        Beispiel::
        
            measParam_possib=('S11', 'S12', 'S21', 'S22')

        Diese Liste gilt für alle Parameter mit dem Namen 'measParam', egal in welchem Command oder Function.


        .. rubric:: possibilities_maps:

        possibilities_maps können nur in der Driver-Klasse selbst, nicht in der Superklasse definiert werden.
        Beispiel::
        
            Command('SetSweepType','VISA Command String'),
                            Parameter('sweepType',ptype=str)
                            )),

        Will man für den Parameter 'sweepType' eine Possibilites_Map erzeugen, dann muss diese folgenden Namen 
        besitzen: Name-des-Parameters_possib_map
        Beispiel::
    
            sweepType_possib_map={'LOGARITHMIC'  :   'LOGARITHMIC_map',
                                  'LINEAR'  :   'LINEAR_map',
                                    }
        
        Diese Map gilt für alle Parameter mit dem Namen 'sweepType', egal in welchem Command oder Function.


        .. rubric:: return_maps

        return_maps können nur in der Klasse selbst, nicht in der Super-Klasse, definiert werden.
        Beispiel::

            Command('SetSweepType','VISA Command String'),
                            Parameter('sweepType',ptype=str)
                            )),

        Will man für dieses Command eine return_maps erzeugen, dann muss diese folgenden Namen besitzen: 
        Name_des_Command_rmap
        Beispiel::

            GetSweepType_rmap={'LOG'  :   'LOGARITHMIC',
                               'LIN'  :   'LINEAR',
                                }
    
        Das Vorgehen für Functions ist äquivalent. 
    """

    def __new__(mcs, cls_name, bases, dct):
        # print "__new__: \n"
        # print "DriverMetaClass:\n NAME: %s \n\n BASES:\n %s\n\n DICT:\n%s"%(cls_name,str(bases),str(dict))
        # print "\n\n\n"

        # *********************
        # Erstellen und Kompilieren der Methoden
        # *********************
        for cmd_func_name, cmd_func in list(dct['_cmds'].items()):
            # Prüfen ob Methode schon existiert, wenn ja, dann private Methode erzeugen.
            if cmd_func_name in dct:
                cmd_func_name = "_" + cmd_func_name
            func_str = {}
            func_str['name'] = cmd_func_name
            func_str['args'] = cmd_func.getParameterStr()

            M_code = """def create_Methode(command,function=None):
                          def %(name)s(self,%(args)s):
                              return command(self,%(args)s)
                          m= %(name)s
                          if function:
                              m.commands=function
                          return m""" % func_str

            code = compile(M_code, '<string>', 'single')
            evaldict = {}
            exec(code, evaldict)

            if isinstance(cmd_func, Function):
                dct[cmd_func_name] = evaldict["create_Methode"](cmd_func, function=cmd_func)
            else:
                dct[cmd_func_name] = evaldict["create_Methode"](cmd_func)

            # ********************
            # Übergeben von Possibilities-tupel/dicts, Return-dicts an die
            # Funktionen oder Parameter
            # ********************

            if isinstance(cmd_func, Function):
                for command_name, command in list(cmd_func.items()):
                    try:
                        return_map = dct['%s_rmap' % command_name]
                        command.setReturn_map(return_map)
                        # print return_map
                    except KeyError:
                        pass
            else:
                try:
                    return_map = dct['%s_rmap' % cmd_func_name]
                    cmd_func.setReturn_map(return_map)
                    # print return_map
                except KeyError:
                    pass

            for para_name, para in list(cmd_func.getParameter().items()):

                try:
                    possib = dct['%s_possib' % para_name]
                    para.setPossibilities(possib)
                    # print possib
                except KeyError:
                    pass

                try:
                    possib = getattr(bases[0], '%s_possib' % para_name)
                    para.setPossibilities(possib)
                    # print possib
                except AttributeError:
                    pass

                try:
                    possib_map = dct['%s_possib_map' % para_name]
                    para.setPossibilities_map(possib_map)
                    # print possib_map
                except KeyError:
                    pass

        # **********************
        # Syntaxcheck der Methoden anhand des _commands dicts in der Elternklasse
        # Existiert eine Methode nicht, wir eine erstellt welche einen NotImplementedError Exception wirft
        #
        # Syntaxcheck heißt: Es wird geprüft, ob die Parameter der implementierte Methoden mit den
        # Angaben des _commands dict übereinstimmen (Name, Reihenfolge).
        # ***********************
        for commands_name, commad_map in list(bases[0]._commands.items()):
            para_command = commad_map['parameter']
            if isinstance(para_command, str):
                para_command = (para_command,)

            try:
                args = ['self']
                if para_command:
                    args.extend(para_command)

                if args != inspect.getfullargspec(dct[commands_name])[0]:
                    raise DriverImplementedError(
                        'The function %s is not correct implemented\n            args current: %s      args should be: %s' % (
                            commands_name, inspect.getfullargspec(dct[commands_name])[0], args))
            except KeyError:
                if para_command:
                    args = ", ".join(para_command)
                else:
                    args = ""

                func_str = {'name': commands_name,
                            'args': args}

                M_code = """def %(name)s(self,%(args)s): 
                              raise NotImplementedError('The function %(name)s is not implemented yet')""" % func_str

                code = compile(M_code, '<string>', 'single')
                evaldict = {}
                exec(code, evaldict)
                dct[commands_name] = evaldict["%(name)s" % func_str]

        return type.__new__(mcs, cls_name, bases, dct)

    # def __init__(cls, name, bases, dct):
    #        print "\n__init_: \n"
    #        print "DriverMetaClass:\n NAME: %s \n\n BASES:\n %s\n\n DICT:\n%s"%(name,str(bases),str(dict))
    #        print "\n\n\n"        
    #        super(Meta_Driver, cls).__init__(name, bases, dct)


class CommandsStorage(dict):
    """ CommandStorage ist im Grunde ein dict. Es ermöglicht die Übergabe der Werte als Argument an 
        die __init__ Methode. 
        Jedes Argument muss eine Methode .getName() besitzen über die der Name des Arguments abgerufen werden kann.
        
        CommandStorage fügt jedes Argument, mit dessen Namen als key, sich selbst hinzu. 
        Weiterhin wird für jedes Argument ein Attribut mit dessen Namen angelegt.

        Das ermöglicht einen Zugriff auf zwei Arten::
        
            CommandS['key']
            CommandS.key 
        
        Verwendung::
        
            c=CommandsStorage(item1,item2,.....)
    """

    def __init__(self, driver, *items):
        """
        :param driver: Superklasse das Drivers
        :param *items: itemts müssen eine Methode .getName() besitzen. 
        """
        super().__init__()
        self.driver = None
        for i in items:
            self[i.getName()] = i
            setattr(self, i.getName(), i)
            i.init(driver)


class Function(dict):
    """ Function ist eine Sammelklasse für Commands.

        .. rubric:: Verwendung:
        
        Die Commands werden der Function beim initialisieren des Function-Objekts
        übergeben. Will man mehr als ein Command angeben, muss man eine List/Tuple von Commands übergeben. 
        Das erste Argument von Funktion muss immer der name der Function sein::
 
            f=Function(name_der_Function,(
                      Command('command_1','command_str',(Parameter_1),rtype=float)
                      Command('command_2','command_str',(Parameter_1,Parameter_2),rtype=str)
                      ) )

        f ist ein Aufrufbares Objekt (callable object), das heißt es kann wie ein Methode/Funktion verwenden::
    
            print (f(self,Argumente))

        Die Parameter die Function besitzt, richten sich nach den Parametern der Commands. 
        Bei dem oben aufgeführten Beispiel hätte das Function Objekt zwei Parameter, in folgender Reihenfolge:: 
    
            f(self,Parameter_1,Parameter_2)

        Der Parameter_1 kommt bei den Commands doppelt vor, wird aber bei Function nur einmal verwendet, 
        und zwar an der Stelle wo er zuerst auftritt. 


        **WICHITG:** Das erste Argument beim Aufruf einer Function muss immer die aktuelle Dirver Instanz sein! 

        **HINWEIS:**   Es ist nicht empfohlen die  Function Objekt direkt zu verwenden, man sollte immer über die
                       durch die Meta-Klasse erzeugten Methoden gehen. Dort wird die Driver Instanz dann automatisch 
                       übergeben.


        .. rubric:: Rückgabe:

        Als Standard gibt Function ein Dict zurück. Als key wird der Name des Command verwendet, 
        als Wert der Rückgabewert der Commands. 
 
        zum Beispiel:
 
        Eine Function Objekt hat zwei Commandos::
            
            f=Function('bsp',(
                Command('command_1','command_str',(Parameter),rtype=float)
                Command('command_2','command_str',(Parameter),rtype=str)
                ))
 
 
        Dieses Function Objekt würde beispielsweiße folgendes dict zurück geben::
            
            print f(self,Argumente)
                ->  {'command_1': 888,
                    'command_2': irgendwas_str}
 
 
        **Um die Rückgabe besser kontrollieren zu können ist es möglich ein Template anzugeben**
        Beispiel::
         
            f=Function('bsp',(
                Command('command_1','command_str',(Parameter),rtype=float)
                Command('command_2','command_str',(Parameter),rtype=str)
                    ),rtmpl='%(command_1)d')
 
        Diese Function Objekt würde folgendes zurück geben::
            
            print f(self,Argument)
                ->  888
                
        Der Type der Rückgabe würde aber immer noch ein str sein::  
            
            print type(f(self,Argument))
                ->  <type 'str'>
 
 
        Will man nun aber ein float als Rückgabe haben, muss man zusätzlich rtype angeben::
            
            f=Function('bsp',(
                Command('command_1','command_str',(Parameter),rtype=float)
                Command('command_2','command_str',(Parameter),rtype=str)
                    ),rtmpl='%(command_1)d',rtype=float)
    
            print f(self,Argument)
                ->  888
 
            print type(f(self,Argument))
                ->  <type 'float'>

        Es kann entweder ein Python Standard Typ angehen werden, oder ein Objekt welches von R_TYPES() 
        abgeleitet wurde. Was für R_TYPES() Objekte existieren, siehe dazu :mod:`mpylab.device.r_types`. Die Klassen dieses Moduls 
        müssen natürlich auch importiert sein.
        Es kann auch der Platzhalter '<default>' verwendet werden. Dann wird in dem _commands dict 
        der Super Klasse des Driver nach dem returntype, unter dem Namen der Function, gesucht und dieser Verwendet. 

        **WICHTIG:** rtype wird nur beachtet, wenn auch rtmpl definiert wurde.

        .. rubric:: Methods
    """

    def __init__(self, name, commands, rtmpl=None, rtype=None):
        """
        :param name: name der Function
        :param commands: Command oder tuple/list mit Commands
        :param rtmple: Template für Rückgabe (siehe Klassen Beschreibung)
        :param rtype: Gewünschter Type der Rückgabe (z.B. float) (siehe Klassen Beschreibung)
        """
        super().__init__()
        self.rtmpl = rtmpl
        self.rtype = rtype
        self.name = name

        self.parameter = {}
        self.intance_param = {}

        self.return_class = None

        # Falls commands keine Liste ist -> umwandeln in List
        if not isinstance(commands, (list, tuple)):
            commands = [commands]
        elif isinstance(commands, tuple):
            commands = list(commands)

        self.commands = commands

        # Parameter aus den Commands holen und
        # für Function aufbereiten
        parameterTuple = []
        for c in commands:
            self[c.getName()] = c
            setattr(self, c.getName(), c)
            self.parameter.update(c.getParameter())

            c_para_tmp = c.getParameterTuple()
            c_para = []
            for i in c_para_tmp:
                if i in parameterTuple:
                    continue
                c_para.append(i)
            parameterTuple.extend(c_para)
        self.parameterTuple = tuple(parameterTuple)

        self.is_init = False

    def init(self, driver_super):
        """Init() führt einige, für die Initialisierung des Objekts, nötigen Schritte durch, 
           sie muss aufgerufen werden, bevor das objekt verwendet werden kann.

           Wird durch ein CommandStorage Objekt automatisch erledigt.
           
           :param driver_super: Driver Super Klasse, !nicht Instanze! 
        """
        for c in self.commands:
            c.init(driver_super, f_name=self.name)

        rtype = None
        if self.rtype == '<default>':
            rtype = driver_super._commands[self.name]['returntype']
        else:
            rtype = self.rtype

        if rtype:
            if isinstance(rtype, R_TYPES):
                self.return_class = rtype
            elif isinstance(rtype, str):
                self.return_class = R_STR(rtype)
            else:
                self.return_class = R_DEFAULT(rtype, command=self)

    def __call__(self, driver, *para):
        """Mit Hilfe dieses Slots wird das Objekt aufrufbar (callable)
        Nähre Infos zur Verwendung des Function Objekt siehe Klassen Beschreibung
        
        :param driver: Instanze eines Drivers
        :param para: Argumente für die Parameter des Function objekts 
        """

        # Prüfen ob das erste Argument auch wircklich ein Instanze von Driver ist:
        if not isinstance(driver, DRIVER):
            raise TypeError('First argument of Function %s(driver,%s) must be a instance of DRIVER' % (
            self.name, self.getParameterStr()))

            # Anzahl der übergebenen Argumente prüfen
        if len(para) > len(self.parameterTuple) or len(para) < len(self.parameterTuple):
            raise TypeError('Function %s(driver,%s) takes exactly %d arguments (%d given)' % (
            self.name, self.getParameterStr(), len(self.parameterTuple) + 1, len(para) + 1))

        # Eine Kopie der Parameter für jeder Driver Instanz anlegen und die Parameter Initialisieren
        if driver not in self.intance_param:
            p = copy.deepcopy(self.parameter)
            for v in list(p.values()):
                v.init(self, driver)
            self.intance_param[driver] = p

        prameter = self.intance_param[driver]

        # Die Übergebnen Argumente den Parametern Objekten übergeben:
        i = 0
        for p in self.parameterTuple:
            prameter[p](para[i])
            i = i + 1

        return_map = {}
        for c in self.commands:
            return_map[c.getName()] = c._do_command(driver, prameter)

        if self.rtmpl:
            if self.return_class:
                return self.return_class(self.rtmpl % return_map)
            else:
                return self.rtmpl % return_map

        return return_map

    def getName(self):
        """Gibt den Namen des Function Objekts zurück
        """
        return self.name

    def getParameterTuple(self):
        """Gibt die Parameter des Function Objekts als Tuple zurück
        """
        return self.parameterTuple

    def getParameterStr(self):
        """Gibt die Parameter des Function Objekts als String zurück
        """
        return ", ".join(self.parameterTuple)

    def getParameter(self):
        """Gibt alle Parameter der integrierten Commands, des Function Objekts, als dict zurück
        """
        return self.parameter

    def Rfunction(self):
        return None


class Command(object):
    """ Command kümmert sich um die Verwaltung und Ausführung von VISA Kommandos

        Jedes Command hat einen Namen, einen VISA-Befehls String, Parameter und optionale Keyword-Parameter. 
        Für nähere Beschreibung der Parameter siehe auch __init__() Funktion.


        .. rubric:: Verwendung
        
        Beispiel::
        
            c = Command('nane','SENSe%(channel)d:FREQuency:CENTer %(cfreq)s HZ',(
                        Parameter('channel',class_attr='internChannel'),
                        Parameter('cfreq')  
                        ) )
                         
        Der VISA-Befehls String ist ein Formatting String. In einen Platzhalter %(name)s wird der 
        aktuelle Werte des Parameters mit gleichen Name eingefügt und so der String vervollständigt. 
        Für jeden Platzhalter im String muss es einen passenden Parameter geben. 

        Instanzen von Command sind aufrufbare Objekte (callable Objekts)::

            print c(self,888)
                -> Rückgabe_des_VISA_Befehls z.B 777

        Das erste Argument für ein Command muss immer die aktuelle Driver Instanz sein, 
        alle weiteren Argumente sind für die Parameter. Die Reihenfolge der Parameter entspricht 
        der Reihenfolge bei der Initialisierung des Objekts. Ist allerdings ein Parameter an eine Attribut der 
        Driver-Instanz gebunden, dann kann der Wert nicht beim Aufruf des Objektes übergeben werden (siehe dazu
        auch die Beschreibung von Parameter()). 
        888 ist also der Wert für cfreq (im obigen Beispiel).


        .. rubric:: Rückgabe:

        Standardmäßig gibt ein Command unverändert das zurück was es vom Gerät über VISA erhält. 
        Das ist entweder nichts, oder ein String. Die Rückgabe kann aber auch angepasst werden, 
        dazu dienen die Keyword-Argumente: rfunction, rtype, return_map:

        *Bei rfunction kann der Name einer Methode der Klasse angegeben werden.*
        
        (Da alle Commands bzw. Functions in _cmds auch zu Methoden werden, können auch diese Verwendet werden)::

            c = Command('Setnane','SENSe%(channel)d:FREQuency:CENTer %(cfreq)s HZ',(
                        Parameter('channel',class_attr='internChannel'),
                        Parameter('cfreq')  
                        ),rfunction='Getname')
                        
            print self.Getname()
                -> return_of_Getname

            print c(self,888):
                -> return_of_Getname

        Wird rfunction definiert, haben rtype und return_map keine Bedeutung mehr. 
         
        *Mit rtype kann der Rückgabe-Type bestimmt werden*::

            c = Command('Setnane','SENSe%(channel)d:FREQuency:CENTer %(cfreq)s HZ',(
                         Parameter('channel',class_attr='internChannel'),
                         Parameter('cfreq')  
                         ),rtype=float)
            
            oder gleichbedeutend:
            
            c = Command('Setnane','SENSe%(channel)d:FREQuency:CENTer %(cfreq)s HZ',(
                         Parameter('channel',class_attr='internChannel'),
                         Parameter('cfreq')  
                         ),rtype=R_FLOAT())

            print c(self,888)
                -> 777

            print type(c(self,888))
                -> <type 'float'>

        Es kann entweder ein Python Standard Typ angehen werden, oder ein Objekt welches von R_TYPES() (:mod:`mpylab.device.r_types`)
        abgeleitet wurde. Was für R_TYPES() Objekte existieren, siehe r_types.py. Die Klassen dieses Moduls 
        müssen natürlich auch importiert sein. Intern wird float auf R_FLOAT() gemappt.
        Es kann auch der Platzhalter '<default>' verwendet werden. Dann wird in dem _commands dict 
        der Super Klasse des Driver nach dem returntype, unter dem Namen des Commands, gesucht und dieser Verwendet.
        '<default>' darf nicht verwendet werden, wenn Command in einer Function definiert wurde.


        *Mit return_map können Werte, die das Geräte zurückgibt, auf gewünschte Werte gemappt werden*::

            c = Command('Setnane','SENSe%(channel)d:FREQuency:CENTer %(cfreq)s HZ',(
                         Parameter('channel',class_attr='internChannel'),
                         Parameter('cfreq')  
                         ),return_map={777:'2000'},rtype=float)

            print c(self,888)
                 -> 2000

            print type(c(self,888))
                -> <type 'str'>

        Ohne return_map würde c 777 vom Type Float zurückgeben (siehe Bsp bei rtype)
        
        
        .. rubric:: Methods:
    """

    def __init__(self, name, command, parameter, rfunction=None, rtype=None, return_map=None):
        """ Zur Verwendung von Command, siehe Klassen Beschreibung
        
        :param name:        Der Name des Commands
        :param command:     Der Visa Befehl als Formatting String (siehe Klassen Beschreibung)
        :param parameter:   Parameter des Commands, wenn mehr als ein Parameter verwendet werden soll, 
                            dann müssen die Parameter als List oder Tuple übergeben werden. 
        :param rfunction:   Methode dessen Wert zurück gegen werden soll (siehe Klassen Beschreibung)
        :param rtype:       Rückgabe Type (siehe Klassen Beschreibung) 
        :param return_map:  Rückgabe Map (siehe Klassen Beschreibung)
        """

        self.return_map = return_map
        self.name = name
        self.function_name = None

        self.intance_param = {}

        if isinstance(command, str):
            self.command = command
        else:
            pass
            # error!!!!!!!!!!!

        self.rfunction = rfunction

        if self.rfunction and not isinstance(self.rfunction, str):
            raise TypeError('Value for rfunction must be type of String. Command: %s' % self.name)

        self.rtype = rtype

        self.tmpl = None

        # Parameter in eine List umwandeln, falls Tuple oder nur ein Parameter übergeben wurde.
        if not isinstance(parameter, (list, tuple)):
            parameter = [parameter]
        elif isinstance(parameter, tuple):
            parameter = list(parameter)

        ParameterTuple = []
        self.parameter = {}

        # Parameter in einem Dict speichern.
        for para in parameter:
            self.parameter[para.getName()] = para
            if not para.isClass_attr():
                ParameterTuple.append(para.getName())

        self.parameterTuple = tuple(ParameterTuple)

        self.isinit = False

    def init(self, driver_super, f_name=None):
        """Init() führt einige, für die Initialisierung des Commands, nötigen Schritte durch, 
           sie muss aufgerufen werden bevor das Command Objekt verwendet werden kann.

           Wird durch ein CommandStorage oder durch eine Function Objekt automatisch erledigt.
           
           :param driver_super: Driver Super Klasse, !nicht Instanze! 
           :param f_name: Name der Function welche das Command umschließt 
        """

        # Wenn default angegeben wurde, den rtype aus dem _command dict der Eltern Klasse holen.
        if self.rtype == '<default>':
            if self.function_name:
                raise TypeError('<default> is not allowed if Command is component of function')
            try:
                rtype = driver_super._commands[self.name]['returntype']
            except:
                raise DriverImplementedError(
                    '%s is not defined in the superclass %s, argument <default> is not allowed' % (
                    self.name, driver_super))
        else:
            rtype = self.rtype

        # Zum rtype passendes R_TYPES Objekt speichern, falls nicht direkt ein R_TYPES Objekt angegeben wurde.
        if rtype:
            if isinstance(rtype, R_TYPES):
                self.tmpl = rtype
            elif isinstance(rtype, str):
                self.tmpl = R_STR(rtype)
            else:
                self.tmpl = R_DEFAULT(rtype, command=self)

        self.isinit = True

        return 1

    def __call__(self, driver, *para):
        """Mit Hilfe dieses Slots wird das Objekt aufrufbar (callable)
           Nähre Infos zur Verwendung des Command Objekt siehe Klassen Beschreibung
        
        :param driver: Instanze eines Drivers
        :param para: Argumente für die Parameter des Command objekts 
        """

        # Überprüfen, ob das erste Argument eine Instanze von Driver ist
        if not isinstance(driver, DRIVER):
            raise TypeError('First argument of Command %s(driver,%s) must be a instance of DRIVER' % (
            self.name, self.getParameterStr()))

            # Die Anzahl der Argumente prüfen
        if len(para) > len(self.parameterTuple) or len(para) < len(self.parameterTuple):
            raise TypeError('Command %s(driver,%s) takes exactly %d arguments (%d given)' % (
            self.name, self.getParameterStr(), len(self.parameterTuple) + 1, len(para) + 1))

        # Eine Kopie der Parameter für jeder Driver Instanz anlegen und die Parameter Initialisieren
        if driver not in self.intance_param:
            p = copy.deepcopy(self.parameter)
            for v in list(p.values()):
                v.init(self, driver)
            self.intance_param[driver] = p

        prameter = self.intance_param[driver]

        # Den Parameter die Werte übergeben
        i = 0
        for p in self.parameterTuple:
            prameter[p](para[i])
            i = i + 1

        return self._do_command(driver, prameter)

    def _do_command(self, driver, parameters):
        """Diese Methode führt das VISA Command aus.

           Diese Methode sollte nie direkt verwendet werden, es sollte immer das Objekt selbst 
           aufgerufen werden (also der __call__ Slot verwendet werden) !!!

           Nähre Infos zur Verwendung von Command siehe Klassen Beschreibung 

           :param driver:       Eine Instanze eines Drivers
           :param parameters:   Paramter für den VISA Kommando String  
        """

        # Prüfen, ob von Driver schon die init() Methode aufgerufen wurde.
        # Diese muss immer zu erst aufgerufen werden
        if not driver.isInit():
            raise InitError()

        communication_obj = driver.getCommunication_obj()

        # Das Kommando mit Hilfe des Communication Objektes ausführen.
        # und die Rückegabe mit Hilfe eines R_TYPES Objekt laut vorgabe umwandeln
        try:
            if self.command == "":
                ans = communication_obj.read()
                ans = self.tmpl(ans)

            elif self.rtype:
                ans = communication_obj.query(self.command % parameters)
                ans = self.tmpl(ans)
            else:
                ans = communication_obj.write(self.command % parameters)

        except (TypeError, ValueError) as e:
            if isinstance(e, TypeError):
                if 'number' in str(e):
                    raise TypeError("Value of one Parameter of the Command %s can not convert into int." % self.name)
                elif 'float' in str(e):
                    raise TypeError("Value of one Parameter of the Command %s can not convert into float." % self.name)
                else:
                    raise TypeError(e)
            else:
                if 'unsupported format character' in str(e):
                    raise ValueError("""Command string of the Command %s not correct
                        %s""" % (self.name, e))
                else:
                    raise ValueError(e)

        # Wenn eine rfunction angegeben wurde, diese Auführen und zurückgeben.
        if self.rfunction:
            try:
                return getattr(driver, self.rfunction)()
            except AttributeError as e:
                raise AttributeError("%s\n           Failure at Command: %s  Parameter: rfunction" % (e, self.name))

        # Wenn ein return_map definiert wurdeh, mappen:
        if self.return_map:
            try:
                ans = self.return_map[ans]
            except:
                pass

        return 0, ans

    def getName(self):
        """Gibt den Namen des Commands zurück
        """
        return self.name

    def getParameter(self):
        """Gibt alle Parameter des Commands als Map zurück
        """
        return self.parameter

    def getParameterTuple(self):
        """Gibt die Namen der Parameter des Commands, welche nicht an globale Attribute der Driver Klasse gebunden sind, als Tubel zurück.
        """
        return self.parameterTuple

    def getParameterStr(self):
        """Gibt die Parameter des Commands, welche nicht an globale Attribute der Driver Klasse gebunden sind, als String zurück
        """
        return ", ".join(self.parameterTuple)

    def setReturn_map(self, return_map):
        """Mit dieser Methode kann nachträglich die return_Map des Commands gesetzt werden.
           Wird von der Meta-Klasse verwendet.
        """
        self.return_map = return_map

    def Rfunction(self):
        return self.rfunction


class Parameter(object):
    """ Parameter verwaltet und speichert die Argumente für die VISA Kommandos. 

        **HINWEIS!** Es ist nie nötig den Parametern direkt Werte zu übergeben, das wird 
                        immer durch ein Function bzw. Command Objekt erledigt! 

        .. rubric:: Verwendung:

        *Dem einfachsten Parameter Objekt muss nur ein Name über geben werden*::

            p=Parameter('name')


        *Es ist möglich einen Type für diesen Parameter zu definieren*::

            p=Parameter('name', ptype=float)

        Der Parameter versucht dann, den ihm übergebenen Wert in den angegeben Typ umzuwandeln, klappt das nicht,
        wird eine Exception geworfen
        Alle Python Standard Typen sind erlaubt.


        *Weiterhin ist es möglich sogenannte Possibilities anzugeben*::

            p=Parameter('name', possibilities=('LINEAR','LOGARITHMIC'))

        Dies ist eine Liste oder Tuple mit möglichen Werte des Parameters. 
        Wird dem Parameter keiner der der möglichen Werte übergeben verwendet er einen, 
        zu dem übergebenen Wert ähnlichen, aus der Liste. 
        Possibilities ist also kein strickte Prüfung, dies ist aber mit Validatoren möglich 
        (siehe weiter unten).


        *Mit Possibilities_Map ist es möglich, übergebene Werte, auf einen für den VISA Befehl* 
        *brauchbaren Werte, zu mappen*::
          
            p=Parameter('name', possibilities_map={'LOGARITHMIC'  :   'LOGARITHMIC_map',
                                                    'LINEAR'  :   'LINEAR_map'})
                            
        In diesem Beispiel wird dem Parameter z.B. LOGARITHMIC übergeben, dieser würde 
        LOGARITHMIC_map daraus machen.
        Dieses vorgehen ist oft nötig, da alle Geräte einer Geräteklasse auf die gleiche 
        Arte und Weise angesprochen werden sollen, also auch mit den gleichen Argumenten. 
        Diese Argumente entsprechen aber nicht immer den Werte welche die VISA Kommandos 
        verlangen, somit muss gemappt werden.  


        *Das requires Keyword Argument*::

            p=Parameter('name', requires=IS_IN_SET(('a','b')) ) 

        Requires kann man Objekte sogenannter Validatoren Klassen übergeben. 
        Es ist auch möglich, mehrerer Validatoren zu übergeben, diese müssen dann in einer 
        List oder Tuple zusammengefasst werden. 
        Der dem Parameter übergebene Wert, wird mit Hilfe dieser Klassen auf seine 
        Richtigkeit geprüft. Dieser Test ist immer ein strikter Test. So darf im obigen 
        Beispiel dem Parameter nur 'a' oder 'b' übergeben werden und nichts andres. 
        Was für Validatoren exitieren, siehe validators.py


        *Validatoren haben die höchste Priorität, erst danach werden possibilities und danach possibilities_map verarbeitet*.  

        
        *Man kann ein Parameter aber auch an ein Attribut der Driver Instanz binden*:: 
    
            p=Parameter('name', class_attr='Attribut der Instanz')

        Der Werte für den Parameter wird dann immer aus diesem Attribut genommen.
        Wird class_attr definiert, haben  ptype, possibilities und possibilities_map keine Wirkung.
        
        
        .. rubric:: Methods:
    """

    def __init__(self, name, class_attr=None, ptype=None, requires=None, possibilities_map=None, possibilities=None):
        """Zur Verwendung von Parameters, siehe Klassen Beschreibung
        
        :param name:                Der Name des Parameters
        :param class_attr:          Bindet den Parameter an einen Klassen Attribut  (siehe Klassen Beschreibung)
        :param ptype:               Typ des Parameters (siehe Klassen Beschreibung)
        :param requires:            Liste von Validatoren  (siehe Klassen Beschreibung)
        :param possibilities_map:   Possibilities_map für den Parameter (siehe Klassen Beschreibung) 
        :param possibilities:       Rossibilities für den Parameter (siehe Klassen Beschreibung)
        """
        self.name = name
        self.class_attr = class_attr
        self.ptype = ptype
        self.requires = requires
        self.value = None
        self.driver = None
        self.command = None
        self.possib = possibilities
        self.possib_map = possibilities_map

    def init(self, cmd, driver):
        """Init() führt einige, für die Initialisierung des Parameters, nötigen Schritte durch, 
           sie muss aufgerufen werden bevor das Parameter Objekt verwendet werden kann.

           Wird durch ein Command automatisch erledigt.
           
           :param cmd: Command Instanz zu dem der Parameter gehört. 
           :param driver: Driver Instanz zu dem der Parameter gehört.
        """
        self.command = cmd
        self.driver = driver

    def getValue(self):
        """Gibt den aktuellen Wert des Parametes zurück.
        """
        if self.class_attr:
            return getattr(self.driver, self.class_attr)
        return self.value

    def __call__(self, value):
        """Mit Hilfe dieses Slots wird das Objekt aufrufbar (callable)
           Nähre Infos zur Verwendung des Parameters Objekt siehe Klassen Beschreibung

        :param para: Neuer Wert für den Parameter
        """

        if self.ptype:
            if not isinstance(value, self.ptype):
                try:
                    value = self.ptype(value)
                except:
                    raise TypeError(
                        'Attribute %s of %s must be of type %s' % (self.name, self.command.getName(), str(self.ptype)))

        self._validate(value)

        if self.possib and isinstance(value, str):
            value = fstrcmp(value, self.possib, n=1, cutoff=0, ignorecase=True)[0]
            # print 'value after fsrtrcmp ',value

        if self.possib_map:
            try:
                value = self.possib_map[value]
            except:
                pass
            # print 'value after maping:',value

        self.value = value

    # def __repr__(self):
    #    #print 'repr'
    #    return self.getValue()

    def __str__(self):
        """Dieser Slot wird verwendet wenn der Parameter in einen String umgewandelt werden soll.
        """
        # print 'str'
        try:
            return str(self.getValue())
        except ValueError as e:
            raise ValueError("""Can not convert the value " %s " from the Parameter %s of the Command %s into str
                  %s""" % (self.getValue(), self.name, self.command.getName(), e))

    def __int__(self):
        """Dieser Slot wird verwendet wenn der Parameter in ein Int umgewandelt werden soll.
        """
        # print 'to init',self.getValue()
        try:
            return int(self.getValue())
        except ValueError as e:
            raise ValueError("""Can not convert the value " %s " from the Parameter %s of the Command %s into int
                  %s""" % (self.getValue(), self.name, self.command.getName(), e))

    def __float__(self):
        """Dieser Slot wird verwendet wenn der Parameter in ein Float umgewandelt werden soll.
        """
        # print 'float'
        try:
            return float(self.getValue())
        except ValueError as e:
            raise ValueError("""Can not convert the value " %s " from the Parameter %s of the Command %s into float
                  %s""" % (self.getValue(), self.name, self.command.getName(), e))

    def getName(self):
        """Gibt den Namen des Parameters zurück.
        """
        return self.name

    def _validate(self, value):
        # print self.requires
        if not self.requires:
            return value
        requires = self.requires
        if not isinstance(requires, (list, tuple)):
            requires = [requires]
        for validator in requires:
            (value, error) = validator(value)
            if error:
                raise ValidateError(error, parameter=self.name, command=self.command.getName())
        return value

    def isClass_attr(self):
        """Diese Methode prüft, ob der Parameters an ein Klassen-Attribut gebunden ist.
           Sie gibt true zurück falls er gebunden ist, falls nicht wird false zurückgegeben.
        """
        r = False
        if self.class_attr:
            r = True
        return r

    def setPossibilities_map(self, map):
        """ Diese Methode ermöglicht das nachträgliche setzen einer Possibilities_map.
            Nähre Infos zur Verwendung des Parameters Objekt siehe Klassen Beschreibung
        """
        self.possib_map = map

    def setPossibilities(self, possib):
        """ Diese Methode ermöglicht das nachträgliche setzen von Possibilities.
            Nähre Infos zur Verwendung des Parameters Objekt siehe Klassen Beschreibung
        """
        self.possib = possib

    def Getptype(self):
        """ Gibt den Typ des Parameters zurück.
            (siehe Klassen Beschreibung)
        """
        return self.ptype
