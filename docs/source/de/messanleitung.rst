.. -*-coding: utf-8 -*-

Messablauf in Modenverwirbelungskammern
=======================================

Diese Seite fasst den praktischen Messablauf mit ``MpyLab`` für
Modenverwirbelungskammern (Reverberation Chambers) zusammen.

Überblick
---------

``MpyLab`` integriert Geräteansteuerung, Datenerfassung und Auswertung in einer
Python-Laufzeit. Typische Messungen bestehen aus einem kompakten Messskript und
einer Konfigurationsdatei.

Empfohlenes Projektlayout pro Messkampagne:

- ein eigener Ordner für Messskript und Konfiguration
- optional eine ``.dot``-Datei zur Beschreibung des Messgraphen
- Autosave-/Ergebnisdateien, die von der Laufzeit erzeugt werden

Messlaufzeit
------------

Ein Messlauf erzeugt ein ``MSC``-Objekt, entweder neu oder aus gespeichertem
Zustand (pickle). Die Laufzeit übernimmt:

- Instrumentenkommunikation
- Ausführung von Messroutinen
- Auswertungsroutinen
- Autosave und Persistenz von Zwischenständen

Durch Persistenz können längere Messungen an Checkpoints fortgesetzt werden.

Messgraph (DOT)
---------------

Die Topologie des Aufbaus (Instrumente, Kabel, Koppler, Dämpfer, Signalpfade)
wird als Graph in einer ``.dot``-Datei beschrieben. Dieser Graph wird in der
Laufzeit verwendet, um Signalpfade aufzulösen und Messgrößen zu bewerten.

Die Parser-/Grammatikreferenzen sind separat dokumentiert:

- :doc:`dot-grammar`
- :doc:`dat-file-grammar`

Historische Fassung
-------------------

Unterhalb der aktuellen Anleitung ist die historische, ausführliche Version
weiterhin verfügbar:

.. toctree::
   :maxdepth: 1

   messanleitung-historisch.rst
