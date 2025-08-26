# -*- coding: utf-8 -*-
"""This is :mod:`mpylab.device.Metaui`: Metaclass to Build a standard GUI from the _setgetlist.

   :author: Christian Albrecht, Hans Georg Krauthaeuser
   :copyright: All rights reserved
   :license: no licence yet
"""

import traits.api as tapi
from traits.etsconfig.api import ETSConfig
from traits.has_traits import MetaHasTraits

ETSConfig.toolkit = "wx"
import traitsui.api as tuiapi
import traitsui.menu as tuim
import io
import re
import inspect


def erzeugeFired_Methode_mit_Rfunction(command, rfunction, param_list):
    """
    Functionfactory zum erzeugen von Traits-fired Funktionen.
    """

    def Methode_fired(self):
        setattr(self, rfunction.upper(), str(eval('self.dv.%s(%s)' % (command, ", ".join(param_list)))[1]))

    return Methode_fired


def erzeugeFired_Methode(name, param_list):
    """
    Functionfactory zum erzeugen von Traits-fired Funktionen.
    """

    def Methode_fired(self):
        setattr(self, name.upper(), str(eval('self.dv.%s(%s)' % (name, ", ".join(param_list)))[1]))

    return Methode_fired


def _Init_fired(self):
    """
    Standard init_fired Funktion.
    """
    ini = io.StringIO(self.INI)
    self.dv.Init(ini)

    # Alle Get Funktionen einmal aufrufen und so die Anzeige mit aktuellen Werten belegen.
    for item in self.mainEntries:
        m = re.match(r'^[Gg]et.*$', item)
        if m:
            getattr(self, "_%s_fired" % item)()


def Erzeuge_TapiVar(typ):
    """
    Hilfsfunktion zum erstellen von Traits-Variablen.
    """
    if typ == float:
        return tapi.Float()
    elif typ == int:
        return tapi.Int()
    else:
        return tapi.Str()


