Documentation Maintenance
=========================

This documentation uses generated API pages and an audit step.

Public API policy
-----------------

The audit script treats the following symbols as public API:

- importable ``*.py`` modules below ``src/mpylab`` (excluding ``__init__.py`` and ``legacy`` modules)
- top-level classes/functions whose names do not start with ``_``
- class methods whose names do not start with ``_``
- Qt event-handler methods (for example ``mousePressEvent`` or ``closeEvent``) are excluded from API documentation and docstring coverage
- generated modules are not documented inside generated Python files

Docstrings for public API symbols must be in English.

Generated code policy
---------------------

``src/mpylab/tools/dot.py`` is generated from ``src/mpylab/tools/dot.g`` via yapps2.
Do not add or maintain docstrings in ``dot.py`` because regeneration overwrites them.

Use this documentation path instead:

- parser grammar and generation notes in ``dot.g`` / dedicated RST pages
- public runtime/parser behavior via ``mpylab.tools.dotparser``
- ``mpylab.tools.dotparser`` is intentionally kept active as an in-progress migration path away from generated ``dot.py``

Current exclusions in automation:

- docs coverage excludes ``mpylab.tools.dot``
- docstring coverage excludes ``mpylab.tools.dot``

Local commands
--------------

Generate API module page:

.. code-block:: bash

   python tools/docs_generate_api.py

Audit documentation consistency:

.. code-block:: bash

   python tools/docs_audit.py

Strict audit (fail on uncovered modules):

.. code-block:: bash

   python tools/docs_audit.py --fail-on-uncovered

Docstring coverage report for the public API:

.. code-block:: bash

   python tools/docs_audit.py

Strict docstring audit (fail when public symbols are undocumented):

.. code-block:: bash

   python tools/docs_audit.py --fail-on-missing-docstrings

CI behavior
-----------

- ``docs-check`` runs ``tools/docs_audit.py``.
- ``docs-check`` builds docs with ``sphinx-build -W``.

If modules are added or renamed, regenerate ``docs/source/api/modules.rst``.
