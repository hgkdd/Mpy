# -*- coding: utf-8 -*-
"""This is :mod:`mpylab.tools.space_generators``.

   Provides Generator Versions of logspace and linspace

   :author: Hans Georg Krauthäuser (main author)

   :license: GPL-3 or higher
"""


class LogSpace:
    def __init__(self, start=80e6, stop=1e9, step=1.01, endpoint=True):
        self.start = start
        self.stop = stop
        self.step = step
        self.endpoint = endpoint

    def __iter__(self):
        f = self.start
        while f <= self.stop:
            yield f
            f *= self.step
        if self.endpoint and f > self.stop:
            yield self.stop


class LinSpace:
    def __init__(self, start=80e6, stop=1e9, step=1e6, endpoint=True):
        self.start = start
        self.stop = stop
        self.step = step
        self.endpoint = endpoint

    def __iter__(self):
        f = self.start
        while f <= self.stop:
            yield f
            f += self.step
        if self.endpoint and f > self.stop:
            yield self.stop

if __name__ == "__main__":
    print("=== LinSpace Test ===")
    lin = LinSpace(start=0, stop=10, step=3)

    for i, f in enumerate(lin):
        print(f"{i}: {f}")

    print("\n=== LogSpace Test ===")
    log = LogSpace(start=1, stop=100, step=2)

    for i, f in enumerate(log):
        print(f"{i}: {f}")

    print("\n=== HF Beispiel (Frequenz-Sweep) ===")
    freqs = LogSpace(start=80e6, stop=1e9, step=1.1)

    for i, f in enumerate(freqs):
        print(f"{i}: {f/1e6:.2f} MHz")
        if i > 10:   # nur erste paar Werte anzeigen
            print("...")
            break
