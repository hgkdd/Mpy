.. -*-coding: utf-8 -*-

FAQs
====


Q:	
   Warum wird Python als Programmiersprache verwendet?

A:	
   Python (http://www.python.org/) besitzt mehrere Vorteile:

	- es ist einfach zu lernen
	- es ist gut dokumentiert
	- es ist kostenlos
	- es läuft auf vielen Platformen und ist unabhängig
	- es gibt viele Module die es für wissenschaftliche Berechnungen, Messaufgaben und graphische Datenausgabe hervoragend geeignet sind
	
	
	
Q: 	
   Welche Python-Version sollte benutzt werden?

A: 	
   Früher musste eine bestimmte Python-Version benutzt werden, da einige Treiber hart gegen einen bestimmten Compiler programmiert waren. Für die neue Treiber trifft diese nicht mehr zu, und die genaue Python-Version sollte eigentlich keine Rolle mehr spielen.

   Da Mpy aber noch einige andere Pakete voraussetzt, muss man sich immer ein bisschen daran orientieren, für welche Python-Version diese Pakete zu Verfügung stehen. 
	
   Aktuell ist es ratsam mit Python 2.5 zu arbeiten.
	


Q:	
   Welchen Editor sollte man benutzen?

A:
   Das ist letzendlich eine Geschmackssache. Man kann z.B. Emacs (http://de.wikipedia.org/wiki/Emacs) oder Notepad++ (http://de.wikipedia.org/wiki/Notepad%2B%2B) benutzen. Diese Unterstützen viele nützliche Features wie Syntaxhervorhebung und Mehrfachansicht.

   Speziell für Python gibt es auch noch Stani's Python Editor (http://sourceforge.net/projects/spe) oder The Eric Python IDE (http://eric-ide.python-projects.org/), die als integrierte Entwicklungsumgebung gedacht sind.



Q:	
   Welche Kodierung sollte man benutzen?

A:	
   Die meisten Quelltexte verwenden UTF-8 (8-bit Unicode Transformation Format).



Q:	
   Welchen Debugger sollte man benutzen?

A:
   Ein Vorschlag wäre WinPDB (http://winpdb.org/). Anders als der Name vermuten lässt, ist dieser Debugger nicht nur für Windows konzipiert, sondern platformunabhängig.



Q:
   Welche Pakete werden sonst noch benötigt?

A:
   Außer Python werden noch folgende Pakete benötigt:

      - NumPy	-> zur numerischen Matrizenrechnung 	-> http://numpy.scipy.org/
      - SciPy	-> für wissenschaftliche Berechnungen 	-> http://www.scipy.org/
      - PyVISA 	-> zur Kommunikation über den GBIP-Bus	-> http://pyvisa.sourceforge.net/
      - scuq	-> zur Fehlerfortplanzung und Einheitenrechnung -> `hg clone ssh://hg@etec.zih.tu-dresden.de/scuq`
	
	
	
Q:	
   Gibt es eine Möglichkeit neue Pakete und Quelltext auszuprobieren, ohne die lauffähige Python-Version zu gefährden?

A:	
   Mit VirtualEnv (http://pypi.python.org/pypi/virtualenv) ist es möglich isolierte Python-Umgebungen zu erzeugen. Eine solche isolierte Umgebung kann wie eine Sandbox genutzt werden, um neue Dinge auszuprobieren. Falls etwas schiefgeht, kehrt man einfach wieder in die ursprüngliche Umgebung zurück.



Q:
   Wie kommt man an die Quelltexte?

A:
   Mpy benutzt Mercurial (http://de.wikipedia.org/wiki/Mercurial) als Versionskontrollsystem. Mercurial ist ein verteiltes, plattformunabhängiges Versionskontrollsystem. Mercurial wurde auch hauptsächlich in Python geschrieben und wird primär über die Kommandozeile mit hg benutzt. Diese Abkürzung steht für das chemische Symbol für Quecksilber. Für Windows gibt es auch ein graphisches Front-End namens TortoiseHG (http://bitbucket.org/tortoisehg/), dass als Windows Explorer Erweiterung funktioniert. 

   Das Hauptrepository liegt in Dresden und ist über `ssh://hg@etec.zih.tu-dresden.de/Mpy` zu erreichen. Da Mercurial ein verteilten Versionskontrollsystem ist, können nebeneinander aber mehrere Repositories existieren, die man auch untereinander synchronisieren kann.

