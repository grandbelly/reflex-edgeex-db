"""
event_with_error — DRY wrapper for the generic 'except Exception as e' pattern
that appears 101 times across 24 state files (per audit_code-quality_2026-05-21.md).

PoC scope: Cluster A handlers (61% of the 101 sites) — those that simply log +
set self.error_message on the canonical BaseState field. Cluster B (also resets
a loading flag) will need a parameterizable variant; out of scope for this PoC.

Reflex 0.8 compatibility verified via reflex/event.py:2413-2455 — @rx.event on a
class-body method only stamps BACKGROUND_TASK_MARKER and returns the function
unchanged. Our decorator wraps the function; @rx.event then stamps the wrapper.
Stacking order (matters):
    @rx.event(background=True)   # outer
    @event_with_error            # inner
    async def my_handler(self): ...
"""
import functools
import inspect
from typing import Any, Callable

from reflex.utils import console
from reflex.event import BACKGROUND_TASK_MARKER

_FAIL_LOUD = False  # flip True in dev to re-raise after logging


def event_with_error(fn: Callable) -> Callable:
    """Catch-all error decorator for Reflex event handlers (Cluster A).

    Wraps both plain async coroutines and async generators (yield events).
    On exception: logs via reflex.utils.console.error and sets
    self.error_message to str(exc). Also resets self.loading if present.

    Apply BELOW @rx.event / @rx.event(background=True). See module docstring
    for stacking order.
    """
    is_gen = inspect.isasyncgenfunction(fn)

    if is_gen:
        @functools.wraps(fn)
        async def _gen_wrapper(self: Any, *args: Any, **kwargs: Any):
            try:
                async for value in fn(self, *args, **kwargs):
                    yield value
            except Exception as exc:
                console.error(f"[{type(self).__name__}.{fn.__name__}] {exc}")
                async with self:
                    if hasattr(self, "error_message"):
                        self.error_message = str(exc)
                    if hasattr(self, "loading"):
                        self.loading = False
                if _FAIL_LOUD:
                    raise
        wrapper = _gen_wrapper
    else:
        @functools.wraps(fn)
        async def _coro_wrapper(self: Any, *args: Any, **kwargs: Any):
            try:
                return await fn(self, *args, **kwargs)
            except Exception as exc:
                console.error(f"[{type(self).__name__}.{fn.__name__}] {exc}")
                async with self:
                    if hasattr(self, "error_message"):
                        self.error_message = str(exc)
                    if hasattr(self, "loading"):
                        self.loading = False
                if _FAIL_LOUD:
                    raise
        wrapper = _coro_wrapper

    # Belt-and-suspenders: preserve BACKGROUND_TASK_MARKER even if stacking
    # order is accidentally reversed (rx.event inner, event_with_error outer).
    if getattr(fn, BACKGROUND_TASK_MARKER, False):
        setattr(wrapper, BACKGROUND_TASK_MARKER, True)

    return wrapper
