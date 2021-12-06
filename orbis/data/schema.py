from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Tuple
from schema import Schema, Or, And, Use, Optional

from orbis.core.exc import OrbisError

vulnerability = Schema(And({str: {'cwe': int,
                                  'exploit': str,
                                  'cve': Or(str, None),
                                  'related': Or([int], None),
                                  'generic': [str],
                                  'build_system': str,
                                  'java_version': str,
                                  'failing_module': str,
                                  'locs': Schema(And({str: [int]},
                                                     Use(
                                                         lambda d: [Location(file=Path(k), lines=v) for k, v in
                                                                    d.items()])))
                                  }},
                           Use(lambda d: [Vulnerability(id=k, **v) for k, v in d.items()])))

manifest = Schema(And({str: And({'id': str,
                                 'cwe': int,
                                 'exploit': str,
                                 'cve': Or(str, None),
                                 'related': Or([int], None),
                                 'generic': [str],
                                 'build_system': str,
                                 'java_version': str,
                                 'failing_module': str,
                                 'locs': Schema(And({str: [int]},
                                                    Use(
                                                        lambda d: [Location(file=Path(k), lines=v) for k, v in
                                                                   d.items()])))
                                 }, Use(lambda v: Vulnerability(**v)))},
                      Use(lambda m: [Manifest(commit=k, vuln=v) for k, v in m.items()])))

paths = Schema(And({'source': str, 'lib': Or(str, None), 'include': Or(str, None)},
                   Use(lambda d: Paths(source=d['source'], lib=d['lib'], include=d['include']))))


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
class Vulnerability:
    """
        Data object represents an instance of a vulnerability in a Project/Program
    """
    id: str
    cwe: int
    exploit: str
    locs: List[Location]
    related: List[int]
    generic: List[str]
    cve: str = '-',
    build_system: str = '-',
    java_version: str = '-',
    failing_module: str = '-',

    def jsonify(self):
        """
            Transforms object to JSON representation.
        """
        return {'id': self.id, 'cwe': self.cwe, 'exploit': self.exploit, 'related': self.related, 'cve': self.cve,
                'generic': self.generic, 'build_system': self.build_system, 'java_version': self.java_version,
                'failing_module': self.failing_module,
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
class Test:
    """
        Data object represents a test case. 
    """
    id: str
    order: int
    file: str
    timeout: int = None
    script: str = ""
    args: str = ""
    is_pov: bool = False

    def jsonify(self):
        """
            Transforms object to JSON representation.
        """
        return {'id': self.id, 'order': self.order, 'file': self.file, 'script': self.script, 'args': self.args,
                "timeout": self.timeout, 'is_pov': self.is_pov}


@dataclass
class Oracle:
    """
        Data object representing the oracle.
    """
    cases: Dict[str, Test]
    path: Path = None
    script: str = ""
    args: str = ""

    def __len__(self):
        return len(self.cases)

    def jsonify(self):
        """
            Transforms object to JSON representation.
        """
        return {'cases': {name: test.jsonify() for name, test in self.cases.items()},
                "script": self.script, "path": self.path, "args": self.args}


@dataclass
class Paths:
    """
        Data object represents the paths associated to a Program/Project.
    """
    source: str = None
    lib: str = None
    include: str = None

    def jsonify(self):
        """
            Transforms object to JSON representation.
        """
        return {'source': self.source, 'lib': self.lib, 'include': self.include}

    @property
    def src(self):
        """
            Returns the full path to the source code.
        """
        return self.root / self.source

    def has_source(self):
        """
            Checks whether source code directory exists.
        """
        return self.source and (self.root / self.source).exists()

    def has_lib(self):
        """
            Checks whether dependency directory exists.
        """
        return self.lib and (self.root / self.lib).exists()

    def has_include(self):
        """
            Checks whether include directory exists.
        """
        return self.include and (self.root / self.include).exists()


@dataclass
class Program:
    """
        Data object represents a program in the dataset.
    """
    id: str
    name: str
    manifest: List[Vulnerability]
    paths: Paths

    def jsonify(self):
        """
            Transforms object to JSON representation.
        """
        return {
            self.id:
                {
                    'name': self.name,
                    'paths': self.paths.jsonify(),
                    'manifest': {k: v for vuln in self.manifest for k, v in vuln.jsonify().items()}
                }
        }

    @property
    def vuln_files(self):
        """
            Returns the paths for all vulnerable files in the program.
        """
        return [file for vuln in self.manifest for file in vuln.files]

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


@dataclass
class Project:
    """
        Data object that represents a project in the metadata  
    """
    repo_path: str
    name: str
    id: str
    manifest: List[Manifest]
    patches: dict
    paths: Paths

    def get_manifest(self, vid: str):
        for m in self.manifest:
            if m.vuln.id == vid:
                return m

        raise OrbisError(f"Manifest with vulnerability id {vid} not found")

    def get_manifest_by_commit_sha(self, commit_sha: str):
        for m in self.manifest:
            if m.commit == commit_sha:
                return m

        raise OrbisError(f"Manifest with commit sha {commit_sha} not found")

def get_cases(cases: Dict[str, dict], pov: bool, select: List[str] = None):
    """
        Returns the test cases from the oracle YAML
    """
    if select:
        return {c: Test(id=c, **cases[c], is_pov=pov) for c in select if c in cases}
    return {k: Test(id=k, **v, is_pov=pov) for k, v in cases.items()}


def parse_oracle(yaml: dict, select: List[str] = None, pov: bool = False) -> Oracle:
    """
        Parses the oracle YAML
    """
    return Schema(And({'cases': Schema(And({str: {'order': int, 'file': str,
                                                  Optional('script', default=""): str,
                                                  Optional('timeout', default=""): int,
                                                  Optional('args', default=""): str}
                                            }, Use(lambda c: get_cases(c, pov, select)))),
                       "script": str,
                       Optional('path', default=""): str,
                       Optional('args', default=""): str},
                      Use(lambda o: Oracle(cases=o['cases'], script=o['script'], args=o['args'],
                                           path=Path(o['path']))))).validate(yaml)


def parse_metadata(yaml: dict) -> Program:
    """
        Parses the metadata for a program
    """
    return Schema(And({'id': str, 'name': str, 'manifest': manifest, 'paths': paths},
                      Use(lambda prog: Program(**prog)))).validate(yaml)


def parse_dataset(yaml: dict) -> List[Project]:
    """
        Returns the projects in the metadata file.
    """
    return Schema(And({str: {'id': str, 'name': str, 'manifest': manifest, 'paths': paths,
                             Optional('patches', default={}): dict}},
                      Use(lambda proj: [Project(**v, repo_path=k) for k, v in proj.items()]))).validate(yaml)
