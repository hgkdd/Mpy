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