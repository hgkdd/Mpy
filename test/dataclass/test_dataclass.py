from dataclasses import dataclass
from typing import TypedDict
from bidict import bidict



@dataclass
class Instrumentation:
    device: bidict

