import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    'mumble_wait', Path(__file__).resolve().parents[1] / 'scripts/wait-mumble-address.py')
mumble = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mumble)


class MumbleStartupTests(unittest.TestCase):
    def test_local_bind_probe_does_not_require_netlink(self):
        self.assertTrue(mumble.address_ready('127.0.0.1'))
        self.assertTrue(mumble.address_ready(''))

    def test_waits_for_delayed_lan_address(self):
        with patch.object(mumble, 'address_ready', side_effect=[False, False, True]), \
                patch.object(mumble.time, 'monotonic', return_value=0), \
                patch.object(mumble.time, 'sleep') as sleep:
            self.assertTrue(mumble.wait_for_address('192.0.2.1', timeout=90))
            self.assertEqual(sleep.call_count, 2)

    def test_timeout_exits_instead_of_starting_a_broken_daemon(self):
        with patch.object(mumble, 'address_ready', return_value=False), \
                patch.object(mumble.time, 'monotonic', side_effect=[0, 1, 90]), \
                patch.object(mumble.time, 'sleep') as sleep:
            self.assertFalse(mumble.wait_for_address('192.0.2.1', timeout=90))
            sleep.assert_called_once_with(1)

    def test_config_reads_only_host_and_rejects_invalid_addresses(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / 'mumble.ini'
            p.write_text('#host=bad\npassword=private\n host = "127.0.0.1"\n')
            self.assertEqual(mumble.configured_host(p), '127.0.0.1')
            p.write_text('host=invalid\n')
            with self.assertRaises(ValueError):
                mumble.configured_host(p)
            p.write_text('port=64738\n')
            self.assertEqual(mumble.configured_host(p), '')


if __name__ == '__main__':
    unittest.main()
