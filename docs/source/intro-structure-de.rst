.. -*-coding: utf-8 -*-

Verzeichnisstruktur
===================

Dieses Dokument gibt einen Überblick über die Verzeichnisstruktur von ``MpyLab``.

Hauptverzeichnis von ``MpyLab``:
    * ``src/mpylab``: allgemeiner Source-Tree des Frameworks
    * ``test``: spezielle Messprogramme, die auf das Framework zugreifen (hauptsächlich zum Testen)
    * ``docs``: Dokumentationsbaum

Unterverzeichnis ``src/mpylab``:
    * ``device``: Treiber für aktive und passive Geräte
    * ``env``: Messumgebungen (MVK, GTEM-Zelle)
    * ``tools``: Hilfsprogramme und Utility-Funktionen

Unterverzeichnis ``device``:
    * ``device.py``: Wrapper zum Umschreiben alter Treiber (in ``C``; heute nicht mehr verwendet) auf neue Treiber mit einheitlicher Schnittstelle
    * ``driver.py``: Basisklasse der neuen in Python geschriebenen Treiber

Darunter liegen Treiberklassen für unterschiedliche Gerätetypen:
    * ``amplifier.py``: für Verstärker
    * ``nport.py``: für Antennen, Kabel, Richtkoppler usw.
    * ``powermeter.py``: für Leistungsmesser
    * ``signalgenerator.py``: für Signalgeneratoren
    * ...

Zusätzlich gibt es spezielle Treiber für konkrete Geräte, z. B.:
    * ``amp_ifi_smx25.py``: Verstärker von IFI, Typ SMX25
    * ``pm_gt_8540c.py``: Leistungsmesser von GigaTronics, Typ 8542C Universal Power Meter
    * ``sg_rs_smr.py``: Signalgenerator von Rohde&Schwarz, Typ SMR
    * ``sg_rs_swm.py``: Signalgenerator von Rohde&Schwarz, Typ SWM

Die Benennung folgt dem Muster ``amp/pm/sg_<Herstellerkürzel>_<Typkürzel>.py``.
