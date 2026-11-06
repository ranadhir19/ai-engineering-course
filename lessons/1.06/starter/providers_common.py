"""Shared helper: run the three mock provider servers as subprocesses.

Every driver in this lesson (compare, route, the harness) needs the
same three servers. This module starts them, waits until each answers
``/__count``, and stops them on exit. Standard library only.
"""

import json
import os
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SERVER = os.path.join(HERE, "mock_provider_server.py")

PORTS = {"sprout": 8771, "atlas": 8772, "oracle": 8773}


def _get_json(url, timeout=2.0):
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def request_count(provider_name):
    return _get_json(
        "http://127.0.0.1:" + str(PORTS[provider_name]) + "/__count"
    )["requests"]


class ProviderServers:
    """Context manager: the named provider servers, running locally."""

    def __init__(self, names=("sprout", "atlas", "oracle")):
        self.names = tuple(names)
        self.procs = []

    def __enter__(self):
        for name in self.names:
            proc = subprocess.Popen(
                [sys.executable, SERVER, "--profile", name],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self.procs.append(proc)
        deadline = time.time() + 15.0
        for name in self.names:
            url = "http://127.0.0.1:" + str(PORTS[name]) + "/__count"
            while True:
                try:
                    _get_json(url, timeout=1.0)
                    break
                except Exception:
                    if time.time() > deadline:
                        self.__exit__(None, None, None)
                        raise RuntimeError("provider server did not start: " + name)
                    time.sleep(0.1)
        return self

    def __exit__(self, *exc):
        for proc in self.procs:
            proc.terminate()
        for proc in self.procs:
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        self.procs = []
        return False
