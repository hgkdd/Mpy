UI Adapter Contract
===================

The measurement runtime in ``mpylab.env`` supports a small UI adapter
contract so that terminal (TUI) and future GUI implementations can use the
same measurement logic.

Primary methods
---------------

- ``ask(msg, buttons, level, data) -> int``
  Presents a user message and returns the selected button index.
- ``emit_log(block, *args) -> None``
  Sends log events to configured log sinks.
- ``poll_key() -> int | None``
  Non-blocking key polling. Returns ASCII code or ``None``.
- ``check_interrupt() -> int | None``
  Backward-compatible alias that delegates to ``poll_key()``.
- ``pre_user_event() / post_user_event()``
  Hooks around blocking user interactions.
- ``run_interactive(obj, banner)``
  Starts an interactive session if supported.

Integration in ``Measure``
--------------------------

``Measure._setup_ui_adapter()`` binds legacy attributes to the adapter:

- ``self.messenger`` -> ``ui.ask``
- ``self.UserInterruptTester`` -> ``ui.check_interrupt``
- ``self.PollKey`` -> ``ui.poll_key``
- ``self.PreUserEvent`` -> ``ui.pre_user_event``
- ``self.PostUserEvent`` -> ``ui.post_user_event``

For compatibility, both interrupt setter spellings are supported:

- ``set_user_interrupt_tester(...)`` (preferred)
- ``set_user_interrupt_Tester(...)`` (legacy alias)

Migration note
--------------

Internal code should use ``set_user_interrupt_tester(...)`` only.
The legacy alias ``set_user_interrupt_Tester(...)`` remains available for
external scripts and existing notebooks to keep backward compatibility.

Kernel usage
------------

Measurement kernels use ``poll_key()`` as the explicit key-input path.
When a direct handler is not callable, ``resolve_poll_key(...)`` can resolve
``self.PollKey`` from caller locals as fallback.
