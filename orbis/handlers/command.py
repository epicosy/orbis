import subprocess
import psutil as psutil

from threading import Timer
from cement import Handler

from orbis.core.exc import CommandError
from orbis.data.results import CommandData
from orbis.core.interfaces import HandlersInterface


class CommandHandler(HandlersInterface, Handler):
    class Meta:
        label = 'command'

    def __init__(self, **kw):
        super(CommandHandler, self).__init__(**kw)
        self.log = True

    def _exec(self, proc: subprocess.Popen, cmd_data: CommandData):
        out = []
        cmd = cmd_data.args.split()[0]
        for line in proc.stdout:
            decoded = line.decode()
            out.append(decoded)

            if self.app.pargs.verbose and self.log:
                self.app.log.info(decoded, cmd)

        cmd_data.output = ''.join(out)

        proc.wait(timeout=1)

        if proc.returncode and proc.returncode != 0:
            cmd_data.return_code = proc.returncode
            proc.kill()
            cmd_data.error = proc.stderr.read().decode()

            if cmd_data.error:
                self.app.log.error(cmd_data.error)

    def __call__(self, cmd_data: CommandData, msg: str = None, raise_err: bool = False, exit_err: bool = False,
                 **kwargs) -> CommandData:

        if msg and self.app.pargs.verbose:
            self.app.log.info(msg)

        self.app.log.debug(cmd_data.args, cmd_data.cwd)

        with subprocess.Popen(args=cmd_data.args, shell=True, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, env=cmd_data.env, cwd=cmd_data.cwd) as proc:
            cmd_data.pid = proc.pid
            cmd_data.set_start()

            if cmd_data.timeout:
                timer = Timer(cmd_data.timeout, _timer_out, args=[proc, cmd_data])
                timer.start()
                self._exec(proc, cmd_data)
                proc.stdout.close()
                timer.cancel()
            else:
                self._exec(proc, cmd_data)

            cmd_data.set_end()
            cmd_data.set_duration()

            if raise_err and cmd_data.error:
                raise CommandError(cmd_data.error)

            if exit_err and cmd_data.error:
                exit(proc.returncode)

            return cmd_data


# https://stackoverflow.com/a/54775443
def _timer_out(p: subprocess.Popen, cmd_data: CommandData):
    cmd_data.error = "Command timed out"
    cmd_data.timeout = True
    process = psutil.Process(p.pid)
    cmd_data.return_code = p.returncode if p.returncode else 3

    for proc in process.children(recursive=True):
        proc.kill()

    process.kill()
