"""State and local control for the bridge's time-limited link button."""
from datetime import datetime, timezone
import signal


LINK_BUTTON_WINDOW_SECONDS = 30


def _timestamp(now=None):
    if now is None:
        now = datetime.now(timezone.utc)
    return now.timestamp()


def pressLinkButton(config, now=None):
    """Open the physical-link equivalent for one registration window.

    This only changes in-memory state.  A successful application registration
    still goes through the normal API endpoint and is the operation that is
    persisted by the configuration manager.
    """
    config.setdefault("linkbutton", {})["lastlinkbuttonpushed"] = _timestamp(now)


def linkButtonIsOpen(config, now=None):
    """Return whether a normal API registration is currently permitted."""
    try:
        pressed_at = float(config.get("linkbutton", {}).get("lastlinkbuttonpushed", 0))
    except (TypeError, ValueError):
        return False
    return 0 <= _timestamp(now) - pressed_at <= LINK_BUTTON_WINDOW_SECONDS


def installLinkButtonSignal(config, logger):
    """Install the host-local virtual button handler.

    ``SIGUSR1`` can only be sent by a process with container/process control;
    it deliberately is not exposed through the Hue API.  It therefore remains
    a physical-presence equivalent for the Docker emulator rather than a
    network-accessible pairing bypass.
    """
    def on_signal(_signum, _frame):
        pressLinkButton(config)
        logger.info("Virtual link button pressed; registration open for 30 seconds")

    signal.signal(signal.SIGUSR1, on_signal)
    return on_signal
