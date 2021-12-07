from pathlib import Path

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

    def check(self, name: str, path: str):
        """
            Checks if plugin can be loaded
        """
        return super()._load_plugin_from_dir(name, path)

    def _setup(self, app_obj):
        super()._setup(app_obj)

        for section in self.app.config.get_sections():
            try:
                kind, name = section.split('.')

                if kind != 'plugins':
                    continue

                try:
                    self.load_plugin(name)
                except FrameworkError as fe:
                    raise OrbisError(str(fe))

                loaded = name in self._loaded_plugins
                enabled = 'enabled' in self.app.config.keys(section) and self.app.config.get(section, 'enabled')

                if loaded and enabled:
                    self.benchmark = name
                    break
            except ValueError:
                continue

        if self.benchmark is None:
            self.app.log.warning("No plugin loaded.")
        #    exit(1)
