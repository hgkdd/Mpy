.. -*-coding: utf-8 -*-
Implementierung eines Treibers mit dem Driver-Framework
========================================================

Dieses Dokument beschreibt an Hand eines Beispiels die 
Implementierung eines eigenen Treibers in Mpy mit Hilfe des 
Driver Framework.

Als Beispiel soll ein Netzwerkanalysator von Rohde und Schwarz 
mit der Typenbezeichung ZLV dienen.

Der Treiber basiert auf der Klasse :class:`Networkanalyer`, 
die wiederum auf der Klasse :class:`DRIVER` aus der Datei driver_new.py 
aufsetzt. Alle Treiber sind im Verzeichnis `/mpylab/device/` gespeichert.

Einen neuen Treiber anlegen
---------------------------

Am besten man kopiert einen vorhandenen Treiber, wie z.B. 
`nw_rs_zlv.py` und speichert die Datei unter einen neuen Namen ab.
Die Syntax sollte dabei aus `nw`, einem Herstellerkürzel und 
einem Typenkürzel bestehen, die durch Unterstriche verbunden werden. 

Allgemein ist die Syntax also: `nw_<Herstellerkürzel>_<Typenkürzel>.py`

Den neuen Treiber anpassen
--------------------------

Nun öffnet man die neue Treiberdatei. Sie besteht hauptsächlich aus drei Teilen:

1. der Definition einer neuen Unterklasse für den speziell Networkanalyer
2. der Definition einer neuen Unterklasse für die Test-GUI
2. der Definition einer Funktion :meth:`main`, mit der der Treiber getestet werden kann.

Im Falle des nw_rs_zlv sind noch zwei Hilfsklassen `Trace` und `WINDOW` vorhanden 
auf die hier nichtnäher eingegangen werden soll.

Der erste Teil besteht wiederum aus drei Teilen:

#######################

1.2 cmds-Methoden
^^^^^^^^^^^^^^^^^^
Im ersten Teil der Klasse werden im Wörterbuch `_cmds` die Befehle zum 
Steuern des Gerätes festgelegt. Für jeden Befehl wird im Wörterbuch ein 
neues `Command` bzw. `Function` angelegt. Ein `Command` besteht aus:: 

	Command(Name, VISA-Befehl, Parameter, Retrun-Typ/-Funktion)

Für eine detailliertere Beschreibung siehe :class:`tools.Command()` und :class:`tools.Function()`.

Auf jedes ` Command `, das in `_cmds` definiert wurde, kann in der Klasse
wie auf eine normale Methode zugegriffen werden.
z.B.::

	self.name(...)

*Eine in `_cmds` definierte Methode wollen wir ab jetzt cmds-Methode nennen.* 

Es ist auch möglich eine cmds-Methode in der Klasse zu überlagern 
indem man eine Methode mit dem gleichen Namen definiert. Wurde das getan, 
kann man auf die ursprüngliche cmds-Methode zugreifen in dem man ein „_“ vor dem Namen setzt.::

	def name(self,...):
		...

	self.name(...)    (überlagerte Methode)
	self._name(...)   (ursprüngliche _cmds-Methode)


Dieses Vorgehen hat den Vorteil, dass der Zugriff auf VISA-Befehle immer 
vollkommen transparent über Methoden erfolgt und man somit voll objektorientiert 
arbeiten kann. Um das Ausführen der VISA-Befehle und das erstellen der Methoden
kümmern sich Klassen welche in `tools.py` definiert wurden. Damit das alles funktioniert,
müssen folgende Import Anweisungen in der Driver-Datei vorhanden sein::

	from tools import *
	from r_types import *
	from validators import *
	from mpy_exceptions import *

Weiterhin ist es **wichtig**, dass am Anfang der Klasse die Metaklasse definiert wird::

	__metaclass__=Meta_Driver


