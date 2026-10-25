"""Self-terminate background polling loops when the client tab has disconnected.

Reflex keeps a polling loop alive on a feature flag (`is_streaming` / `_polling_active`),
not on the socket. When a tab closes without firing `on_unload`, the loop runs forever —
re-querying the DB every interval and hitting reflex's
"Attempting to send delta to disconnected client" warning (measured: ~13.6k times / 12 days
on a single idle tab). Polling loops call `client_connected(self)` and `break` when it returns False.

ponytail: reaches into reflex internals (`App.event_namespace.token_to_sid`); pinned to reflex 0.8.16.
Fail-safe by design — returns True on *any* uncertainty (no token yet, no namespace, exception)
so a detection bug can never kill a live loop. It returns False only when a token is positively
absent from the live-socket map (i.e. the client really did disconnect).
"""
from __future__ import annotations

_app = None  # cached App instance; get_app() inserts cwd into sys.path each call, so cache it


def _get_event_namespace():
    global _app
    if _app is None:
        from reflex.utils import prerequisites
        from reflex import constants
        _app = getattr(prerequisites.get_app(), constants.CompileVars.APP)
    return _app.event_namespace


def token_connected(token: str, token_to_sid) -> bool:
    """Pure decision: is this client token still mapped to a live socket?

    No token → not hydrated yet → treat as connected (never kill prematurely).
    """
    if not token:
        return True
    return token_to_sid.get(token) is not None


def client_connected(state) -> bool:
    """True if the tab driving this background loop is still connected. Fail-safe True."""
    try:
        ns = _get_event_namespace()
        if ns is None:
            return True
        return token_connected(state.router.session.client_token, ns.token_to_sid)
    except Exception:
        return True


if __name__ == "__main__":
    # Pure-logic self-check — no reflex server, runnable on host.
    assert token_connected("", {}) is True                      # not hydrated → assume live
    assert token_connected("", {"x": "sid"}) is True
    assert token_connected("t1", {"t1": "sid-abc"}) is True      # mapped → connected
    assert token_connected("t1", {}) is False                    # gone → disconnected
    assert token_connected("t1", {"t2": "sid"}) is False         # only other tabs live
    print("client_connected logic OK")
