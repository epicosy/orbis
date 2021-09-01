import re
from pathlib import Path
from typing import Union, List, Tuple

from orbis.data.results import CommandData, Program, Vulnerability
from orbis.core.exc import OrbisError, CommandError
from orbis.handlers.benchmark import BenchmarkHandler


class CGCRepair(BenchmarkHandler):
    """
        Handler for interacting locally with the CGCRepair benchmark
    """
    class Meta:
        label = 'cgcrepair'

    @staticmethod
    def match_id(out: str) -> Union[str, None]:
        match = re.search('id (\d{1,4})', out)
        if match:
            return match.group(1)

        return None

    def help(self) -> CommandData:
        return super().__call__(cmd_str=f"cgcrepair --help", raise_err=True)

    def get(self, vuln: str, **kwargs) -> Program:
        if vuln not in self.vulns:
            raise OrbisError(f"{vuln} not found")

        working_dir = self.get_working_dir(vuln, randomize=True)
        root_dir = working_dir / vuln

        return Program(name=self.vulns[vuln].program, working_dir=working_dir, root=root_dir, source=root_dir / 'src',
                       lib=root_dir / 'lib', include=root_dir / 'include', vuln=self.vulns[vuln])

    def load(self, **kwargs):
        if not self.vulns:
            vulns_data = super().__call__(cmd_str=f"cgcrepair database vulns -w", raise_err=True, **kwargs)

            for line in vulns_data.output.strip().split('\n'):
                cwe, pid, program, _id, related = line.split('\t')
                self.vulns[_id] = Vulnerability(id=_id, cwe=cwe, pid=pid, program=program, exploit=_id)

    def prepare(self, program: Program, **kwargs) -> CommandData:
        checkout_cmd = self.checkout(program, **kwargs)
        program['id'] = self.match_id(checkout_cmd.output)
        self.app.log.warning(str(program['id']))

        if program['id'] is None:
            id_file = program.working_dir / '.instance_id'

            if id_file.exists():
                program['id'] = id_file.open(mode='r').readlines()[0]
            else:
                raise OrbisError("Could not match ID")

        self.app.log.info(f"Prepared {program.name} instance with ID: {program['id']}")
        return checkout_cmd

    def get_programs(self, **kwargs):
        try:
            cmd_data = super().__call__(cmd_str=f"cgcrepair database list --metadata --name", raise_err=True, **kwargs)

            return sorted([line.strip() for line in cmd_data.output.split('\n') if line])

        except CommandError as ce:
            self.app.log.warning(str(ce))
            return []

    def get_triplet(self, program: Program, **kwargs) -> Tuple[str, List[str], Union[str, List[str]]]:
        tests_cmd = self(cmd_str=f"cgcrepair -vb task triplet --vid {program.vuln.id}", raise_err=True, **kwargs)
        cid, pos_tests, neg_tests = tests_cmd.output.splitlines()

        return cid, pos_tests.split(' '), neg_tests.split(' ')

    def get_manifest(self, program: Program, **kwargs) -> List[Path]:
        manifest_cmd = self(cmd_str=f"cgcrepair -vb corpus --cid {program['cid']} manifest", raise_err=True, **kwargs)
        files = manifest_cmd.output.splitlines()

        return [Path(file) for file in files if file != '']

    def checkout(self, program: Program, **kwargs) -> CommandData:
        return super().__call__(cmd_str=f"cgcrepair -vb corpus --cid {program['cid']} checkout -wd {program.working_dir} -rp",
                                **kwargs)

    def make(self, program: Program, **kwargs) -> CommandData:
        return super().__call__(cmd_str=f"cgcrepair -vb instance --id {program['id']} make", **kwargs)

    def compile(self, program: Program, **kwargs) -> CommandData:
        if 'args' in kwargs:
            kwargs['args'] += " 2>&1"
        return super().__call__(cmd_str=f"cgcrepair -vb instance --id {program['id']} compile", **kwargs)

    def test(self, program: Program, **kwargs) -> CommandData:
        if 'args' in kwargs:
            kwargs['args'] += " 2>&1"
        return super().__call__(cmd_str=f"cgcrepair -vb instance --id {program['id']} test", **kwargs)


def load(nexus):
    nexus.handler.register(CGCRepair)
