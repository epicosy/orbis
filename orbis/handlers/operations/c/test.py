import os
import signal
import sys
import psutil
import fileinput

from pathlib import Path
from typing import List, Tuple, Callable

from orbis.data.misc import Context
from orbis.ext.database import TestOutcome
from orbis.utils.misc import collect_files

from orbis.data.results import CommandData
from orbis.handlers.command import CommandHandler
from orbis.data.schema import Test


class TestHandler(CommandHandler):
    class Meta:
        label = 'test'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.failed = False

    def run(self, context: Context, test: Test, timeout: int, cwd: str = None, script: str = None, env: dict = None,
            args: str = None, process_outcome: Callable = None, kill: bool = False) -> Tuple[CommandData, TestOutcome]:
        """
            Runs the test and saves the outcome into the database.

            :param context: the instance with the associated directory and the program
            :param test: the test to be run
            :param timeout: timeout to stop the test execution
            :param cwd: working directory for running the test
            :param script: script file or command to invoke the test (overwrites the script associated to the test)
            :param args: args to associate to the test (overwrites the args associated to the test)
            :param env: dictionary with the environment variables
            :param kill: kills the associated processes to the executed command
            :param process_outcome: Function that receives 3 arguments (cmd_data, test, and the test_outcome)
        """

        if script and (not test.script or test.script == ""):
            test.script = script

        if args and not test.args:
            test.args = args
        
        cmd_data = CommandData(args=f"{test.script} {test.args}", cwd=cwd, timeout=timeout, env=env)
        cmd_data = super().__call__(cmd_data=cmd_data, raise_err=False, exit_err=False,
                                    msg=f"Testing {test.id} on {test.file}\n")
        pids = [str(cmd_data.pid)]
        outcome = TestOutcome(instance_id=context.instance.id, co_id=context.instance.pointer, name=test.id,
                              duration=round(cmd_data.duration, 3), exit_status=cmd_data.exit_status,
                              error=cmd_data.error, passed=True if not cmd_data.error else False)

        if outcome.duration > timeout and outcome.error and outcome.exit_status != 0:
            outcome.error = "Test timed out"

        if process_outcome:
            pids = process_outcome(cmd_data, test, outcome)

        if kill:
            if cmd_data.error and outcome.sig not in [signal.SIGSEGV, signal.SIGILL, signal.SIGBUS]:
                # Try to kill erroneous process with no crash
                self.kill_process(name=context.project.name, target_pids=pids)

        t_id = self.app.db.add(outcome)
        self.app.log.debug(f"Inserted 'test outcome' with id {t_id} for instance {context.instance.id}.")

        return cmd_data, outcome

    def kill_process(self, name: str, target_pids: List[str] = None):
        """
        Gets a list of all the PIDs of the running process whose name contains the given string process_name and
        kills the process. If target_pids list is supplied, it checks the pids for the process with the list
        """
        # based on https://thispointer.com/python-check-if-a-process-is-running-by-name-and-find-its-process-id-pid/
        # Iterate over the all the running process
        self.app.log.warning(f"Killing {name} process.")

        killed_pids = []

        for proc in psutil.process_iter():
            try:
                proc_info = proc.as_dict(attrs=['pid', 'name', 'create_time'])
                # Check if process name contains the given name string.
                if name in proc_info['name']:
                    if psutil.pid_exists(proc_info['pid']):
                        if target_pids and proc_info['pid'] not in target_pids:
                            continue
                        os.system(f"kill -9 {proc_info['pid']}")
                        killed_pids.append(proc_info['pid'])
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as pe:
                sys.stderr.write(str(pe))

        if killed_pids:
            self.app.log.info(f"Killed processes {killed_pids}.")

        return killed_pids

    @staticmethod
    def write_result(test_outcome: TestOutcome, out_file: Path, prefix: Path = None, write_fail: bool = False):
        if prefix:
            out_file = prefix / out_file

        if not write_fail and not test_outcome.passed:
            return

        with out_file.open(mode="a") as of:
            of.write(f"{test_outcome.name} {test_outcome.passed}\n")

    # Path(self.app.pargs.cov_dir) if self.app.pargs.cov_dir else working.cmake
    def coverage(self, out_dir: Path, cov_dir: Path, rename_suffix: str):
        # copies coverage file generated to coverage dir with respective name

        for file in collect_files(cov_dir, self.app.pargs.cov_suffix):
            in_file = cov_dir / file
            out_path = out_dir / file.parent
            out_file = out_path / Path(file.name)

            if not out_path.exists():
                out_path.mkdir(parents=True, exist_ok=True)

            if in_file.exists():
                concat_file = Path(file.stem + rename_suffix) if rename_suffix else Path(out_file)
                concat_file = out_path / concat_file

                with concat_file.open(mode="a") as fout, fileinput.input(in_file) as fin:
                    for line in fin:
                        fout.write(line)
                # delete the file generated
                in_file.unlink()
