"""UI adapter abstractions for measurement environments.

The adapter keeps UI interaction points (ask/log/interrupt/pre/post events)
behind a small interface so that TUI and future GUI integrations can share the
same measurement logic.
"""

from __future__ import annotations

from typing import Any, Callable


def resolve_poll_key(handler: Any, caller_locals: dict[str, Any] | None = None) -> Callable[[], int | None] | None:
    """Resolve a poll-key callable from explicit handler or caller context."""
    if callable(handler):
        return handler
    if isinstance(caller_locals, dict):
        caller_self = caller_locals.get("self")
        candidate = getattr(caller_self, "PollKey", None)
        if callable(candidate):
            return candidate
    return None


class MeasurementUIAdapter:
    """Abstract UI adapter contract for measurement flows."""

    def ask(
        self,
        msg: str = "Are you ready?",
        buttons: list[str] | None = None,
        level: str = "",
        data: dict[Any, Any] | None = None,
    ) -> int:
        """Display question and return selected button index."""
        raise NotImplementedError

    def emit_log(self, block, *args) -> None:
        """Emit one structured log block."""
        raise NotImplementedError

    def poll_key(self) -> int | None:
        """Poll one pending key event, if any."""
        raise NotImplementedError

    def check_interrupt(self) -> int | None:
        """Check for interrupt request using key polling."""
        return self.poll_key()

    def pre_user_event(self) -> None:
        """Run hook before user-facing event."""
        raise NotImplementedError

    def post_user_event(self) -> None:
        """Run hook after user-facing event."""
        raise NotImplementedError

    def run_interactive(self, obj: Any, banner: str) -> None:
        """Start interactive shell for an object."""
        raise NotImplementedError


class TUIAdapter(MeasurementUIAdapter):
    """Default terminal-oriented adapter using callables from `Measure`."""

    def __init__(
        self,
        messenger: Callable[[str, list[str] | None, str, dict[Any, Any] | None], int],
        logger: list[Callable[..., Any]] | None,
        interrupt_tester: Callable[[], int | None],
        pre_user_event: Callable[[], None],
        post_user_event: Callable[[], None],
        interactive_runner: Callable[[Any, str], None],
    ) -> None:
        self._messenger = messenger
        self._logger = list(logger) if logger is not None else []
        self._interrupt_tester = interrupt_tester
        self._pre_user_event = pre_user_event
        self._post_user_event = post_user_event
        self._interactive_runner = interactive_runner

    def set_messenger(self, messenger: Callable[[str, list[str] | None, str, dict[Any, Any] | None], int]) -> None:
        """Replace messenger callback."""
        self._messenger = messenger

    def set_logger(self, logger: list[Callable[..., Any]] | None) -> None:
        """Replace logger callback list."""
        self._logger = list(logger) if logger is not None else []

    def set_interrupt_tester(self, tester: Callable[[], int | None]) -> None:
        """Replace interrupt polling callback."""
        self._interrupt_tester = tester

    def set_pre_user_event(self, cb: Callable[[], None]) -> None:
        """Replace pre-user-event callback."""
        self._pre_user_event = cb

    def set_post_user_event(self, cb: Callable[[], None]) -> None:
        """Replace post-user-event callback."""
        self._post_user_event = cb

    def set_interactive_runner(self, runner: Callable[[Any, str], None]) -> None:
        """Replace interactive-runner callback."""
        self._interactive_runner = runner

    def ask(
        self,
        msg: str = "Are you ready?",
        buttons: list[str] | None = None,
        level: str = "",
        data: dict[Any, Any] | None = None,
    ) -> int:
        """Forward user prompt request to configured messenger."""
        return self._messenger(msg, buttons, level, data)

    def emit_log(self, block, *args) -> None:
        """Forward one log block to all configured loggers."""
        for log in self._logger:
            log(block, *args)

    def poll_key(self) -> int | None:
        """Poll and return key code from interrupt tester."""
        return self._interrupt_tester()

    def pre_user_event(self) -> None:
        """Call pre-user-event hook."""
        self._pre_user_event()

    def post_user_event(self) -> None:
        """Call post-user-event hook."""
        self._post_user_event()

    def run_interactive(self, obj: Any, banner: str) -> None:
        """Call interactive runner with object and banner."""
        self._interactive_runner(obj, banner)
