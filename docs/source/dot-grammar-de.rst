DOT-Grammatik und Parser-Generierung
====================================

``mpylab.tools.dot`` ist generierter Code und darf nicht manuell bearbeitet werden.

Verbindliche Quellen
--------------------

- Grammatikquelle: ``src/mpylab/tools/dot.g``
- generierter Parser: ``src/mpylab/tools/dot.py``
- gepflegte Runtime-Parser-API: ``src/mpylab/tools/dotparser.py``

Migrationsstatus
----------------

``mpylab.tools.dotparser`` ist eine aktive, bereits gestartete Migration weg vom
generierten ``dot.py``-Parser. Das Modul bleibt Teil der aktiven API und kann
in weiteren Codepfaden genutzt werden.

Regenerierung
-------------

Zur Regenerierung ``dot.g`` mit yapps2 ausführen. Die Dokumentation des
Parser-Verhaltens gehört auf diese Seite (und verwandte Doku-Seiten), nicht als
manuell gepflegte Docstrings in generierten Ausgaben.

Unterstützter Sprachumfang
--------------------------

Die Grammatik in ``dot.g`` unterstützt einen praxisnahen DOT-Teilumfang, darunter:

- ``graph`` und ``digraph``
- Node- und Edge-Statements
- Attributlisten (``[...]``)
- Kommentare (``#`` und ``//``)
- Bezeichner als IDs, Zahlen und gequotete Strings
