import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from collector import Collector
from start import prepare_live, main


class StartTests(unittest.TestCase):
    def test_sudo_is_fixed_and_noninteractive(self):
        calls = []
        def runner(args, **kwargs):
            calls.append(args)
            return SimpleNamespace(stdout='Active Simple USB Radio device is [1999].', returncode=0)
        c = Collector(device='1999', use_sudo=True, runner=runner)
        c.active()
        self.assertEqual(calls[0], ['/usr/bin/sudo','-n','--','/usr/sbin/asterisk','-rx','susb active'])

    def test_auto_fallback_and_actual_sample(self):
        samples = []
        class Fake:
            device_from = staticmethod(Collector.device_from)
            def __init__(self, device, use_sudo): self.device, self.use_sudo = device, use_sudo
            def command(self, command):
                if not self.use_sudo: raise ValueError('denied')
                return 'Active Simple USB Radio device is [1999].'
            def sample(self): samples.append(self.device)
        c = prepare_live(factory=Fake)
        self.assertEqual(c.device, '1999')
        self.assertTrue(c.use_sudo)
        self.assertEqual(samples, ['1999'])
        with self.assertRaisesRegex(ValueError, 'Expected device'):
            prepare_live(device='2000', factory=Fake)

    def test_invalid_sample_does_not_retry_as_privileged(self):
        modes = []
        class Fake:
            device_from = staticmethod(Collector.device_from)
            def __init__(self, device, use_sudo): modes.append(use_sudo)
            def command(self, command): return 'Active Simple USB Radio device is [1999].'
            def sample(self): raise ValueError('No USB statistics')
        with self.assertRaisesRegex(ValueError, 'No USB'):
            prepare_live(factory=Fake)
        self.assertEqual(modes, [False, False])

    def test_root_refused(self):
        with patch('start.os.geteuid', return_value=0, create=True):
            self.assertEqual(main(['--check']), 1)

    def test_old_python_explained(self):
        with patch('start.sys.version_info', (3, 10)):
            self.assertEqual(main(['--check']), 1)
