from pathlib import Path
from typing import List, Dict, Tuple

from orbis.core.exc import OrbisError
from orbis.data.schema import Project
from orbis.ext.database import CompileOutcome
from orbis.handlers.benchmark.benchmark import args_to_str
from orbis.handlers.operations.c.make import MakeHandler
from orbis.data.results import CommandData


class BuildHandler(MakeHandler):
    class Meta:
        label = "build"

    def backup_manifest_files(self, out_path: Path, source_path: Path, manifest_files: List[Path]) -> CommandData:
        """
            Backups the manifest files to an output path.
            :param out_path: Output directory.
            :param source_path: Path to the directory with the target program.
            :param manifest_files: List of target file relative paths (src/main.c) to
                                    the working directory (/tmp/program_dir).
            :return: Last call result for the 'cp' command.
        """
        cmd_data = CommandData.get_blank()

        for file in manifest_files:
            bckup_path = out_path / file.parent

            if not bckup_path.exists():
                bckup_path.mkdir(parents=True, exist_ok=True)

            count = self.app.db.count(CompileOutcome) + 1
            bckup_file = bckup_path / f"{file.stem}_{count}{file.suffix}"

            cmd_data = super().__call__(cmd_data=CommandData(args=f"cp {file} {bckup_file}", cwd=str(source_path)),
                                        msg=f"Backup of manifest file {file} to {out_path}.\n", raise_err=True)

        return cmd_data

    def cmake_build(self, target: str, env: dict = None, cwd: str = None, **kwargs) -> CommandData:
        args = args_to_str(kwargs) if kwargs else ""
        cmd_data = CommandData(args=f"cmake --build . --target {target} {args}", cwd=cwd, env=env)
        super().__call__(cmd_data=cmd_data, msg=f"Building {target}\n", raise_err=True)
        self.app.log.info(f"Built {target}.")
        return cmd_data

    def cmake_build_preprocessed(self, inst_commands: Dict[str, str], build_path: Path) -> CommandData:
        """
            Builds the instrumented preprocessed files to objects.
            :param inst_commands: Dictionary with the modified cmake commands for building the instrumented files.
            :param build_path: Path to the build directory.
            :return: Command outcome for the last built file or the failed command.
        """

        if not inst_commands:
            raise OrbisError(f"No instrumented commands.")

        cmd_data = CommandData.get_blank()

        self.app.log.info(f"Building preprocessed files {list(inst_commands.keys())}.")

        for file, command in inst_commands.items():
            cmd_data = self.build_preprocessed_file(file, command, build_path=build_path)

        return cmd_data

    def build_preprocessed_file(self, file: str, command: str, build_path: Path) -> CommandData:
        if Path(file).exists():
            return super().__call__(CommandData(args=command, cwd=str(build_path)), raise_err=True,
                                    msg=f"Creating object file for {file}.\n")

        raise OrbisError(f"File {file} not found.")

    def cmake_link_executable(self, source_path: Path, cmake_path: Path, build_path: Path,
                              env: dict = None) -> CommandData:
        self.app.log.info(f"Linking into executable {source_path.name}.")
        link_file = cmake_path / "link.txt"

        if link_file.exists():
            cmd_str = f"cmake -E cmake_link_script {link_file} {source_path.name}"
            return super().__call__(cmd_data=CommandData(args=cmd_str, cwd=str(build_path), env=env),
                                    msg="Linking object files into executable.\n", raise_err=True)

        raise OrbisError(f"Link file {link_file} found")

    @staticmethod
    def commands_to_instrumented(mappings: Dict[str, str], commands: Dict[str, Dict[str, str]],
                                 replace_str: Tuple[str, str] = None) -> Dict[str, str]:
        """
            Replaces the commands.
            :param mappings: Dictionary with the mappings between the original files and the instrumented files.
            :param commands: Dictionary with the cmake commands for each file for building the files.
            :param replace_str: Tuple pair with old and new strings to replace in the the command.
            :return: Returns the dictionary of instrumented files with the associated build command.
        """

        if not mappings:
            raise OrbisError("No mappings between source files and instrumented files")

        matches = dict()

        for file, inst_file in mappings.items():
            if file in commands:
                matches[inst_file] = commands[file]['command'].replace(str(commands[file]['file']), inst_file)

                if replace_str:
                    matches[inst_file] = matches[inst_file].replace(*replace_str)

            else:
                raise OrbisError(f"Could not find compile command for {file}.")

        return matches
