from abc import abstractmethod, ABC

from orbis.data.misc import Context
from orbis.data.results import CommandData
from orbis.data.schema import Oracle
from orbis.handlers.benchmark.benchmark import BenchmarkHandler
from orbis.handlers.operations.c.build import BuildHandler
from orbis.handlers.operations.c.make import MakeHandler
from orbis.handlers.operations.c.test import TestHandler


class CBenchmark(BenchmarkHandler, ABC):
    class Meta:
        label = "c_benchmark"

    @property
    def make_handler(self) -> MakeHandler:
        return self.app.handler.get('handlers', 'make', setup=True)

    @property
    def build_handler(self) -> BuildHandler:
        return self.app.handler.get('handlers', 'build', setup=True)

    @property
    def test_handler(self) -> TestHandler:
        return self.app.handler.get('handlers', 'test', setup=True)

    @abstractmethod
    def make(self, context: Context, **kwargs) -> CommandData:
        pass

    @abstractmethod
    def build(self, context: Context, **kwargs) -> CommandData:
        pass

    @abstractmethod
    def test(self, context: Context, tests: Oracle, povs: Oracle, timeout: int,
             **kwargs) -> CommandData:
        pass
