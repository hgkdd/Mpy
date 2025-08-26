.. -*-coding: utf-8 -*-

Verzeichnisstruktur
====================

Hauptverzeichnis von `Mpy`:
	- `mpylab`	-> allgemeine Quelldateien des Frameworks
	- `test` -> spezielle Messprogramme, die auf das Framework zugreifen

Unterverzeichnis `mpylab`:
	- `device`	-> Treiber für aktive und passive Geräte
	- `doc`		-> Dokumentation
	- `env`		-> Messumgebungen (MVK, GTEM-Zelle)
	- `tools`	-> alles möglichen Hilfsprogramme und Funktionen

Unterverzeichnis `device`:
	- `device.py`	-> Wrapper, um von alten Treiber auf neue umzuschreiben und für die darüberliegende Schicht ein einheitliches Interface zu geben
	- `driver.py`	-> die Mutter aller neuen Treiber, die in Python geschrieben sind
	
Darunter existieren verschiedene Klassen von Treiber für verschiedene Gerätetypen:
	- `amplifier.py`		-> für Verstärker
	- `nport.py`			-> für Antennen, Kabel, Richtkoppler, ...
	- `powermeter.py`		-> für Leistungsmesser
	- `signalgenerator.py`	-> für Signalgeneratoren
	
Darunter existieren weiterhin spezielle Treiber für spezielle Geräte, z.B.:
	- `amp_ifi_smx25.py`	-> Verstärker von IFI, Typ SMX25
	- `pm_gt_8540c.py`		-> Leistungsmesser von GigaTronics, Typ 8542C Universal Power Meter
	- `sg_rs_smr.py`		-> Signalgenerator von Rohde&Schwarz, Typ SMR
	- `sg_rs_swm.py`		-> Signalgenerator von Rohde&Schwarz, Typ SWM

Die Syntax ist also `amp/pm/sg_<Herstellerkürzel>_<Typenkürzel>.py`