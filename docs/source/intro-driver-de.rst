.. -*-coding: utf-8 -*-

Implementierung eines Treibers
==============================

Dieses Dokument beschreibt an Hand eines einfachen Beispiel die Implementierung eines eigenen 
Treibers in Mpy.

Als Beispiel soll ein Signalgenerator von Giga-tronics mit der Typenbezeichung 12520A aus 
der 12000A Microwave Synthesizers Series dienen.

Der Treiber basiert auf der Klasse :class:`SIGNALGENERATOR`, die wiederum auf der 
Klasse :class:`DRIVER` aufsetzt. Alle Treiber sind im Verzeichnis `/mpy/device/` gespeichert.

Einen neuen Treiber anlegen
---------------------------

Am besten man kopiert einfach einen vorhandenen Treiber, wie z.B. `sg_res_swm.py` und 
speichert die Datei unter einen neuen Namen ab.
Die Syntax sollte dabei aus `sg`, einem Herstellerkürzel und einem Typenkürzel bestehen, 
die durch Unterstriche verbunden werden. 

Allgemein ist die Syntax also: `sg_<Herstellerkürzel>_<Typenkürzel>.py`
In unserem speziellen Fall heißt der Treiber z.B. `sg_gt_12520a.py`

Den neuen Treiber anpassen
--------------------------

Nun öffnet man die neue Treiberdatei. Sie besteht hauptsächlich aus zwei Teilen:

1. der Definition einer neuen Unterklasse für den speziellen Signalgeneratur
2. der Definition einer Funktion :meth:`main`, mit der der Treiber getestet werden kann.

Der erste Teil besteht wiederum aus zwei Teilen:

1. der Definition einer Funktion :meth:`__init__` zum Initialisieren der Klasse
2. der Definition einer Funktion Init zum Initialisieren des Gerätes
		
Im ersten Teil werden in dem Wörterbuch `_cmds` die eigentlichen Befehle zum Steuern des 
Geräts definiert, z.B. :meth:`SetFreq` zum Setzen der Frequenz. Diese Befehle sind 
alle in der :class:`SIGNALGENERATOR`-Klasse festgelegt.

Das Wörterbuch enthält für jeden Eintrag ein Schlüsselwort mit dem allgemeinen Befehl 
als String, z.B. :meth:`SetFreq`. Diesem Schlüsselwort wird eine Liste zugeordnet, wobei jeder 
Listeneintrag ein Tupel ist. Jedes Tupel enthält ein Kommando für einen Befehl und eine 
Vorlage für die darauffolgende Antwort als String. 
Nun muss man in der Dokumentation der Gerätes nachschlagen, über welchen GPIB-Befehl sich z.B. die Frequenz setzen lässt. 

In unserem Beispiel lautet der Befehl::

   CW <Wert> <Einheit>
			
wobei die Einheit `HZ`, `KZ`, `MZ`, `GZ` sein kann. Ein Antwort gibt das Gerät darauf nicht.
			
In das `_cmds`-Wörterbuch musst der :meth:`SetFreq`-Eintrag nun entsprechend angepasst werden::
			
   'SetFreq':  [("'CW %.1f HZ'%freq", None)]
			
Das `%.1f` steht dabei für die Stelle, an der der Wert der Variable `freq` 
geschrieben wird. `%.1f` steht dabei für eine Gleitkommazahl mit einer Nachkommastelle. 
Weil keine Antwort erwartet wird, ist die Vorlage `None`.
			
Etwas schwieriger wird das Ganze, wenn man einen Wert vom Gerät auslesen möchte, z.B. die 
Frequenz mit :meth:`GetFreq`. Der nötige GPIB-Befehl in unserem Beispiel lautet::
			
   OPCW
			
und der Signalgenerator antwortet darauf z.B. mit::
			
   1000000000.0
			
Dementsprechend lautet der :meth:`GetFreq`-Eintrag im `_cmds`-Wörterbuch::
			
   'GetFreq':  [( 'OPCW', r'(?P<freq>%s)'%self._FP)],
			
Da hier eine Antwort, nämlich die aktuelle Frequenz, vom Signalgenerator erwartet wird, 
ist das Template nicht `None`, sondern entspricht einer bestimmten Zeichenfolge die nun näher 
erklärt wird.

Das `r` vor der String-Notation steht für Raw String Notation, und bedeutet dass 
Rückstriche in diesem String keine besondere Bedeutung haben.

Das `%s` bedeuted, dass an dieser Stelle der Wert von `self._FP` eingefügt wird. 
In der Zeichenfolge `self._FP` ist der reguläre Ausdruck für einen Gleitkommazahl 
in exponentieller Schreibweise abgelegt. 
Das hat den Hintergrund, dass Python keine `scanf`-Befehl hat und Zahl aus Strings nur 
über reguläre Ausdrücke extrahieren kann. Der Wert von `self._FP` wird in der 
:class:`SIGNALGERATOR`-Klasse festgelegt.

Das `(?P<freq>%s)` bedeuted nun, dass der Gleitkommawert der Frequenz aus der 
Antwortzeichenkette 
extrahiert wird und als Variable `freq` gespeichert wird. Das passiert intern 
in der :class:`DRIVER`-Klasse in der :meth:`_gpib_query`-Funktion über ein `re.match`. 
Das Ergebnis von `re.match` ist ebenfalls ein MatchObject, dass mit `groupdict` 
in ein Wörterbuch umgewandelt 
werden kann, welches dann den Schlüssel `freq` und die Frequenz enthält.
			