Es ist zu beachten, dass in der Super-Klasse des Drivers, in unserem Fall 
class:`Networkanalyer`, ein weiteres Wörterbuch `_commands` definiert sein 
kann. In diesem Wörterbuch sind alle Methoden definiert, welche jede 
Driver-Implementierung besitzen sollte. Auch wird in `_commands` vorgeschrieben
welche Parameter diese Methoden haben müssen.

Fehlt in einer Driver Implementierung eine Methode aus dem `_commands` 
Wörterbuch, so wird automatisch eine erzeugt, welche bei Aufruf einen 
NotImplementedError wirft.

Es ist sicher zu stellen, dass die Parameteranzahl und -reihenfolge aus 
`_commands` und der konkreten Methoden-Implementierung übereinstimmen. 
Dies wird auch durch die Metaklasse geprüft, ist die Übereinstimmung nicht 
gegeben, wirft die Metaklasse beim erstellen des Objektes einen Error.

Dieses Vorgehen stellt sicher, dass bei alle Driver-Implementierungen 
die Methoden, welche Grundfunktionen ansprechen sollen, identische sind.    

1.2 Methoden
^^^^^^^^^^^^^

Im Teil 1.2 der Klasse werden die Methoden der Klasse definiert. 
In der Beispiel Klasse :class:`nw_rs_zlv` finden sich dazu verschiedene Beispiele.


1.3 Die INIT() Methode
^^^^^^^^^^^^^^^^^^^^^^^^
Im Teil 1.2 der Klasse wir die Init() Methode definiert. Diese Methode
initialisiert den Driver und muss vor allen anderen aufgerufen werden. 
In dieser Methode wird unteranderem die ini-Datei abgearbeitet.


2 UI-Klasse
^^^^^^^^^^^^
Teil 2 der Datei ist die UI-Klasse. Diese Klasse wird verwendet um eine
Test-GUI zu erzeugen. Um eine einfache GUI mit allen cmds-Methoden zu
erzeugen reicht es die Meta-Klassen::

    #Meta Klasse
    __metaclass__ = Metaui
    
    #Driver Klasse
    __driverclass__=NETWORKANALYZER
    
    #Super Klasse des Drivers
    __super_driverclass__=NETWORKAN

 und die __ini__() Methode zu definieren.::

    def __init__(self,instance, ini=None):
        super_ui.__init__(self,instance,ini)

Mit weiteren Modifikationen lässt sich die GUI anpassen. Siehe dazu die Beispiel-Datei `nw_rs_zlv.py.` 

