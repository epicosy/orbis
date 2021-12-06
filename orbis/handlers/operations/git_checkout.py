import traceback
from pathlib import Path
from shutil import copytree, ignore_patterns
from typing import Tuple

from git import Repo

from orbis.core.exc import OrbisError
from orbis.data.schema import Project, Manifest
from orbis.handlers.operations.checkout import CheckoutHandler


class GitCheckoutHandler(CheckoutHandler):
    """
        Checkouts project to specific commit version.
        The corpus is a single Git-repository, where each vulns lies on a branch
    """

    class Meta:
        label = 'git_checkout'

    def __call__(self, project: Project, manifest: Manifest, corpus_path: Path, working_dir: Path = None,
                 root_dir: Path = None, seed: int = None, force: bool = False) -> Tuple[int, Path]:
        """
            Checkouts to the manifest commit version the project and copies the files to the working directory.

            :param project: data object representation of the project
            :param manifest: data object representation of the manifest
            :param corpus_path: path where the projects are stored
            :param working_dir: destination path of the clone. the default uses the project's name and a random seed
            :param root_dir: root path to be used for the working directory: default is '/tmp'.
            :param seed: random seed for the working directory.
            :param force: flag to overwrite existing working directory.
        """
        try:
            if not corpus_path.exists():
                raise OrbisError(f"Corpus path {corpus_path} not found.")

            repo = Repo(str(corpus_path))

            working_dir = self._mkdir(project.name, working_dir, root_dir, force, seed)

            if repo.commit() != repo.commit(manifest.commit):
                repo.git.checkout(manifest.commit)
                self.app.log.info(f"Checked out {project.name} to commit {manifest.commit}")

            self.app.log.info(f"Copying files to {working_dir}.")

            copytree(src=str(corpus_path), dst=str(working_dir), dirs_exist_ok=True, ignore=ignore_patterns('.git'))
            # self._write_manifest(working_dir_source)
            _id = self._save(manifest.commit, working_dir)

            print(f"Checked out {project.name} - {manifest.commit}.")
            print(f"Id: {_id}\nWorking directory: {working_dir}")

            # restore to head
            repo.git.checkout('HEAD')

            return _id, working_dir

        except Exception as e:
            self.error = str(e)
            self.app.log.warning(traceback.format_exc())
            return None, None