Für alle anderen Befehle kann nach dem gleichen Prinzip vorgegangen werden.
			
In Teil b werden im Wörterbuch presets die Befehle vor Voreinstellungen vorgenommen. 
Auch diese Befehle müssen wenn nötig nach dem obigen Schema angepasst werden.
			
Teil B besteht auch aus zwei Hauptteilen:

1. der Definition einer Standard-ini-Datei
2. der Definition eines Testablaufs
		
In Teil a wird eine Standard-ini-Datei festgelegt, die benutzt wird, wenn keine andere 
ini-Datei über die Kommandozeile eingegeben wird. Die ini-Datei wird innerhalb der Datei 
definiert, über die Funktion :meth:`format_block` angepasst und über `StringIO` als 
virtuelle Datei 
zur Verfügung gestellt.

Diese ini-Datei enthält mehrere Blöcke.

- `[description]` für die allgemeine Beschreibung des Geräts
- `[init_value]` für die allgemeine Definition von Werten
- `[channel_1]` für die Definition von Werten speziell für einen Kanal

Da Signalgeneratoren auch mehrere Ausgänge haben können, kann es also auch 
`[channel_2]` usw. geben, 
in unserem Fall gibt es aber nur `[channel_1]`.
			
Im Block `[description]` werden nun folgende Werte festgelegt::

   description: 'GT_12000A'  	-> Typenbeschreibung
   type:        'SIGNALGENERATOR' 	-> zugehörige Python-Klasse
   vendor:      'Giga-tronics' 	-> Hersteller

Alle anderen Feld können frei bleiben, da der Treiber ja unabhängig von der 
genauen Seriennummer usw. sein soll.
				
Im Block `[init_value]` werden folgende Werte festgelegt, die den kleinsten gemeinsamen Nenner aller Typen in den 12000A-Serie darstellen::

   [Init_Value]
   fstart: 2e9 	-> niedrigster Frequenz
   fstop: 8e9	-> höchste Frequenz
   fstep: 0.1	-> kleinster Frequenzschritt
				
Eine Angabe der GPIB-Adresse macht hier eigentlich keinen Sinn, mann kann aber eine definieren.
				
Im Block `[Channel_1]` werden Angaben zum Kanal gemacht::

   name: RFOut		-> Name 
   level: -100		-> Leistungswert
   unit: 'dBm'		-> Einheit
   outputstate: 0	-> Ausgangsstatus (0=Aus, 1=An)
			
In Teil b wird der Signalgenerator und der Treiber mit einem kurzen Testprogramm getestet. 
Dazu wird der Signalgenerator initialisiert, eine Frequenz gesetzt, eine Leistung gesetzt 
und der Ausgang angeschaltet. Danach wird der Signalgeneratur runtergefahren.
	
Eine spezielle ini-Datei anlegen
--------------------------------

Die ini-Datei ist eine einfache Textdatei, die z.B. unter dem Namen `sg_gt_12520a.ini` 
gespeichert wird. Sie enthält die oben genannten Blöcke, ihr Inhalt ist aber spezieller 
und nicht nur auf eine ganze Typenreihe, sondern auf einen ganze speziellen Typ und 
ein ganz spezielles Gerät ausgelegt. Deshalb ist hier auch die Definition einer 
Seriennummer, Firmwareversion und weiteren Angaben sinnvoll::

   [description]
   description: 12520A
   type:        SIGNALGENERATOR
   vendor:      Giga-tronics
   serialnr:    121015
   deviceid:	
   driver:      sg_rs_swm.py
   version:     0.73
   build-nr:    49.24

   [Init_Value]
   fstart: 10e6
   fstop: 20e9
   fstep: 0.1
   gpib: 6
   virtual: 0

   [Channel_1]
   name: RFOut
   level: -100
   unit: 'dBm'
   outputstate: 0


Den neuen Treiber testen
-------------------------

Den neuen Treiber kann man am einfachsten Testen, indem man ihn einfach aufruft. Dazu geht man mit der Kommandozeile ins /mpy/device/ Verzeichnis und ruft::
	
   python sg_gt_12000a.py 
	
auf. Dann wird die neue Treiberklasse angelegt und das Testprogramm gestartet. Wenn das 
Programm ohne Fehlermeldung durchläuft, dann funktioniert alles im Testprogramm definierte.
	
Mit:: 
	
   python sg_gt_12000a.py sg_gt_12520a.ini 
	
kann man den Treiber mit der speziellen ini-Datei konfugurieren und testen.
	
Bei Problemen ist es sinnvoll python mit dem -i Schalter aufzurufen um nach dem Auftreten 
des Fehlers im interaktiven Modus zu bleiben. Wenn die neue Klasse problemlos angelegt 
wurde, kann man mit::
	
   sg=SIGNALGENERATOR()
   ini='sg_gt_12520a.ini'
   err=sg.Init(ini)
   err,freq=sg.SetFreq(1e9)
   ...
	
alle möglichen Befehle durchgehen, um einen Fehler zu finden.


Das beschriebene Verfahren lässt sich natürlich auch auf Leistungsmesser, Verstärker 
usw. anwenden.

