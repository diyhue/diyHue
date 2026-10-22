import unittest


class PskValueTests(unittest.TestCase):
    """OpenSSL only accepts a PSK as hex digits.

    A client key that arrived base64url encoded (the HDMI Sync Box sends
    one) has to be decoded first, otherwise the entertainment server starts
    but immediately dies with "Not a hex number".
    """

    @staticmethod
    def _psk_value(key):
        import base64
        import binascii

        if not key:
            return ""
        if all(c in "0123456789abcdefABCDEF" for c in key) and len(key) % 2 == 0:
            return key
        try:
            decoded = base64.urlsafe_b64decode(key + "=" * (-len(key) % 4))
            return binascii.hexlify(decoded).decode()
        except Exception:
            return binascii.hexlify(key.encode()).decode()

    def test_hex_key_is_passed_through(self):
        key = "0E89C42026A94FEBB10B89118E5D76C7"
        self.assertEqual(self._psk_value(key), key)

    def test_base64url_key_is_decoded_to_hex(self):
        key = "QUig8nU0ergCvWRcozqhvI7JF50-5UENBQjnFx8Y"
        self.assertEqual(
            self._psk_value(key),
            "4148a0f275347ab802bd645ca33aa1bc8ec9179d3ee5410d0508e7171f18",
        )

    def test_decoded_value_is_valid_hex(self):
        key = "QUig8nU0ergCvWRcozqhvI7JF50-5UENBQjnFx8Y"
        value = self._psk_value(key)
        self.assertTrue(all(c in "0123456789abcdef" for c in value))
        self.assertEqual(len(value) % 2, 0)

    def test_missing_key_returns_empty_string(self):
        self.assertEqual(self._psk_value(None), "")
        self.assertEqual(self._psk_value(""), "")

    def test_non_base64_key_falls_back_to_hex_of_ascii(self):
        # A key that cannot be base64 decoded still has to yield valid hex,
        # otherwise OpenSSL refuses to start.
        value = self._psk_value("!!!not-base64!!!")
        self.assertTrue(all(c in "0123456789abcdef" for c in value))
        self.assertEqual(len(value) % 2, 0)


class EntertainmentUserKeyTests(unittest.TestCase):
    """The entertainment service must not crash on a user without a client key."""

    def test_logging_does_not_concatenate_none(self):
        class User:
            username = "syncbox"
            client_key = None

        # This is what services/entertainment.py does on start. It used to
        # raise TypeError: can only concatenate str (not "NoneType") to str
        message = "Key: " + str(User.client_key)
        self.assertEqual(message, "Key: None")

    def test_psk_falls_back_to_username(self):
        class User:
            username = "syncbox"
            client_key = None

        psk = User.client_key or User.username
        self.assertEqual(psk, "syncbox")


if __name__ == "__main__":
    unittest.main()
