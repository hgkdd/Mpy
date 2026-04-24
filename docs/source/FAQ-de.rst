.. -*-coding: utf-8 -*-

FAQs
====

Q:
    Wie installiere ich ``MpyLab`` als Anwender?

A:
    Anwender sollten eine lokale virtuelle Umgebung verwenden. Der einfachste Weg mit
    ``uv`` (https://docs.astral.sh/uv/) sieht so aus::

        > mkdir Mpylab
        > cd Mpylab
        > uv venv
        > source .venv/bin/activate
        > uv pip install mpylab

Q:
    Wie installiere ich ``MpyLab`` als Entwickler?

A:
    Entwickler sollten eine editierbare Version aus den lokalen Git-Repositories in
    einer virtuellen Umgebung installieren. Der einfachste Weg mit ``uv`` sieht so aus::

        > mkdir mpylab-develop
        > cd mpylab-develop
        > git clone https://gitlab.hrz.tu-chemnitz.de/chair-of-electromagnetic-theory-and-compatibility-at-tu-dresden/mpylab/mpylab.git
        > git clone https://gitlab.hrz.tu-chemnitz.de/chair-of-electromagnetic-theory-and-compatibility-at-tu-dresden/mpylab/scuq.git
        > mkdir venv-mpylab
        > cd venv-mpylab
        > uv venv
        > source .venv/bin/activate
        > uv pip install -e ../scuq
        > uv pip install -e ../mpylab

Q:
    Wo finde ich Dokumentation zu ``MpyLab``?

A:
    Die Dokumentation ist online verfügbar:
    (https://mpylab.readthedocs.io/en/latest/)

Q:
    Wie kann ich zu ``MpyLab`` beitragen?

A:
    Registrierte Mitwirkende können direkt ins Repository pushen. Andernfalls sollte ein
    Pull Request erstellt werden. Details siehe GitHub-Dokumentation:
    (https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/creating-a-pull-request).

Q:
   Warum wird Python als Programmiersprache verwendet?

A:
   Python (http://www.python.org/) hat mehrere Vorteile:

   - leicht zu erlernen
   - gut dokumentiert
   - frei verfügbar
   - auf vielen Plattformen nutzbar
   - viele Module für wissenschaftliches Rechnen, Messtechnik und grafische Ausgabe

Q:
    Welche Python-Version sollte verwendet werden?

A:
   Es sollte Python 3.8 oder höher verwendet werden.

Q:
   Welcher Editor sollte verwendet werden?

A:
   Das ist vor allem Geschmackssache. Einen Überblick über Python-Entwicklungsumgebungen
   gibt es hier:
   (https://wiki.python.org/moin/IntegratedDevelopmentEnvironments).
   Häufig genutzte IDEs sind PyCharm (https://www.jetbrains.com/pycharm/) und
   Visual Studio Code (https://code.visualstudio.com/).

Q:
   Welche Zeichenkodierung sollte verwendet werden?

A:
   Standard ist UTF-8 (8-bit Unicode Transformation Format).

Q:
   Welchen Debugger sollte man verwenden?

A:
    Python enthält den Debugger ``pdb`` bereits selbst:
    (https://docs.python.org/3/library/pdb.html).
    Die in gängigen IDEs integrierten Debugger sind mindestens ebenso gut.

Q:
   Welche weiteren Pakete werden benötigt?

A:
   Die Abhängigkeiten stehen in ``requirements.txt``:
   (https://github.com/hgkdd/Mpy/blob/main/requirements.txt).

Q:
    Wie kann ich Änderungen testen, ohne die stabile Installation zu beeinflussen?

A:
    ``MpyLab`` sollte immer in einer virtuellen Umgebung installiert werden.
    Nach der Installation per ``uv pip install -e`` sind Änderungen in den lokalen
    Quellverzeichnissen sofort in der Umgebung verfügbar. Getestete Änderungen
    sollten anschließend ins zentrale Git-Repository übernommen werden.

Q:
   Wie bekomme ich den Quellcode?

A:
   ``MpyLab`` und ``scuq`` (sowie weitere Projekte) liegen auf GitLab TU Chemnitz:
   (https://gitlab.hrz.tu-chemnitz.de/chair-of-electromagnetic-theory-and-compatibility-at-tu-dresden/mpylab).
