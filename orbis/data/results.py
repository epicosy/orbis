import os
from typing import AnyStr, Dict
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class CommandData:
    args: str
    env: Dict[str, str] = field(default_factory=lambda: os.environ.copy())
    cwd: str = None
    pid: int = None
    exit_status: int = 0
    duration: float = 0
    start: datetime = None
    end: datetime = None
    output: AnyStr = None
    error: AnyStr = None
    timeout: int = None
    returns: dict = field(default_factory=lambda: {})

    def __getitem__(self, key: str):
        return self.returns[key]

    def __setitem__(self, key: str, value):
        self.returns[key] = value

    def __iter__(self):
        return iter(self.returns)

    def to_dict(self):
        return {'args': self.args, 'exit_status': self.exit_status, 'duration': self.duration, 'start': str(self.start),
                'end': str(self.end), 'error': self.error, 'timeout': self.timeout, 'returns': self.returns}

    def set_end(self, end_time: datetime = None):
        if not None:
            self.end = datetime.now()
        else:
            self.end = end_time

    def set_start(self, start_time: datetime = None):
        if not None:
            self.end = datetime.now()
        else:
            self.end = start_time

    def set_duration(self):
        if self.end and self.start:
            self.duration = (self.end-self.start).total_seconds()

    @staticmethod
    def get_blank():
        cmd_data = CommandData(args="")
        cmd_data.set_start()

        return cmd_data

    def failed(self, err_msg: str):
        self.error = err_msg

        if not self.exit_status:
            self.exit_status = 1

        if not self.end:
            self.end = datetime.now()
            self.set_duration()


@dataclass
class Store:
    assets: dict = field(default_factory=lambda: {})

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
