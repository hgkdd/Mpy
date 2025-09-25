.. -*-coding: utf-8 -*-

FAQs
====

Q:
    Wie installiere ich ``Mpylab`` als Nutzer?


A:
    Nutzer sollten eine lokale virtuelle Umgebung verwenden. Der einfachste Weg unter Verwendung von ``uv`` (https://docs.astral.sh/uv/) sieht so aus::

        > mkdir Mpylab
        > cd Mpylab
        > uv venv
        > source .venv/bin/activate
        > uv pip install Mpylab

Q:
    Wie installiere ich ``Mpylab`` als Entwickler?


A:
    Entwickler sollten aus den lokalen Git-Repositories eine editerbare Version in eine lokale virtuelle Umgebung installieren. Der einfachste Weg unter Verwendung von ``uv`` (https://docs.astral.sh/uv/) sieht so aus::

        > mkdir mpylab-develop
        > cd mpylab-develop
        > gh repo clone hgkdd/Mpy
        > gh repo clone hgkdd/scuq
        > mkdir venv-mpylab
        > cd venv-mpylab
        > uv venv
        > source .venv/bin/activate
        > uv pip install -e ../scuq
        > uv pip inatall -e ../Mpy


Q:
    Wo finde ich die Dokumentation zu ``Mpylab``?

A:
    Die Documentation ist online verfügbar: (https://mpylab.readthedocs.io/en/latest/)


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
   Es sollte eine Python-Version ab 3.8 verwendet werden.
	


Q:	
   Welchen Editor sollte man benutzen?

A:
   Das ist letzendlich eine Geschmackssache. Eine Übersicht über Python Entwicklungsumgebungen findet
   man z.B. hier: (https://wiki.python.org/moin/IntegratedDevelopmentEnvironments).
   Populäre IDEs sind PyCharm (https://www.jetbrains.com/pycharm/) oder
   Visual Studio Code (https://code.visualstudio.com/).


Q:	
   Welche Kodierung sollte man benutzen?

A:	
   Standart ist UTF-8 (8-bit Unicode Transformation Format).



Q:	
   Welchen Debugger sollte man benutzen?

A:
    Python enthält einen eigenen Debugger pdb (https://docs.python.org/3/library/pdb.html).
    Mindestens genau so gut sind die in populären IDEs integrierten Debugger.



Q:
   Welche Pakete werden sonst noch benötigt?

A:
   Die Abhängigkeiten finden sich in der Datei ``requirements.txt`` (https://github.com/hgkdd/Mpy/blob/main/requirements.txt).

	
	
Q:	
    Wie probiere ich Änderungen aus ohne dass hierfür die Lauffähigkeit der stabilen Version gefährdet wird?

A:
    ``MpyLab`` sollte **immer** in einer virtuellen Umgebung installiert werden.
    Dies geht (beispielsweise) wie folgt::

        /home/USER/dev/test % gh repo clone hgkdd/Mpy
        Cloning into 'Mpy'...
        remote: Enumerating objects: 3515, done.
        remote: Counting objects: 100% (40/40), done.
        remote: Compressing objects: 100% (36/36), done.
        remote: Total 3515 (delta 10), reused 16 (delta 3), pack-reused 3475 (from 2)
        Receiving objects: 100% (3515/3515), 29.05 MiB | 6.44 MiB/s, done.
        Resolving deltas: 100% (2266/2266), done.
        /home/USER/dev/test % gh repo clone hgkdd/scuq
        Cloning into 'scuq'...
        remote: Enumerating objects: 294, done.
        remote: Counting objects: 100% (294/294), done.
        remote: Compressing objects: 100% (111/111), done.
        remote: Total 294 (delta 174), reused 291 (delta 171), pack-reused 0 (from 0)
        Receiving objects: 100% (294/294), 787.84 KiB | 4.40 MiB/s, done.
        Resolving deltas: 100% (174/174), done.
        /home/USER/dev/test % mkdir venv-mpy-develop
        /home/USER/dev/test % cd venv-mpy-develop 
        /home/USER/dev/test/venv-mpy-develop % uv venv
        Using CPython 3.11.2 interpreter at: /opt/local/bin/python3.11
        Creating virtual environment at: .venv
        Activate with: source .venv/bin/activate
        /home/USER/dev/test/venv-mpy-develop % source .venv/bin/activate
        (venv-mpy-develop) /home/USER/dev/test/venv-mpy-develop % uv pip install -e ../scuq
        Resolved 2 packages in 580ms
              Built scuq @ file:///home/USER/dev/test/scuq
        Prepared 2 packages in 789ms
        Installed 2 packages in 13ms
         + numpy==2.3.3
         + scuq==0.9.1 (from file:///home/USER/dev/test/scuq)
        (venv-mpy-develop) /home/USER/dev/test/venv-mpy-develop % uv pip install -e ../Mpy 
        Resolved 27 packages in 659ms
              Built mpylab @ file:///home/USER/dev/test/Mpy
        Prepared 8 packages in 8.13s
        Installed 25 packages in 53ms
         + bidict==0.23.1
         + contourpy==1.3.3
         + cycler==0.12.1
         + fonttools==4.60.0
         + gpib-ctypes==0.3.0
         + kiwisolver==1.4.9
         + levenshtein==0.27.1
         + matplotlib==3.10.6
         + mpylab==0.9.4 (from file:///home/USER/dev/test/Mpy)
         + packaging==25.0
         + pathvalidate==3.3.1
         + pillow==11.3.0
         + ply==3.11
         + pydot==4.0.1
         + pyparsing==3.2.5
         + pyserial==3.5
         + python-dateutil==2.9.0.post0
         + pyusb==1.3.1
         + pyvisa==1.15.0
         + pyvisa-py==0.8.1
         + rapidfuzz==3.14.1
         + scipy==1.16.2
         + simpleeval==1.0.3
         + six==1.17.0
         + typing-extensions==4.15.0
        (venv-mpy-develop) /home/USER/dev/test/venv-mpy-develop %

    Änderunden an den Quelldateien in ``/home/USER/dev/test/Mpy`` und ``/home/USER/dev/test/scuq`` sind anschließend automatisch im ``venv`` verfügbar. Erprobte Änderungen sollten dann ins zentrale Git-Repository eingespielt werden.


Q:
   Wie kommt man an die Quelltexte?

A:
   ``MpyLab`` und ``scuq`` liegen auf Github (https://github.com/hgkdd).