class Metaui(MetaHasTraits):
    """
    Diese Metaklasse ermöglicht das einfache Erstellen von Guis für das Testen eines Drivers.
    
    Sie baut für alle im _commands- und _cmds-Dict vorhanden Commands und Functions passende Buttons und
    Eingabefelder und nimmt so einem viel Schreibarbeit ab.
    
    Es werden für alles in _commands und _cmds definiert Kommandos Buttons und Felder erstellt. Sind in dem cmds-Dict mehr
    Kommandos definiert als in _commands, so werden auch für diese Buttons gebaut. Der Grund für dieses Vorgehen liegt in der
    Tatsache, dass diese GUI zum testen der Klasse gedacht ist und somit alle definierten Kommandso abgebildet werden sollen.
    Sind in _commands Kommandos aufgeführt die nicht in der konkreten Dirver-Klasse vorhanden sind, so wird eine Methode
    erstellt welche einen NotImplementedError wirft.
    
    
    
    Zu jeder Driver-Superklasse sollte ein UI-Superklasse existieren in der zusätzliche Taps definiert werden
    die für alle von ihr abgeleiteten Driverklassen gleich sein sollen.
    Damit die Metaklasse einwandfrei arbeiten kann, dürfen in der Superklasse nur 
    sogenannte tuiapi.Group (das sind Taps) erstellt werden. Diese müssen wiederrum in einem Dict
    mit dem Namen "GROUPS" gespeichert werden. Wobei folgende Konvention einzuhalten ist::
    
        GROUPS={'Name des Taps' : tuiapi.Group(...)}
    
    Als Beispiele siehe: :mod:`mpylab.device.networkanalyer_ui`
    
    
    
    Weiterhin muss eine UI-Klasse für jede konkrete Driver-Implementierung erstellt werden, diese muss von
    der UI-Superklasse abgeleitet sein. In dieser muss die Meta_ui als Metaklasse angegeben werden, weiterhin 
    sind folgende speziall Variablen nötig:
    
    **__driverclass__= :** Verweis auf eine konkrete Klasse einer Driver-Implementierung. ACHTUNG!! nur ein Verweis auf die Klasse, 
                        keine Instanz der Klasse. 
    
    **__super_driverclass__=**: Verweis auf die Superklasse eines Driver. ACHTUNG!! nur ein Verweis auf die Klasse, 
                            keine Instanz der Klasse.
                            
    Aus diesen Varialben holt sich die Metaklase das _commands-Dict und _cmds-Dict.
    
    Als Beispiel siehe: :class:`mpylab.device.nw_rs_zlv.UI`
    
    .. rubric:: Methods:
    """

    # def __init__(cls, eins, zwei, drei):
    #    print "init %s \n\n   %s  \n\n %s"%(eins,zwei,drei)

    def __new__(cls, class_name, bases, class_dict):

        class_dict.update({'_Init_fired': _Init_fired})

        driverclass = class_dict.get("__driverclass__")
        super_driverclass = class_dict.get('__super_driverclass__')

        tabs = 'INI_grp'
        INI_grp = tuiapi.Group(
            tuiapi.Item('INI', style='custom', springy=True, width=500, height=200, show_label=False),
            tuiapi.Item('Init', show_label=False),
            label='Ini')

        # ********************
        # _cmds abarbeiten
        # ********************

        _cmds = driverclass._cmds
        mainEntries = []
        items_Map = {}

        for command_name, command in list(_cmds.items()):
            items = ""
            if command_name in class_dict['_ignore']:
                continue
            if command_name in mainEntries:
                continue

            mainEntries.append(command_name)

            items = "%s tuiapi.Group(" % (items)
            items = "%s tuiapi.Item('%s',show_label=False,width=100)," % (items, command_name)
            class_dict[command_name] = tapi.Button(command_name)

            if command.Rfunction():
                items = "%s tuiapi.Item('%s',show_label=False,width=100)," % (items, command.Rfunction())
                items = "%s tuiapi.Item('%s',label='Wert',style='readonly',width=70)," % (
                    items, command.Rfunction().upper())

                class_dict[command.Rfunction().upper()] = Erzeuge_TapiVar(str)
                class_dict[command.Rfunction()] = tapi.Button(command.Rfunction())

                if command.Rfunction() not in mainEntries:
                    mainEntries.append(command.Rfunction())

                if command.Rfunction() in list(items_Map.keys()):
                    del items_Map[command.Rfunction()]
            else:
                items = "%s tuiapi.Item('%s',label='%s',style='readonly',width=70)," % (
                    items, command_name.upper(), 'Wert'.rjust(38))
                class_dict[command_name.upper()] = Erzeuge_TapiVar(str)

            param_list = []
            for param_name in command.getParameterTuple():
                param = command.getParameter()[param_name]
                if param.isClass_attr():
                    continue

                if hasattr(driverclass, command_name):
                    if param_name not in inspect.getfullargspec(getattr(driverclass, command_name))[0]:
                        continue

                items = "%s tuiapi.Item('param_%s_%s',label='%s',width=60)," % (items,
                                                                                command_name,
                                                                                param_name.upper(),
                                                                                param_name)
                class_dict['param_%s_%s' % (command_name, param_name.upper())] = Erzeuge_TapiVar(param.Getptype())
                param_list.append('self.param_%s_%s' % (command_name, param_name.upper()))

            if command.Rfunction():
                class_dict["_%s_fired" % command_name] = erzeugeFired_Methode_mit_Rfunction(command_name,
                                                                                            command.Rfunction(),
                                                                                            param_list)
                class_dict["_%s_fired" % command.Rfunction()] = erzeugeFired_Methode(command.Rfunction(), [])

            else:
                class_dict["_%s_fired" % command_name] = erzeugeFired_Methode(command_name, param_list)

            items = "%s orientation='horizontal')" % (items)
            items_Map[command_name] = items

        class_dict.update({'mainEntries': mainEntries})

        item_List = list(items_Map.values())
        item_List = [item_List[i:i + 16] for i in range(0, len(item_List), 16)]

        tabs_list_index = 0
        tabs_list = []

        for item in item_List:
            tabs_list.append(tuiapi.Group(eval(", ".join(item)), label='Main_%d' % tabs_list_index))
            tabs = tabs + ", tabs_list[%d]" % tabs_list_index
            tabs_list_index = tabs_list_index + 1

        # *******************
        # commands abarbeiten
        # *******************

        notIEntries = []
        items_Map = {}

        for command_name, item in list(super_driverclass._commands.items()):
            items = ""
            if (command_name in mainEntries) or (command_name in notIEntries):
                continue
            if command_name in class_dict['_ignore']:
                continue

            if item['parameter']:
                para_command = item['parameter']
                if isinstance(para_command, str):
                    para_command = (para_command,)

            # Testen ob die Methode direkt, also nicht über _cmds, implementiert wurde:
            # Wird die Methode in _commands angegeben, aber nicht implementiert wurde,
            # Erzeug die Meta Klasse eine Methode die einen  NotImplementedError wirft
            driver_ins = driverclass()
            try:
                p = ""
                if item['parameter']:
                    for param_name in para_command:
                        p = p + "'',"
                eval('driverclass.%s(driver_ins,%s)' % (command_name, p))
            except NotImplementedError:
                pass
            else:
                driver_ins.__del__()
                continue

            driver_ins.__del__()

            notIEntries.append(command_name)

            items = "%s tuiapi.Group(" % (items)
            items = "%s tuiapi.Item('%s',show_label=False,width=100)," % (items, command_name)
            class_dict[command_name] = tapi.Button(command_name)

            items = "%s tuiapi.Item('%s',label='%s',style='readonly',width=70)," % (items, command_name.upper(), 'Wert')
            class_dict[command_name.upper()] = Erzeuge_TapiVar(str)

            param_list = []

            if item['parameter']:
                for param_name in para_command:
                    items = "%s tuiapi.Item('param_%s_%s',label='%s',width=60)," % (
                        items, command_name, param_name.upper(), param_name)
                    class_dict['param_%s_%s' % (command_name, param_name.upper())] = Erzeuge_TapiVar(str)
                    param_list.append('self.param_%s_%s' % (command_name, param_name.upper()))

            class_dict["_%s_fired" % command_name] = erzeugeFired_Methode(command_name, param_list)

            items = "%s orientation='horizontal')" % (items)
            items_Map[command_name] = items

        item_List = list(items_Map.values())
        item_List = [item_List[i:i + 16] for i in range(0, len(item_List), 16)]

        for item in item_List:
            tabs_list.append(tuiapi.Group(eval(", ".join(item)), label='NotImp_%d' % tabs_list_index))
            tabs = tabs + ", tabs_list[%d]" % tabs_list_index
            tabs_list_index = tabs_list_index + 1

        # **********************
        # In den UI Klassen definiert Groups holen:
        # ************************

        for i in class_dict:
            if type(class_dict.get(i)) == tuiapi.Group:
                tabs = '%s,class_dict.get("%s")' % (tabs, i)

        i = 0
        for b in bases:
            for n, v in list(b.GROUPS.items()):
                if type(v) == tuiapi.Group:
                    tabs = '%s,bases[%d].GROUPS["%s"]' % (tabs, i, n)
            i = i + 1

        # *************
        # Fenster zusammen bauen:
        # ***************

        tabs = "tuiapi.Group(%s, layout='tabbed')" % tabs

        class_dict.update(
            {'traits_view': tuiapi.View(eval(tabs), title="Spectrumanalyer", buttons=[tuim.CancelButton])})

        # print "Meta   %s \n\n bases\n %s \n\n dict \n %s"%(class_name,str(bases),str(class_dict))

        return MetaHasTraits.__new__(cls, class_name, bases, class_dict)
