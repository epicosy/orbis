from pathlib import Path
from typing import List
import fileinput


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


def collect_coverage(out_dir: Path, cov_dir: Path, cov_suffix: str, rename_suffix: str = None):
    """
        copies coverage file generated to coverage dir with respective name
    """
    for file in collect_files(cov_dir, cov_suffix):
        in_file = cov_dir / file
        out_path = out_dir / file.parent
        out_file = out_path / Path(file.name)

        if not out_path.exists():
            out_path.mkdir(parents=True, exist_ok=True)

        if in_file.exists():
            concat_file = Path(file.stem + rename_suffix) if rename_suffix is not None else Path(out_file)
            concat_file = out_path / concat_file

            with concat_file.open(mode="a") as fout, fileinput.input(in_file) as fin:
                for line in fin:
                    fout.write(line)
            # delete the file generated
            in_file.unlink()