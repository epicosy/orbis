import re
from typing import Union, List, Tuple, Dict, Any, AnyStr

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

    def get_program(self, pid: str, **kwargs) -> Dict[str, Any]:
        cmd_data = super().__call__(cmd_str=f"cgcrepair database metadata --cid {pid}", raise_err=True, **kwargs)
        _, name, vulns, manifest = cmd_data.output.splitlines()
        vid, main, _, related = vulns.split('|')

        if related:
            related = related.split(';')
        else:
            related = None

        return {'pid': pid, 'name': name, 'manifest': manifest.split(' '), 'vuln': {'id': vid, 'cwe': main,
                                                                                    'related': related}}

    def get_vulns(self) -> Dict[str, Any]:
        vulns_data = super().__call__(cmd_str=f"cgcrepair database vulns -w", raise_err=True)
        vulns = {}

        for line in vulns_data.output.strip().split('\n'):
            cwe, pid, program, _id, related = line.split('\t')
            vulns[_id] = {'id': _id, 'cwe': cwe, 'pid': pid, 'program': program}

        return vulns

    def get_vuln(self, vid: str) -> Dict[str, Any]:
        vuln_data = super().__call__(cmd_str=f"cgcrepair database vulns --vid {vid}", raise_err=True)

        cwe, pid, program, vid, related = vuln_data.output.split('\t')

        return {'vid': vid, 'cwe': cwe, 'pid': pid, 'program': program}

    def prepare(self, program: Program, **kwargs) -> CommandData:
        checkout_cmd = self.checkout(program.vuln.pid, str(program.working_dir), **kwargs)
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

    def get_triplet(self, vid: Program, **kwargs) -> Dict[str, Any]:
        tests_cmd = self(cmd_str=f"cgcrepair -vb task triplet --vid {vid}", raise_err=True, **kwargs)
        cid, pos_tests, neg_tests = tests_cmd.output.splitlines()

        return {'cid': cid, 'pos_tests': pos_tests.split(' '), 'neg_tests': neg_tests.split(' ')}

    def get_manifest(self, pid: str, **kwargs) -> Dict[str, List[AnyStr]]:
        manifest_cmd = self(cmd_str=f"cgcrepair -vb corpus --cid {pid} manifest", raise_err=True, **kwargs)

        return {'manifest': manifest_cmd.output.splitlines()}

    def checkout(self, pid: str, working_dir: str, **kwargs) -> Dict[str, Any]:
        cmd_data = super().__call__(cmd_str=f"cgcrepair -vb corpus --cid {pid} checkout -wd {working_dir} -rp", **kwargs)
        iid = self.match_id(cmd_data.output)
        response = cmd_data.to_dict()
        response.update({'iid': iid})

        return response

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
