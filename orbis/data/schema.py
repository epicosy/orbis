from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Tuple
from schema import Schema, Or, And, Use, Optional


@dataclass
class Location:
    file: Path
    lines: List[int]

    def jsonify(self):
        return {str(self.file): self.lines}


@dataclass
class Vulnerability:
    id: str
    cwe: int
    exploit: str
    locs: List[Location]
    related: List[int]
    generic: List[str]
    cve: str = '-'

    def jsonify(self):
        return {'id': self.id, 'cwe': self.cwe, 'exploit': self.exploit, 'related': self.related, 'cve': self.cve,
                'generic': self.generic, 'locs': {k: v for loc in self.locs for k, v in loc.jsonify().items()}}

    @property
    def files(self) -> List[Path]:
        return [loc.file for loc in self.locs]


@dataclass
class Test:
    id: str
    order: int
    file: str
    timeout: int = None
    script: str = ""
    args: str = ""
    is_pov: bool = False

    def jsonify(self):
        return {'id': self.id, 'order': self.order, 'file': self.file, 'script': self.script, 'args': self.args,
                "timeout": self.timeout, 'is_pov': self.is_pov}


@dataclass
class Oracle:
    cases: Dict[str, Test]
    path: Path = None
    script: str = ""
    args: str = ""

    def __len__(self):
        return len(self.cases)

    def jsonify(self):
        return {'cases': {name: test.jsonify() for name, test in self.cases.items()},
                "script": self.script, "path": self.path, "args": self.args}


@dataclass
class Paths:
    root: Path
    source: str = None
    lib: str = None
    include: str = None

    def jsonify(self):
        return {'root': self.root, 'source': self.source, 'lib': self.lib, 'include': self.include}

    @property
    def src(self):
        return self.root / self.source

    def has_source(self):
        return self.source and (self.root / self.source).exists()

    def has_lib(self):
        return self.lib and (self.root / self.lib).exists()

    def has_include(self):
        return self.include and (self.root / self.include).exists()


@dataclass
class Program:
    id: str
    name: str
    manifest: List[Vulnerability]
    paths: Paths

    def jsonify(self):
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


def get_cases(cases: Dict[str, dict], pov: bool, select: List[str] = None):
    if select:
        return {c: Test(id=c, **cases[c], is_pov=pov) for c in select if c in cases}
    return {k: Test(id=k, **v, is_pov=pov) for k, v in cases.items()}


def parse_oracle(yaml: dict, select: List[str] = None, pov: bool = False) -> Oracle:
    return Schema(And({'cases': Schema(And({str: {'order': int, 'file': str,
                                                  Optional('script', default=""): str,
                                                  Optional('timeout', default=""): int,
                                                  Optional('args', default=""): str}
                                            }, Use(lambda c: get_cases(c, pov, select)))),
                       "script": str,
                       "path": str,
                       Optional('args', default=""): str},
                      Use(lambda o: Oracle(cases=o['cases'], script=o['script'], args=o['args'], 
                                           path=Path(o['path']))))).validate(yaml)


def parse_metadata(yaml: dict) -> Program:
    manifest = Schema(And({str: {'cwe': int,
                                 'exploit': str,
                                 'cve': Or(str, None),
                                 'related': Or([int], None),
                                 'generic': [str],
                                 'locs': Schema(And({str: [int]},
                                                    Use(
                                                        lambda d: [Location(file=Path(k), lines=v) for k, v in
                                                                   d.items()])))
                                 }},
                          Use(lambda d: [Vulnerability(id=k, **v) for k, v in d.items()])))

    paths = Schema(And({'root': str, 'source': str, 'lib': Or(str, None), 'include': Or(str, None)},
                       Use(lambda d:
                           Paths(root=Path(d['root']), source=d['source'], lib=d['lib'], include=d['include']))))

    return Schema(And({'id': str, 'name': str, 'manifest': manifest, 'paths': paths},
                      Use(lambda prog: Program(**prog)))).validate(yaml)
