from dataclasses import dataclass
from pathlib import Path

from orbis.data.schema import Project
from orbis.ext.database import Instance


@dataclass
class Context:
    root: Path
    source: Path
    build: Path
    project: Project
    instance: Instance
