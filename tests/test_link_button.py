import pathlib
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch
import unittest


BRIDGE_EMULATOR = pathlib.Path(__file__).parents[1] / "BridgeEmulator"
sys.path.insert(0, str(BRIDGE_EMULATOR))

from functions.linkButton import (  # noqa: E402
    LINK_BUTTON_WINDOW_SECONDS,
    installLinkButtonSignal,
    linkButtonIsOpen,
    pressLinkButton,
)


class LinkButtonTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 9, 21, tzinfo=timezone.utc)
        self.config = {"linkbutton": {"lastlinkbuttonpushed": 0}}

    def test_press_opens_only_the_documented_window(self):
        self.assertFalse(linkButtonIsOpen(self.config, self.now))
        pressLinkButton(self.config, self.now)
        self.assertTrue(linkButtonIsOpen(self.config, self.now))
        self.assertTrue(
            linkButtonIsOpen(
                self.config,
                self.now + timedelta(seconds=LINK_BUTTON_WINDOW_SECONDS),
            )
        )
        self.assertFalse(
            linkButtonIsOpen(
                self.config,
                self.now + timedelta(seconds=LINK_BUTTON_WINDOW_SECONDS + 1),
            )
        )

    def test_invalid_persisted_timestamp_is_closed(self):
        self.config["linkbutton"]["lastlinkbuttonpushed"] = "invalid"
        self.assertFalse(linkButtonIsOpen(self.config, self.now))

    def test_future_persisted_timestamp_is_closed(self):
        self.config["linkbutton"]["lastlinkbuttonpushed"] = (
            self.now + timedelta(seconds=1)
        ).timestamp()
        self.assertFalse(linkButtonIsOpen(self.config, self.now))

    def test_signal_handler_opens_window_without_exposing_an_api_route(self):
        logger = Mock()
        with patch("functions.linkButton.signal.signal") as register:
            handler = installLinkButtonSignal(self.config, logger)
        register.assert_called_once()
        handler(None, None)
        self.assertTrue(linkButtonIsOpen(self.config))
        logger.info.assert_called_once()


if __name__ == "__main__":
    unittest.main()
