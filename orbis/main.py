
from cement import App, TestApp, init_defaults
from cement.core.exc import CaughtSignal

from orbis.core.interfaces import HandlersInterface
from orbis.handlers.command import CommandHandler
from orbis.handlers.plugin import PluginLoader
from .core.exc import OrbisError
from .controllers.base import Base

# configuration defaults
CONFIG = init_defaults('orbis')
CONFIG['orbis']['foo'] = 'bar'


class Orbis(App):
    """orbis primary application."""

    class Meta:
        label = 'orbis'

        # configuration defaults
        config_defaults = CONFIG

        # call sys.exit() on close
        exit_on_close = True

        # load additional framework extensions
        extensions = [
            'orbis.ext.server',
            'yaml',
            'colorlog',
            'jinja2',
        ]

        # configuration handler
        config_handler = 'yaml'

        # configuration file suffix
        config_file_suffix = '.yml'

        # set the log handler
        log_handler = 'colorlog'

        # set the output handler
        output_handler = 'jinja2'

        plugin_handler = 'plugin_loader'

        interfaces = [
            HandlersInterface
        ]

        # register handlers
        handlers = [
            Base, CommandHandler, PluginLoader,
        ]

    def get_config(self, key: str):
        if self.config.has_section(self.Meta.label):
            if key in self.config.keys(self.Meta.label):
                return self.config.get(self.Meta.label, key)

        return None


class OrbisTest(TestApp,Orbis):
    """A sub-class of Orbis that is better suited for testing."""

    class Meta:
        label = 'orbis'


def main():
    with Orbis() as app:
        try:
            app.run()

        except AssertionError as e:
            print('AssertionError > %s' % e.args[0])
            app.exit_code = 1

            if app.debug is True:
                import traceback
                traceback.print_exc()

        except OrbisError as e:
            print('OrbisError > %s' % e.args[0])
            app.exit_code = 1

            if app.debug is True:
                import traceback
                traceback.print_exc()

        except CaughtSignal as e:
            # Default Cement signals are SIGINT and SIGTERM, exit 0 (non-error)
            print('\n%s' % e)
            app.exit_code = 0


if __name__ == '__main__':
    main()