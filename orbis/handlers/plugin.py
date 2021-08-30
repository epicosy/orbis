from cement.core.exc import FrameworkError
from cement.ext.ext_plugin import CementPluginHandler

from orbis.core.exc import OrbisError


class PluginLoader(CementPluginHandler):
    class Meta:
        label = 'plugin_loader'

    def __init__(self):
        super().__init__()
        self._benchmark = None

    @property
    def benchmark(self):
        return self._benchmark

    @benchmark.setter
    def benchmark(self, name: str):
        self._benchmark = name

    def _setup(self, app_obj):
        super()._setup(app_obj)

        for section in self.app.config.get_sections():
            try:
                _, kind, name = section.split('.')

                if kind != 'benchmark':
                    continue

                try:
                    self.load_plugin(f"{kind}/{name}")
                except FrameworkError as fe:
                    raise OrbisError(str(fe))

                loaded = f"{kind}/{name}" in self._loaded_plugins
                enabled = 'enabled' in self.app.config.keys(section)

                if loaded and enabled:
                    self.benchmark = name
                    break
            except ValueError:
                continue
