import platform
import re
import shutil

from os import listdir
from pathlib import Path
from typing import List, Dict, Any, AnyStr, Tuple

from orbis.core.exc import OrbisError
from orbis.data.misc import Context
from orbis.data.results import CommandData
from orbis.data.schema import Oracle, Test, Project
from orbis.ext.database import TestOutcome
from orbis.handlers.benchmark.c_benchmark import CBenchmark


def get_binaries(source_path: Path, binary: Path):
    # Collect the names of binaries to be tested
    cb_dirs = [el for el in listdir(str(source_path)) if el.startswith('cb_')]

    if len(cb_dirs) > 0:
        # There are multiple binaries in this challenge
        return ['{}_{}'.format(binary.name, i + 1) for i in range(len(cb_dirs))]
    else:
        # Check the challenge binary
        if not binary.exists():
            raise OrbisError(f"Challenge binary {binary.name} not found")

        return [binary.name]


def match_pattern(output: str, pattern: str):
    match = re.search(pattern, output)

    if match:
        return match.group(1)

    return None


def get_pids_sig(output: str):
    """
        Returns the pids and signal in the output from the execution of the test
        :param output: output string from executing the test
    """
    match = re.search("# \[DEBUG\] pid: (\d{1,7}), sig: (\d{1,2})", output)
    match2 = re.search("# Process generated signal \(pid: (\d{1,7}), signal: (\d{1,2})\)", output)
    pids = []
    sig = 0

    if match:
        pids.append(match.group(1))
        sig = int(match.group(2))
    elif match2:
        pids.append(match2.group(1))
        sig = int(match2.group(2))
    else:
        match = re.search("# pid (\d{4,7})", output)
        if match:
            pids.append(match.group(1))

    return pids, sig


def parse_output_to_outcome(cmd_data: CommandData, test: Test, test_outcome: TestOutcome) -> List[str]:
    """
        Parses out the number of passed and failed tests from cb-test output
        :return: list of process ids to kill
    """

    # TODO: fix this
    test_outcome.is_pov = test.is_pov
    pids, test_outcome.sig = get_pids_sig(cmd_data.output)
    ok = match_pattern(cmd_data.output, "ok - (.*)")
    not_ok = match_pattern(cmd_data.output, "not ok - (.*)")
    not_ok_polls = re.findall("not ok (\d{1,4}) - (.*)", cmd_data.output)

    if 'timed out' in cmd_data.output:
        test_outcome.error = "Test timed out"
        test_outcome.result = False

    # TODO: fix this
    elif not test.is_pov and not_ok_polls:
        test_outcome.error = "Polls failed"

        for _, msg in not_ok_polls:
            test_outcome.error += f"\n{msg}"

        test_outcome.passed = False
    elif not test.is_pov and not match_pattern(cmd_data.output, "# polls failed: (\d{1,4})"):
        test_outcome.error = "Polls failed"
        test_outcome.passed = False

    # If the test failed to run, consider it failed
    elif 'TOTAL TESTS' not in cmd_data.output:
        test_outcome.error = "Test failed to run."
        test_outcome.passed = False

    elif 'TOTAL TESTS: ' in cmd_data.output:
        total = int(cmd_data.output.split('TOTAL TESTS: ')[1].split('\n')[0])
        passed = int(cmd_data.output.split('TOTAL PASSED: ')[1].split('\n')[0])
        test_outcome.msg = f"TOTAL TESTS: {total} | TOTAL PASSED: {passed}"

        if not_ok:
            test_outcome.msg = not_ok
            test_outcome.passed = False
        elif ok:
            test_outcome.msg = ok
            test_outcome.passed = True
    else:
        test_outcome.error = "Unknown behavior"
        test_outcome.passed = False

    return pids


