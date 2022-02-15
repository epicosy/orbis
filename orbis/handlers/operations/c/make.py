import json
from pathlib import Path
from typing import List

from orbis.handlers.command import CommandHandler
from orbis.ext.database import CompileOutcome, Instance

from orbis.data.misc import Context
from orbis.data.results import CommandData


class MakeHandler(CommandHandler):
    class Meta:
        label = 'make'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @staticmethod
    def get_cmake_commands(working_dir: Path, src_dir: Path, build_dir: Path, compiler_trail_path: bool = False,
                           skip_str: str = None) -> dict:
        compile_commands = {}

        if (build_dir / Path('compile_commands.json')).exists():
            with (build_dir / Path('compile_commands.json')).open(mode="r") as json_file:
                for entry in json.loads(json_file.read()):
                    if compiler_trail_path:
                        entry['command'] = entry['command'].replace('/usr/bin/', '')

                    if skip_str in entry['command']:
                        continue

                    # Looking for the path within the source code folder
                    if entry['file'].startswith(str(src_dir)):
                        short_path = Path(entry['file']).relative_to(src_dir)
                    else:
                        short_path = Path(entry['file']).relative_to(working_dir)

                    compile_commands[str(short_path)] = {'file': Path(entry['file']),
                                                         'dir': Path(entry['directory']),
                                                         'command': entry['command']}

        return compile_commands

    @staticmethod
    def write_cmake_build_args(dest: Path, vuln_files: List[Path], commands: dict, working_dir: Path):
        for file in vuln_files:
            if file.name.endswith(".h"):
                continue

            with dest.open(mode="a") as baf:
                cmd = commands[file.name]['command'].split()
                bargs = ' '.join(cmd[1:-2])
                baf.write(f"{working_dir}\n{bargs}\n")

            dest.chmod(0o777)

    def save_outcome(self, cmd_data: CommandData, context: Context, tag: str = None):
        outcome = CompileOutcome(instance_id=context.instance.id, error=cmd_data.error, exit_status=cmd_data.exit_status,
                                 tag=tag if tag else self.Meta.label)

        co_id = self.app.db.add(outcome)
        self.app.db.update(entity=Instance, entity_id=context.instance.id, attr='pointer', value=co_id)
        self.app.log.debug(f"Inserted '{self.Meta.label} outcome' with id {co_id} for instance {context.instance.id}.")

        return co_id
