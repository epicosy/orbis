import traceback
from binascii import b2a_hex
from os import urandom
from pathlib import Path
from typing import Tuple

from cement import Handler

from orbis.core.exc import NotEmptyDirectory
from orbis.core.interfaces import HandlersInterface
from shutil import copytree

from orbis.data.schema import Program
from orbis.ext.database import Instance


class CheckoutHandler(HandlersInterface, Handler):
    class Meta:
        label = 'checkout'

    def __call__(self, program: Program, working_dir: Path = None, root_dir: Path = None, seed: int = None,
                 force: bool = False) -> Tuple[int, Path]:
        try:
            self.app.log.warning(str(program))
            working_dir = self._mkdir(program.name, working_dir, root_dir, force, seed)
            working_dir_source = working_dir / program.name

            self._checkout_files(program, working_dir, working_dir_source)
            # self._write_manifest(working_dir_source)
            _id = self._save(program, working_dir)

            print(f"Checked out {program.name}.")
            print(f"Id: {_id}\nWorking directory: {working_dir}")

            return _id, working_dir

        except Exception as e:
            self.error = str(e)
            self.app.log.warning(traceback.format_exc())
            return None, None

    def _save(self, program: Program, working_dir: Path) -> int:
        # Inserting instance into database
        instance = Instance(pid=program.id, path=str(working_dir))
        _id = self.app.db.add(instance)

        # write the instance id to a file inside the working directory
        # useful to use in external scripts and to keep track locally of instances
        with (working_dir / '.instance_id').open(mode='w') as oid:
            oid.write(str(_id))

        return _id

    def _mkdir(self, program_name: str, working_dir: Path = None, root_dir: Path = None, force: bool = False,
               seed: int = None):
        # Make working directory
        if not working_dir:
            if not seed:
                seed = b2a_hex(urandom(2)).decode()

            working_dir = Path(root_dir if root_dir else self.app.get_config('root_dir'),
                               f"{program_name}_{seed}")

        self.app.log.info(f"Checking out {program_name} to {working_dir}.")

        if working_dir.exists():
            if any(working_dir.iterdir()) and not force:
                raise NotEmptyDirectory(f"Working directory {working_dir} exists and is not empty.")
        else:
            self.app.log.info("Creating working directory.")
            working_dir.mkdir(parents=True)

        return working_dir

    def _checkout_files(self, program: Program, working_dir: Path, working_dir_source: Path):
        self.app.log.info(f"Copying files to {working_dir}.")

        # Copy challenge source files
        working_dir_source.mkdir()
        copytree(src=str(program.paths.root), dst=str(working_dir_source), dirs_exist_ok=True)

    # TODO: handle this
    '''
    def _write_manifest(self, working_dir_source: Path):
        if self.app.pargs.verbose:
            self.app.log.info(f"Writing manifest files.")

        manifest = Manifest(source_path=working_dir_source)
        manifest.write()

        if self.no_patch:
            vuln_files = ', '.join(manifest.vuln_files.keys())
            self.app.log.info(f"Removing patches definitions from vulnerable files {vuln_files}.")
            manifest.remove_patches(working_dir_source)
    '''