def config_cmake(env: Dict[Any, Any], replace: bool = False, save_temps: bool = False) -> str:
    cmake_opts = f"{env['CMAKE_OPTS']}" if 'CMAKE_OPTS' in env else ""

    if replace:
        cmake_opts = f"{cmake_opts} -DCMAKE_CXX_OUTPUT_EXTENSION_REPLACE=ON"

    cmake_opts = f"{cmake_opts} -DCMAKE_EXPORT_COMPILE_COMMANDS=ON"

    if save_temps:
        env["SAVETEMPS"] = "True"

    # setting platform architecture
    if '64bit' in platform.architecture()[0] and "M32" not in env:
        cmake_opts = f"{cmake_opts} -DCMAKE_SYSTEM_PROCESSOR=amd64"
    else:
        cmake_opts = f"{cmake_opts} -DCMAKE_SYSTEM_PROCESSOR=i686"

    # clang as default compiler
    if "CC" not in env:
        env["CC"] = "clang"

    if "CXX" not in env:
        env["CXX"] = "clang++"

    # Default shared libs
    build_link = "-DBUILD_SHARED_LIBS=ON -DBUILD_STATIC_LIBS=OFF"

    if "LINK" in env and env["LINK"] == "STATIC":
        build_link = "-DBUILD_SHARED_LIBS=OFF -DBUILD_STATIC_LIBS=ON"

    return f"{cmake_opts} -DCMAKE_C_COMPILER={env['CC']} -DCMAKE_ASM_COMPILER={env['CC']} " \
           f"-DCMAKE_CXX_COMPILER={env['CXX']} {build_link}"


