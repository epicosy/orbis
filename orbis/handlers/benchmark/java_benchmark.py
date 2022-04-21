from abc import abstractmethod, ABC

from orbis.data.misc import Context
from orbis.data.results import CommandData
from orbis.data.schema import Oracle
from orbis.handlers.benchmark.benchmark import BenchmarkHandler
from orbis.handlers.operations.java.build import JavaBuildHandler
from orbis.handlers.operations.java.test import JavaTestHandler


class JavaBenchmark(BenchmarkHandler, ABC):
    class Meta:
        label = "java_benchmark"

    @property
    def build_handler(self) -> JavaBuildHandler:
        return self.app.handler.get('handlers', 'java_build', setup=True)

    @property
    def test_handler(self) -> JavaTestHandler:
        return self.app.handler.get('handlers', 'java_test', setup=True)

    @abstractmethod
    def build(self, context: Context, handler: JavaBuildHandler, **kwargs) -> CommandData:
        pass

    @abstractmethod
    def test(self, context: Context, tests: Oracle, timeout: int,
             **kwargs) -> CommandData:
        pass

    @abstractmethod
    def classpath(self, context: Context, **kwargs) -> CommandData:
        pass

    @abstractmethod
    def test_batch(self, context: Context, batch_type: str, timeout: int, **kwargs) -> CommandData:
        pass
