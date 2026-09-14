import socket
import sys
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import make_server
from collector import Collector


class FailureTests(unittest.TestCase):
    def test_missing_usb_is_not_a_pass(self):
        outputs = ['Active Simple USB Radio device is [1999].', 'USB device unassigned']
        def runner(*args, **kwargs): return SimpleNamespace(returncode=0, stdout=outputs.pop(0))
        with self.assertRaises(ValueError): Collector(device='1999',runner=runner).sample()

    def test_readings_do_not_queue(self):
        entered, release = threading.Event(), threading.Event()
        def runner(*args, **kwargs):
            entered.set(); release.wait(2)
            return SimpleNamespace(returncode=0,stdout='No such command')
        c=Collector(device='1999',runner=runner)
        def first():
            try: c.sample()
            except ValueError: pass
        thread=threading.Thread(target=first); thread.start()
        try:
            self.assertTrue(entered.wait(1))
            before=time.monotonic()
            with self.assertRaisesRegex(ValueError,'in progress'): c.sample()
            self.assertLess(time.monotonic()-before,0.5)
        finally:
            release.set(); thread.join()

    def test_slow_clients_are_bounded_and_recover(self):
        server=make_server(0)
        thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
        clients=[]
        try:
            for _ in range(8):
                c=socket.create_connection(server.server_address,timeout=2)
                c.sendall(b'GET / HTTP/1.0\r\n'); clients.append(c)
            # Wait on actual admission, not a fixed sleep.
            deadline=time.monotonic()+2
            while server.slots._value != 0 and time.monotonic()<deadline: time.sleep(.01)
            self.assertEqual(server.slots._value,0)
            with socket.create_connection(server.server_address,timeout=2) as c:
                self.assertIn(b'503',c.recv(200))
            for c in clients: c.close()
            clients=[]
            deadline=time.monotonic()+2
            while server.slots._value != 8 and time.monotonic()<deadline: time.sleep(.01)
            self.assertEqual(server.slots._value,8)
            with socket.create_connection(server.server_address,timeout=2) as c:
                c.sendall(f'GET /api/status HTTP/1.0\r\nHost: localhost:{server.server_port}\r\n\r\n'.encode())
                self.assertIn(b'200',c.recv(200))
        finally:
            for c in clients: c.close()
            server.shutdown(); server.server_close(); thread.join()
