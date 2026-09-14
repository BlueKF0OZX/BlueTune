import json
import sys
import threading
import unittest
import urllib.request
import urllib.error
import subprocess
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from analysis import parse_stats, assess
from collector import Collector
from app import make_server

GOOD = 'RxAudioStats: Pk -8.0  Avg Pwr -21  Min -60  Max -15  dBFS  ClipCnt 0'
CLIP = 'RxAudioStats: Pk -0.2  Avg Pwr -8  Min -30  Max -3  dBFS  ClipCnt 18'


class AnalysisTests(unittest.TestCase):
    def test_confirmed_headroom(self):
        self.assertEqual(assess(parse_stats(GOOD), True)['status'], 'good')

    def test_speech_required(self):
        self.assertEqual(assess(parse_stats(CLIP))['status'], 'unknown')

    def test_clipping_not_summed(self):
        r = assess(parse_stats(CLIP + '\n' + CLIP), True)
        self.assertEqual(r['max_clip_count'], 18)
        self.assertIn('Clipping', r['title'])

    def test_thresholds(self):
        for peak, avg, expected in [(-3, -12, 'good'), (-2.9, -12, 'warning'), (-3, -11, 'warning')]:
            row = f'RxAudioStats: Pk {peak} Avg Pwr {avg} Min -50 Max -8 dBFS ClipCnt 0'
            self.assertEqual(assess(parse_stats(row), True)['status'], expected)

    def test_silence_never_passes(self):
        quiet = 'RxAudioStats: Pk -96 Avg Pwr -96 Min -96 Max -96 dBFS ClipCnt 0'
        self.assertEqual(assess(parse_stats(quiet), True)['status'], 'unknown')

    def test_reject_bad_data(self):
        for value in [None, '', 'No USB device', GOOD.replace('RxAudio', 'TxAudio'),
                      GOOD.replace('-8.0', 'nan'), GOOD.replace('-8.0', '1.0'),
                      GOOD.replace('Min -60', 'Min -10'), GOOD.replace('-8.0', '-90'),
                      GOOD.replace('ClipCnt 0', 'ClipCnt -1'), GOOD+'\nRxAudioStats: truncated',
                      '\n'.join([GOOD]*121), 'x'*65537]:
            with self.subTest(value=str(value)[:60]), self.assertRaises(ValueError):
                parse_stats(value)

    def test_terminal_wrapper_allowed(self):
        self.assertEqual(len(parse_stats('header\n'+GOOD+'\nAsterisk ending (0).')), 1)


class CollectorTests(unittest.TestCase):
    def runner(self, responses):
        self.calls = []
        def run(args, **kwargs):
            self.calls.append(args)
            return SimpleNamespace(returncode=0, stdout=responses.pop(0))
        return run

    def test_only_expected_device(self):
        active = 'Active Simple USB Radio device is [1999].'
        c = Collector(device='1999', runner=self.runner([active, GOOD, active]))
        self.assertEqual(c.sample()['peak'], -8)
        self.assertEqual([x[-1] for x in self.calls], ['susb active', 'susb tune menu-support Y', 'susb active'])

    def test_device_change_discards_result(self):
        active = 'Active Simple USB Radio device is [1999].'
        c = Collector(device='1999', runner=self.runner([active, GOOD, active.replace('1999','2000')]))
        with self.assertRaises(ValueError): c.sample()

    def test_missing_device_never_runs_stats(self):
        c = Collector(device='1999', runner=self.runner(['No such command']))
        with self.assertRaises(ValueError): c.sample()
        self.assertEqual(len(self.calls), 1)

    def test_injection_and_mutations_rejected(self):
        with self.assertRaises(ValueError): Collector(device='1999; reboot')
        c = Collector(device='1999')
        for command in ['susb key','susb active 2000','susb tune rx 999','susb tune menu-support y']:
            with self.assertRaises(ValueError): c.command(command)

    def test_timeout(self):
        def run(*args, **kwargs): raise subprocess.TimeoutExpired('asterisk',3)
        with self.assertRaises(ValueError): Collector(device='1999',runner=run).sample()


class HttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = make_server(0)
        cls.thread = threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()
        cls.url=f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join()

    def request(self,path,body=None,headers=None):
        data=None if body is None else json.dumps(body).encode()
        r=urllib.request.Request(self.url+path,data=data,headers=headers or {})
        return urllib.request.urlopen(r,timeout=3)

    def test_status_and_analyze(self):
        with self.request('/api/status') as response: status=json.load(response)
        self.assertEqual(status['mode'],'demo')
        with self.request('/api/analyze',dict(text=GOOD,speech_confirmed=True),{'X-BlueTune-Token':status['token']}) as response:
            self.assertEqual(json.load(response)['result']['status'],'good')

    def test_foreign_origin_and_missing_token(self):
        for headers in [{}, {'X-BlueTune-Token':self.server.token,'Origin':'https://foreign.invalid'},
                        {'X-BlueTune-Token':self.server.token,'Host':'foreign.invalid'}]:
            with self.assertRaises(urllib.error.HTTPError) as error:
                self.request('/api/analyze',dict(text=GOOD),headers)
            self.assertEqual(error.exception.code,403)

    def test_no_live_in_demo(self):
        with self.assertRaises(urllib.error.HTTPError) as error:
            self.request('/api/sample',{}, {'X-BlueTune-Token':self.server.token})
        self.assertEqual(error.exception.code,409)

    def test_tunnel_port_and_origin(self):
        headers = {'Host':'localhost:8093','Origin':'http://localhost:8093','X-BlueTune-Token':self.server.token}
        with self.request('/api/analyze',dict(text=GOOD),headers) as response:
            self.assertEqual(response.status,200)
        headers['Origin']='http://localhost:8094'
        with self.assertRaises(urllib.error.HTTPError) as error:
            self.request('/api/analyze',dict(text=GOOD),headers)
        self.assertEqual(error.exception.code,403)

    def test_invalid_payload(self):
        for body in [[],dict(text=GOOD,speech_confirmed='true'),dict(text='RxAudioStats: incomplete')]:
            if isinstance(body,dict) and body.get('speech_confirmed'):
                with self.request('/api/analyze',body,{'X-BlueTune-Token':self.server.token}) as r:
                    self.assertEqual(json.load(r)['result']['status'],'unknown')
            else:
                with self.assertRaises(urllib.error.HTTPError) as error:
                    self.request('/api/analyze',body,{'X-BlueTune-Token':self.server.token})
                self.assertEqual(error.exception.code,400)

    def test_path_traversal(self):
        with self.assertRaises(urllib.error.HTTPError) as error: self.request('/../app.py')
        self.assertEqual(error.exception.code,404)


if __name__ == '__main__': unittest.main()