Beim erzeugen einer Instanz dieser Klasse wird eine GUI mit Hilfe von Traits
(http://code.enthought.com/projects/traits/) erzeugt. 

3 main()-Funktion
^^^^^^^^^^^^^^^^^^^^

Teil 3 besteht auch aus zwei Hauptteilen:

1. der Definition einer Standard-ini-Datei
2. der Definition eines Testablaufs
		
In Teil 3.1 wird eine Standard-ini-Datei festgelegt, die benutzt wird, wenn 
keine andere ini-Datei über die Kommandozeile eingegeben wird. Die ini-Datei wird 
innerhalb der Datei definiert, über die Funktion :meth:`format_block` angepasst 
und über `StringIO` als virtuelle Datei zur Verfügung gestellt.

Diese ini-Datei enthält mehrere Blöcke.

- `[description]` für die allgemeine Beschreibung des Geräts
- `[init_value]` für die allgemeine Definition von Werten
- `[channel_1]` für die Definition von Werten speziell für einen Kanal

Da Netzwerkanalysatoren auch mehrere Ausgänge haben können, kann es also auch 
`[channel_2]` usw. geben, in unserem Fall gibt es aber nur `[channel_1]`.
			
Im Block `[description]` werden nun folgende Werte festgelegt::

	description: 'GT_12000A'  	-> Typenbeschreibung
	type:        'NETZWERKANALYSATOR' 	-> zugehörige Python-Klasse
	vendor:      'Giga-tronics' 	-> Hersteller

Alle anderen Feld können frei bleiben, da der Treiber ja unabhängig von der 
genauen Seriennummer usw. sein soll.
				
Im Block `[init_value]` werden folgende Werte festgelegt, die den kleinsten 
gemeinsamen Nenner aller Typen in den ZLV-Serie darstellen::

	[Init_Value]
	fstart: 2e9 	-> niedrigster Frequenz
	fstop: 8e9	-> höchste Frequenz
	fstep: 0.1	-> kleinster Frequenzschritt
	nr_of_channels: 2 -> anzahl der channels
				
Eine Angabe der GPIB-Adresse macht hier eigentlich keinen Sinn, mann 
kann aber eine definieren.
				
Im Block `[Channel_1]` werden Angaben zum Kanal gemacht::

 	SetRefLevel: 10
	SetRBW: 10e3
	SetSpan: 5999991000

Hierbei ist der Aufbau wie folgt::

Name einer Methode des Drivers: Parameter für Methode 		


In Teil 3.2 wird der Netzwerkanalysator und der Treiber mit einem kurzen Testprogramm 
getestet. Dazu wird der Netzwerkanalysator initialisiert, eine Frequenz gesetzt, 
eine Leistung gesetzt und der Ausgang angeschaltet. Danach wird der Signalgeneratur 
runtergefahren.
	
Eine spezielle ini-Datei anlegen
--------------------------------

Die ini-Datei ist eine einfache Textdatei, die z.B. unter dem Namen 
`nw_rs_zlv.ini` gespeichert wird. Sie enthält die oben genannten Blöcke, 
ihr Inhalt ist aber spezieller und nicht nur auf eine ganze Typenreihe, 
sondern auf einen ganze speziellen Typ und ein ganz spezielles Gerät ausgelegt. 
Deshalb ist hier auch die Definition einer 
Seriennummer, Firmwareversion und weiteren Angaben sinnvoll::

	[DESCRIPTION]
	description: 'ZLV-K1'
	type:        'NETWORKANALYZER'
	vendor:      'Rohde&Schwarz'
	serialnr:
	deviceid:
	driver:
	
	[Init_Value]
	fstart: 100e6
	fstop: 6e9
	fstep: 1
	gpib: 18
	virtual: 0
	nr_of_channels: 2

	[Channel_1]
	unit: 'dBm'
	SetRefLevel: 10
	SetRBW: 10e3
	SetSpan: 5999991000
	CreateWindow: 'default'
	CreateTrace: 'default','S22'
	SetSweepCount: 0
	SetSweepPoints: 100
	SetSweepType: 'Log'



Den neuen Treiber testen
-------------------------

Den neuen Treiber kann man am einfachsten Testen, 
indem man ihn einfach aufruft. Dazu geht man mit der 
Kommandozeile ins /mpylab/device/ Verzeichnis und ruft::
	
   python nw_rs_zlv.py 
	
auf. Dann wird die neue Treiberklasse angelegt und das 
Testprogramm gestartet. Wenn das Programm ohne Fehlermeldung 
durchläuft, dann funktioniert alles im Testprogramm definierte.
	
Mit:: 
	
   python nw_rs_zlv.py nw_rs_zlv.ini 
	
kann man den Treiber mit der speziellen ini-Datei konfugurieren und testen.
	
Bei Problemen ist es sinnvoll python mit dem -i Schalter aufzurufen um nach
dem Auftreten des Fehlers im interaktiven Modus zu bleiben. Wenn die neue
Klasse problemlos angelegt wurde, kann man mit::
	
   sg=NETZWERKANALYSATOR()
   ini='nw_rs_zlv.ini'
   err=sg.Init(ini)
   err,freq=sg.SetFreq(1e9)
   ...
	
alle möglichen Befehle durchgehen, um einen Fehler zu finden.


Das beschriebene Verfahren lässt sich natürlich auch auf Leistungsmesser, Verstärker 
usw. anwenden.
