from pathlib import Path
from typing import AnyStr, List
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class CommandData:
    # env: dict = None
    args: str
    pid: int = None
    return_code: int = 0
    duration: float = 0
    start: datetime = None
    end: datetime = None
    output: AnyStr = None
    error: AnyStr = None
    timeout: bool = False

    def to_dict(self):
        return {'args': self.args, 'return_code': self.return_code, 'duration': self.duration, 'start': str(self.start),
                'end': str(self.end), 'error': self.error, 'timeout': self.timeout}


@dataclass
class Store:
    assets = {}

    def __getitem__(self, key: str):
        return self.assets[key]

    def __setitem__(self, key: str, value):
        self.assets[key] = value

    def __iter__(self):
        return iter(self.assets)

    def keys(self):
        return self.assets.keys()

    def items(self):
        return self.assets.items()

    def values(self):
        return self.assets.values()


@dataclass
class Vulnerability:
    id: str
    pid: str
    cwe: str
    program: str
    exploit: str
    cve: str = '-'


@dataclass
class Program(Store):
    working_dir: Path
    name: str
    vuln: Vulnerability
    root: Path
    source: Path = None
    lib: Path = None
    include: Path = None

    def has_source(self):
        return self.source and self.source.exists()

    def has_lib(self):
        return self.lib and self.lib.exists()

    def has_include(self):
        return self.include and self.include.exists()
