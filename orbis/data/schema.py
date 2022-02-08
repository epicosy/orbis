from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Tuple
from schema import Schema, Or, And, Use, Optional

from orbis.core.exc import OrbisError

build = Schema(And({Optional('system', default=""): str, Optional('version', default=""): str,
                    Optional('arch', default=32): int, Optional('args', default=""): str,
                    Optional('script', default=""): str, Optional('env', default={}): dict},
                   Use(lambda b: Build(**b))))


def get_oracle(is_pov: bool = False):
    return Schema(And({'cases': Schema(And({str: {'order': int, 'file': str,
                                                  Optional('script', default=""): str,
                                                  Optional('cwd', default=None): str,
                                                  Optional('timeout', default=""): int,
                                                  Optional('args', default=""): str}
                                            },
                                           Use(lambda c: {k: Test(id=k, **v, is_pov=is_pov) for k, v in c.items()}))),
                       "script": str,
                       Optional('cwd', default=None): str,
                       Optional('path', default=""): str,
                       Optional('args', default=""): str},
                      Use(lambda o: Oracle(cases=o['cases'], script=o['script'], args=o['args'], path=Path(o['path']),
                                           cwd=o['cwd']))))


manifest = Schema(And({str: And({'id': str,
                                 'cwe': int,
                                 'oracle': get_oracle(is_pov=True),
                                 Optional('build', default=None): build,
                                 'cve': Or(str, None),
                                 'related': Or([int], None),
                                 'generic': [str],
                                 'locs': Schema(And({str: [int]},
                                                    Use(
                                                        lambda d: [Location(file=Path(k), lines=v) for k, v in
                                                                   d.items()])))
                                 }, Use(lambda v: Vulnerability(**v)))},
                      Use(lambda m: [Manifest(commit=k, vuln=v) for k, v in m.items()])))


@dataclass
class Build:
    """
        Data object representing the build configurations
    """
    system: str
    version: str
    arch: int
    args: str
    script: str
    env: dict


@dataclass
class Location:
    """
        Data object represents the location of a vulnerability in the source code.
    """
    file: Path
    lines: List[int]

    def jsonify(self):
        """
            Transforms object to JSON representation.
        """
        return {str(self.file): self.lines}


@dataclass
class Test:
    """
        Data object represents a test case.
    """
    id: str
    order: int
    file: str
    timeout: int = None
    cwd: str = None
    script: str = ""
    args: str = ""
    is_pov: bool = False

    def jsonify(self):
        """
            Transforms object to JSON representation.
        """
        return {'id': self.id, 'order': self.order, 'file': self.file, 'cwd': self.cwd, 'script': self.script,
                'args': self.args, "timeout": self.timeout, 'is_pov': self.is_pov}


@dataclass
class Oracle:
    """
        Data object representing the oracle.
    """
    cases: Dict[str, Test]
    path: Path = None
    cwd: str = None
    script: str = ""
    args: str = ""

    def __len__(self):
        return len(self.cases)

    def copy(self, cases: List[str]):
        """
            Returns a copy of the oracle with the specified test cases.
        """

        if not cases or len(cases) == 0:
            return Oracle(cases=self.cases.copy(), path=self.path, cwd=self.cwd, script=self.script, args=self.args)

        return Oracle(cases={k: v for k, v in self.cases.items() if k in cases}, path=self.path, cwd=self.cwd,
                      script=self.script, args=self.args)

    def jsonify(self):
        """
            Transforms object to JSON representation.
        """
        return {'cases': {name: test.jsonify() for name, test in self.cases.items()}, 'cwd': self.cwd,
                "script": self.script, "path": str(self.path), "args": self.args}


@dataclass
class Vulnerability:
    """
        Data object represents an instance of a vulnerability in a Project/Program
    """
    id: str
    cwe: int
    oracle: Oracle
    build: Build
    locs: List[Location]
    related: List[int]
    generic: List[str]
    cve: str = '-',

    def jsonify(self):
        """
            Transforms object to JSON representation.
        """

        return {'id': self.id, 'cwe': self.cwe, 'oracle': self.oracle.jsonify(), 'related': self.related, 'cve': self.cve,
                'build': self.build, 'generic': self.generic,
                'locs': {k: v for loc in self.locs for k, v in loc.jsonify().items()}}

    @property
    def files(self) -> List[Path]:
        """
            Returns the list with the paths for the vulnerable files.
        """
        return [loc.file for loc in self.locs]


@dataclass
class Manifest:
    """
        Data object represents a vulnerable commit version.
    """
    commit: str
    vuln: Vulnerability

    def jsonify(self):
        """
            Transforms manifest object to JSON representation.
        """
        vuln = self.vuln.jsonify()
        vuln['commit'] = self.commit

        return vuln


@dataclass
class Project:
    """
        Data object that represents a project in the metadata  
    """
    repo_path: str
    name: str
    id: str
    build: Build
    oracle: Oracle
    manifest: List[Manifest]
    modules: dict
    packages: dict
    patches: dict

    def jsonify(self):
        """
            Transforms object to JSON representation.
        """
        return {
            self.id:
                {
                    'name': self.name,
                    'manifest': {k: v for vuln in self.manifest for k, v in vuln.jsonify().items()}
                }
        }

    def get_manifest(self, vid: str):
        for m in self.manifest:
            if m.vuln.id == vid:
                return m

        raise OrbisError(f"Manifest with vulnerability id {vid} not found")

    def get_version(self, sha: str):
        for m in self.manifest:
            if m.commit == sha:
                return m

        raise OrbisError(f"Manifest with sha {sha} not found")

    @property
    def vuln_files(self):
        """
            Returns the paths for all vulnerable files in the program.
        """
        return [file for version in self.manifest for file in version.vuln.files]

    def map_files(self, files: List[str], replace_ext: Tuple[str, str], skip_ext: List[str]) -> Dict[(str, str)]:
        """
        Maps the files in the manifest with a list of supplied files. In case the replace_ext argument is supplied,
        it replaces the file extension.
        :param files: List of files to map to the vulnerable files.
        :param replace_ext: Tuple with a pair (old, new) of extensions. Replaces old with new for the comparison.
        :param skip_ext: List of extensions to skip files with the particular extension.
        :return: Dictionary with vulnerable files matched by the name with the provided files (vuln_file, match_file).
                The comparison considers the relative path to the working directory.
        """

        mapping = {}

        for short_path in self.vuln_files:
            if skip_ext and short_path.suffix in skip_ext:
                continue

            if replace_ext:
                short_path = str(short_path).replace(replace_ext[0], replace_ext[1])

            for file in files:
                if short_path in file:
                    if replace_ext:
                        short_path = short_path.replace(replace_ext[1], replace_ext[0])
                    mapping[short_path] = file
                    break

        return mapping


def parse_dataset(yaml: dict) -> List[Project]:
    """
        Returns the projects in the metadata file.
    """
    return Schema(And({str: {'id': str, 'name': str, 'manifest': manifest, 'oracle': get_oracle(is_pov=False),
                             'build': build, Optional('patches', default={}): dict,
                             Optional('modules', default={}): dict, Optional('packages', default={}): dict}},
                      Use(lambda proj: [Project(**v, repo_path=k) for k, v in proj.items()]))).validate(yaml)
