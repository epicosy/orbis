from dataclasses import dataclass
from pathlib import Path

from orbis.data.schema import Program, Project, Manifest
from orbis.ext.database import Instance


@dataclass
class Context:
    root: Path
    source: Path
    build: Path
    program: Program
    instance: Instance
    project: Project
    manifest: Manifest

    @property
    def src(self):
        return self.source / self.program.paths.source
