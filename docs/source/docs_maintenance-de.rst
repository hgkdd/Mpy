Dokumentationspflege
====================

Diese Dokumentation nutzt generierte API-Seiten und einen Audit-Schritt.

Public-API-Richtlinie
---------------------

Das Audit-Skript behandelt folgende Symbole als Public API:

- importierbare ``*.py``-Module unter ``src/mpylab`` (ohne ``__init__.py`` und ``legacy``-Module)
- Top-Level-Klassen/-Funktionen, deren Name nicht mit ``_`` beginnt
- Klassenmethoden, deren Name nicht mit ``_`` beginnt
- Qt-Event-Handler-Methoden (z. B. ``mousePressEvent`` oder ``closeEvent``) sind von API-Dokumentation und Docstring-Coverage ausgenommen
- generierte Module werden nicht in generierten Python-Dateien dokumentiert

Docstrings für Public-API-Symbole müssen auf Englisch sein.

Richtlinie für generierten Code
-------------------------------

``src/mpylab/tools/dot.py`` wird aus ``src/mpylab/tools/dot.g`` via yapps2 generiert.
Docstrings in ``dot.py`` dürfen nicht manuell gepflegt werden, da sie bei jeder
Regeneration überschrieben werden.

Stattdessen gilt dieser Dokumentationspfad:

- Parser-Grammatik und Generierungshinweise in ``dot.g`` / dedizierten RST-Seiten
- öffentliches Laufzeit-/Parser-Verhalten über ``mpylab.tools.dotparser``
- ``mpylab.tools.dotparser`` bleibt als aktive Migrationsbasis weg von ``dot.py`` erhalten

Aktuelle Ausschlüsse in der Automatisierung:

- Docs-Coverage schließt ``mpylab.tools.dot`` aus
- Docstring-Coverage schließt ``mpylab.tools.dot`` aus

Lokale Befehle
--------------

API-Modulseite generieren:

.. code-block:: bash

   python tools/docs_generate_api.py

Dokumentationskonsistenz prüfen:

.. code-block:: bash

   python tools/docs_audit.py

Striktes Audit (Fehler bei undokumentierten Modulen):

.. code-block:: bash

   python tools/docs_audit.py --fail-on-uncovered

Docstring-Coverage für die Public API:

.. code-block:: bash

   python tools/docs_audit.py

Striktes Docstring-Audit (Fehler bei fehlenden Public-API-Docstrings):

.. code-block:: bash

   python tools/docs_audit.py --fail-on-missing-docstrings

Sprach-Pendant-Audit (Fehler bei unvollständigen ``-de``/``-en`` Seitenpaaren):

.. code-block:: bash

   python tools/docs_audit.py --fail-on-missing-language-counterparts

Docstring-Sprachaudit (Fehler bei potenziell nicht-englischen Public-API-Docstrings):

.. code-block:: bash

   python tools/docs_audit.py --fail-on-non-english-docstrings

CI-Verhalten
------------

- ``docs-check`` führt ``tools/docs_audit.py`` aus.
- ``docs-check`` baut die Doku mit ``sphinx-build -W``.

Wenn Module hinzugefügt oder umbenannt werden, ``docs/source/api/modules.rst`` neu erzeugen.
