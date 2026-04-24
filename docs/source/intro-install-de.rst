.. -*-coding: utf-8 -*-

Installation von ``MpyLab`` für Anwender
========================================

Dieses Dokument beschreibt die Installation von ``MpyLab`` für Anwender.

Anwender von ``MpyLab`` (im Gegensatz zu Entwicklern) installieren direkt von
**PyPI** (https://pypi.org/)::

   pip3 install mpylab

Die erforderlichen Abhängigkeiten werden dabei automatisch mitinstalliert.
Es wird dringend empfohlen, eine virtuelle Umgebung zu nutzen, z. B.::

    > mkdir venv && cd venv
    > uv venv
    > source ./.venv/bin/activate
    (venv) > uv pip install mpylab

Die Verwendung von ``uv`` (https://docs.astral.sh/uv/) ist optional.
