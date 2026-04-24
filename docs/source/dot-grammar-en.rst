DOT Grammar and Parser Generation
=================================

``mpylab.tools.dot`` is generated code and must not be edited manually.

Source of truth
---------------

- grammar source: ``src/mpylab/tools/dot.g``
- generated parser: ``src/mpylab/tools/dot.py``
- maintained runtime parser API: ``src/mpylab/tools/dotparser.py``

Migration status
----------------

``mpylab.tools.dotparser`` is an active, started migration attempt to move away
from the generated ``dot.py`` parser. It is kept in the active API and may be
used more broadly in future code paths.

Regeneration
------------

Use yapps2 on ``dot.g`` to regenerate ``dot.py``. Keep parser behavior documentation
on this page (and related docs pages), not as manual docstrings in generated output.

Supported language subset
-------------------------

The grammar in ``dot.g`` supports a practical subset of DOT including:

- ``graph`` and ``digraph``
- node and edge statements
- attribute lists (``[...]``)
- comments (``#`` and ``//``)
- identifiers as IDs, numbers, and quoted strings