class CGCRepair(CBenchmark):
    """
        Handler for interacting locally with the CGCRepair benchmark
    """

    class Meta:
        label = 'cgcrepair'

    def set(self, project: Project):
        self.env["CGC_INCLUDE_DIR"] = project.packages['include']
        lib_path = project.packages['lib32' if "M32" in self.env else 'lib64']
        self.env["CGC_LIB_DIR"] = lib_path

        if "LD_LIBRARY_PATH" in self.env:
            self.env["LD_LIBRARY_PATH"] = lib_path + ":" + self.env["LD_LIBRARY_PATH"]
        else:
            self.env["LD_LIBRARY_PATH"] = lib_path

    def checkout(self, vid: str, working_dir: str = None, root_dir: str = None, **kwargs) -> Dict[str, Any]:
        project = self.get_by_vid(vid)
        manifest = project.get_manifest(vid)
        corpus_path = Path(self.get_config('corpus'))

        iid, working_dir = self.checkout_handler(project, manifest=manifest, corpus_path=corpus_path,
                                                 working_dir=working_dir, root_dir=root_dir)

        if working_dir:
            # Copy CMakeLists.txt
            shutil.copy2(src=str(corpus_path / 'CMakeLists.txt'), dst=working_dir)

        return {'iid': iid, 'working_dir': working_dir}

    def make(self, context: Context, write_build_args: str = None,
             compiler_trail_path: bool = False, replace: bool = False, save_temps: bool = False,
             **kwargs) -> CommandData:

        cmake_opts = config_cmake(env=self.env, replace=replace, save_temps=save_temps)
        cmd_data = CommandData(args=f"cmake {cmake_opts} {context.root} -DCB_PATH:STRING={context.project.name}",
                               cwd=str(context.build), env=self.env)

        if not context.build.exists():
            self.app.log.info("Creating build directory")
            context.build.mkdir(exist_ok=True)

        cmd_data = super().__call__(cmd_data=cmd_data, raise_err=False, msg="Creating build files.")

        if write_build_args:
            # write the build arguments from the compile_commands file generated by CMake
            commands = self.make_handler.get_cmake_commands(working_dir=context.root, skip_str="-DPATCHED",
                                                            src_dir=context.source / context.project.modules['src'],
                                                            build_dir=context.build,
                                                            compiler_trail_path=compiler_trail_path)

            self.make_handler.write_cmake_build_args(dest=Path(write_build_args), vuln_files=context.project.vuln_files,
                                                     commands=commands, working_dir=context.root)

        return cmd_data

    def build(self, context: Context, coverage: bool = False, fix_files: List[AnyStr] = None,
              inst_files: List[AnyStr] = None, cpp_files: bool = False, backup: str = None, link: bool = False,
              replace: bool = False, tag: str = None, save_temps: bool = False, write_build_args: str = None,
              compiler_trail_path: bool = False, **kwargs) -> Tuple[CommandData, Path]:

        if coverage:
            self.env["COVERAGE"] = "True"

        # TODO: check if the fix files can be replaced by the inst files
        # if fix_files and inst_files and len(fix_files) != len(inst_files):
        #    error = f"The files [{fix_files}] can not be mapped. Uneven number of files [{inst_files}]."
        #    raise ValueError(error)

        cmake_source_path = context.build / context.project.name / "CMakeFiles" / f"{context.project.name}.dir"

        # Backups manifest files
        if backup:
            cmd_data = self.build_handler.backup_manifest_files(out_path=Path(backup), source_path=context.source,
                                                                manifest_files=context.project.vuln_files)

        if link:
            cmd_data = self.build_handler.cmake_link_executable(source_path=context.source,
                                                                cmake_path=cmake_source_path,
                                                                build_path=context.build / context.project.name)
        elif inst_files:
            mappings = context.project.map_files(inst_files, replace_ext=('.c', '.i'), skip_ext=[".h"])
            cmake_commands = self.build_handler.get_cmake_commands(working_dir=context.root,
                                                                   src_dir=context.source / context.project.modules[
                                                                       'source'],
                                                                   build_dir=context.build, skip_str="-DPATCHED",
                                                                   compiler_trail_path=compiler_trail_path)
            inst_commands = self.build_handler.commands_to_instrumented(mappings=mappings, commands=cmake_commands,
                                                                        replace_str=('-save-temps=obj', ''))
            cmd_data = self.build_handler.cmake_build_preprocessed(inst_commands=inst_commands,
                                                                   build_path=context.build)

            # links objects into executable
            cmd_data = self.build_handler.cmake_link_executable(source_path=context.source,
                                                                cmake_path=cmake_source_path,
                                                                build_path=context.build / context.project.name)

            self.app.log.info(f"Built instrumented files {inst_files}.")
        else:
            cmd_data = self.make(context=context, write_build_args=write_build_args, save_temps=save_temps,
                                 compiler_trail_path=compiler_trail_path, replace=replace)

            cmd_data = self.build_handler.cmake_build(target=context.project.name, cwd=str(context.build),
                                                      env=self.env)

        return cmd_data, cmake_source_path

    def test(self, context: Context, tests: Oracle, timeout: int, neg_pov: bool = False, prefix: str = None,
             print_ids: bool = False, write_fail: bool = True, only_numbers: bool = False, print_class: bool = False,
             out_file: str = None, **kwargs) -> List[TestOutcome]:

        bin_names = get_binaries(context.source, binary=context.build / context.project.name / context.project.name)
        test_outcomes = []
        tests.args = f"{tests.args} --directory {context.build / context.project.name} --concurrent 1 --debug " \
                     f"--negotiate_seed --timeout {timeout} --cb {' '.join(bin_names)}"

        for name, test in tests.cases.items():
            # TODO: check if pov_seed is necessary for POVs
            # seed = binascii.b2a_hex(os.urandom(48))
            # cb_cmd += ['--pov_seed', seed.decode()]

            # TODO: should pass the general path to specific path if none
            if tests.path:
                test.file = Path(tests.path, test.file)

            args = f"{tests.args} --xml {test.file}"

            _, outcome = self.test_handler.run(context, test, timeout=timeout, script=tests.script, env=self.env,
                                               cwd=tests.cwd, kill=True, args=args,
                                               process_outcome=parse_output_to_outcome)
            test_outcomes.append(outcome)

            if outcome.is_pov and neg_pov:
                # Invert negative test's result
                outcome.passed = not outcome.passed

            if print_ids and outcome.passed:
                if only_numbers:
                    print(outcome.name[1:])
                else:
                    print(outcome.name)
            if print_class:
                print("PASS" if outcome.passed else 'FAIL')

            if out_file is not None:
                self.test_handler.write_result(outcome, out_file=Path(out_file), write_fail=write_fail,
                                               prefix=Path(prefix) if prefix else None)

            # TODO: check this if is necessary
            '''
            if not outcome.passed or outcome.error:
                if not outcome.is_pov:
                    self.failed = True
                elif not neg_pov:
                    self.failed = True
            '''
        return test_outcomes

    def gen_tests(self, project: Project, **kwargs) -> CommandData:
        pass

    def gen_povs(self, project: Project, **kwargs) -> CommandData:
        pass


def load(nexus):
    nexus.handler.register(CGCRepair)
