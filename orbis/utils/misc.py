from pathlib import Path
from typing import List


def collect_files(path: Path, target_suffix: str) -> List[Path]:
    coverage_files = []

    def recurse_walk(current: Path, parent: Path, suffix: str):
        for f in current.iterdir():
            if f.is_dir():
                recurse_walk(f, parent / Path(f.name), suffix)
            elif f.name.endswith(suffix):
                short_path = parent / Path(f.name)
                coverage_files.append(short_path)

    for folder in path.iterdir():
        if folder.is_dir():
            recurse_walk(folder, Path(folder.name), target_suffix)

    return coverage_files
