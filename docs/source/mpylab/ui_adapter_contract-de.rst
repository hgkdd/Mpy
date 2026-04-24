UI-Adapter-Vertrag
==================

Dieses Dokument beschreibt den UI-Adapter-Vertrag der Messlaufzeit in ``mpylab.env``.
Ziel ist, dass Terminal- (TUI) und GUI-Implementierungen dieselbe Messlogik nutzen können.

Primäre Methoden
----------------

- ``ask(msg, buttons, level, data) -> int``
  Zeigt eine Nutzermeldung an und gibt den Index des gewählten Buttons zurück.
- ``emit_log(block, *args) -> None``
  Sendet Log-Ereignisse an konfigurierte Log-Senken.
- ``poll_key() -> int | None``
  Nicht-blockierendes Key-Polling. Liefert ASCII-Code oder ``None``.
- ``check_interrupt() -> int | None``
  Rückwärtskompatibler Alias, der auf ``poll_key()`` delegiert.
- ``pre_user_event() / post_user_event()``
  Hooks um blockierende Benutzerinteraktionen.
- ``run_interactive(obj, banner)``
  Startet eine interaktive Sitzung, falls unterstützt.

Integration in ``Measure``
--------------------------

``Measure._setup_ui_adapter()`` bindet Legacy-Attribute an den Adapter:

- ``self.messenger`` -> ``ui.ask``
- ``self.UserInterruptTester`` -> ``ui.check_interrupt``
- ``self.PollKey`` -> ``ui.poll_key``
- ``self.PreUserEvent`` -> ``ui.pre_user_event``
- ``self.PostUserEvent`` -> ``ui.post_user_event``

Zur Kompatibilität werden beide Schreibweisen für den Interrupt-Setter unterstützt:

- ``set_user_interrupt_tester(...)`` (bevorzugt)
- ``set_user_interrupt_Tester(...)`` (Legacy-Alias)

Hinweis zur Migration
---------------------

Interner Code sollte ausschließlich ``set_user_interrupt_tester(...)`` verwenden.
Der Legacy-Alias ``set_user_interrupt_Tester(...)`` bleibt für externe Skripte und
bestehende Notebooks zur Wahrung der Rückwärtskompatibilität verfügbar.

Nutzung im Kernel
-----------------

Messkerne verwenden ``poll_key()`` als expliziten Pfad für Tastatureingaben.
Wenn ein direkter Handler nicht aufrufbar ist, kann ``resolve_poll_key(...)`` als
Fallback ``self.PollKey`` aus den lokalen Variablen des Aufrufers auflösen.
