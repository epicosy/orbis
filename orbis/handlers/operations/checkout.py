import traceback
from binascii import b2a_hex
from os import urandom
from pathlib import Path
from typing import Tuple

from cement import Handler
from git import Repo

from orbis.core.exc import NotEmptyDirectory, OrbisError
from orbis.core.interfaces import HandlersInterface
from shutil import copytree

from orbis.data.schema import Project, Manifest
from orbis.ext.database import Instance


class CheckoutHandler(HandlersInterface, Handler):
    """
        Checkouts project to specific commit version.
    """

    class Meta:
        label = 'checkout'

    def __call__(self, project: Project, manifest: Manifest, corpus_path: Path, working_dir: Path = None,
                 root_dir: Path = None, seed: int = None, force: bool = False) -> Tuple[int, Path]:
        """
            Checkouts the project to the manifest commit version and copies the files to the working directory.

            :param project: data object representation of the project
            :param manifest: data object representation of the manifest
            :param corpus_path: path where the projects are stored
            :param working_dir: destination path of the clone. the default uses the project's name and a random seed
            :param root_dir: root path to be used for the working directory: default is '/tmp'.
            :param seed: random seed for the working directory.
            :param force: flag to overwrite existing working directory.
        """
        try:
            project_path = corpus_path / project.name

            if not project_path.exists():
                raise OrbisError(f"Project path {project_path} not found.")

            repo = Repo(str(project_path))

            working_dir = self._mkdir(project.name, working_dir, root_dir, force, seed)
            head = repo.commit()

            if repo.commit() != repo.commit(manifest.commit):
                repo.git.checkout(manifest.commit)
                self.app.log.info(f"Checked out {project.name} to commit {manifest.commit}")

            self.app.log.info(f"Copying files to {working_dir}.")

            # TODO: copy without the .git folder
            copytree(src=str(project_path), dst=str(working_dir / project.name), dirs_exist_ok=True)
            # self._write_manifest(working_dir_source)
            _id = self._save(project.id, manifest.commit, working_dir)

            print(f"Checked out {project.name} - {manifest.commit}.")
            print(f"Id: {_id}\nWorking directory: {working_dir}")

            # restore to head
            self.app.log.info(f"Restoring to {head}")
            repo.git.checkout(head)

            return _id, working_dir

        except Exception as e:
            self.error = str(e)
            self.app.log.warning(traceback.format_exc())
            return None, None

    def _save(self, pid: str, commit: str, working_dir: Path) -> int:
        # Inserting instance into database
        instance = Instance(sha=commit, path=str(working_dir), pid=pid)
        _id = self.app.db.add(instance)

        # write the instance id to a file inside the working directory
        # useful to use in external scripts and to keep track locally of instances
        with (working_dir / '.instance_id').open(mode='w') as oid:
            oid.write(str(_id))

        return _id

    def _mkdir(self, project_name: str, working_dir: Path = None, root_dir: Path = None, force: bool = False,
               seed: int = None):
        # Make working directory
        if not working_dir:
            if not seed:
                seed = b2a_hex(urandom(2)).decode()

            working_dir = Path(root_dir if root_dir else self.app.get_config('root_dir'),
                               f"{project_name}_{seed}")

        self.app.log.info(f"Checking out {project_name} to {working_dir}.")

        if working_dir.exists():
            if any(working_dir.iterdir()) and not force:
                raise NotEmptyDirectory(f"Working directory {working_dir} exists and is not empty.")
        else:
            self.app.log.info("Creating working directory.")
            working_dir.mkdir(parents=True)

        return working_dir

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
