import re
from pathlib import Path
from typing import Union, List, Dict, Any, AnyStr

from orbis.data.results import CommandData
from orbis.core.exc import OrbisError
from orbis.handlers.benchmark import BenchmarkHandler


class CGCRepair(BenchmarkHandler):
    """
        Handler for interacting locally with the CGCRepair benchmark
    """
    class Meta:
        label = 'cgcrepair'

    @staticmethod
    def match_id(out: str) -> Union[str, None]:
        match = re.search('Id: (\d{1,4})', out)
        if match:
            return match.group(1)

        return None

    @staticmethod
    def match_path(out: str) -> Union[str, None]:
        match = re.search('Working directory: (.*)', out)
        if match:
            return match.group(1)

        return None

    @staticmethod
    def match_build(out: str) -> Union[str, None]:
        match = re.search('Build path: (.*)', out)

        if match:
            return match.group(1)

        return None

    def help(self) -> CommandData:
        return super().__call__(cmd_str=f"cgcrepair --help", raise_err=True)

    def get_program(self, pid: str, **kwargs) -> Dict[str, Any]:
        response = {}
        cmd_data = super().__call__(cmd_str=f"cgcrepair database metadata --cid {pid}", raise_err=False, **kwargs)

        if not cmd_data.error:
            _, name, vulns, manifest = cmd_data.output.splitlines()
            vid, main, _, related = vulns.split('|')

            response = {'id': pid, 'name': name, 'manifest': manifest.split(' '), 'tests': {},
                        'vuln': {'id': vid, 'cwe': main, 'related': related.split(';') if related else None}}

            tests_cmd = self(cmd_str=f"cgcrepair -vb task tests --cid {pid}", raise_err=False, **kwargs)

            if not tests_cmd.error:
                pos_tests, neg_tests = tests_cmd.output.splitlines()
                response['tests'] = {'pos': pos_tests.split(' '), 'neg': neg_tests.split(' ')}

        return response

    def get_vulns(self) -> Dict[str, Any]:
        vulns_data = super().__call__(cmd_str=f"cgcrepair database vulns -w", raise_err=True)
        vulns = {}

        for line in vulns_data.output.strip().split('\n'):
            cwe, pid, program, _id, related = line.split('\t')
            vulns[_id] = {'id': _id, 'cwe': cwe, 'pid': pid, 'program': program}

        return vulns

    def get_vuln(self, vid: str, **kwargs) -> Dict[str, Any]:
        vuln_data = super().__call__(cmd_str=f"cgcrepair database vulns --vid {vid}", raise_err=True)

        cwe, pid, program, vid, related = vuln_data.output.split(' ')

        return {'id': vid, 'cwe': cwe, 'pid': pid, 'program': program}

    def get_programs(self, **kwargs) -> Dict[str, Any]:
        cmd_data = super().__call__(cmd_str=f"cgcrepair database list --metadata", raise_err=True, **kwargs)

        programs = sorted([line.strip().split(' | ')[0] for line in cmd_data.output.split('\n') if line])
        results = {}

        for cid in programs:
            results[cid] = self.get_program(cid)

        return results

    def get_manifest(self, pid: str, **kwargs) -> Dict[str, List[AnyStr]]:
        manifest_cmd = self(cmd_str=f"cgcrepair -vb corpus --cid {pid} manifest", raise_err=True, **kwargs)

        return {'manifest': manifest_cmd.output.splitlines()}

    def checkout(self, pid: str, working_dir: str = None, root_dir: str = None, **kwargs) -> Dict[str, Any]:
        cmd_str = f"cgcrepair -vb corpus --cid {pid} checkout -rp"

        if working_dir:
            cmd_str = f"{cmd_str} -wd {working_dir}"
        elif root_dir:
            cmd_str = f"{cmd_str} -rd {root_dir}"

        cmd_data = super().__call__(cmd_str=cmd_str, **kwargs)

        working_dir = self.match_path(cmd_data.output)
        iid = self.match_id(cmd_data.output)

        if iid is None:
            id_file = Path(working_dir, '.instance_id')

            if id_file.exists():
                iid = id_file.open(mode='r').readlines()[0]
            else:
                raise OrbisError("Could not match ID")

        response = cmd_data.to_dict()
        response.update({'iid': iid, 'working_dir': working_dir})

        return response

    def make(self, iid: str, **kwargs) -> CommandData:
        return super().__call__(cmd_str=f"cgcrepair -vb instance --id {iid} make", **kwargs)

    def compile(self, iid: str, **kwargs) -> Dict[str, Any]:
        #if 'args' in kwargs:
        #    kwargs['args'] += " 2>&1"
        cmd_data = super().__call__(cmd_str=f"cgcrepair -vb instance --id {iid} compile", **kwargs)
        build_dir = self.match_build(cmd_data.output)

        response = cmd_data.to_dict()
        response.update({'iid': iid, 'build': build_dir})

        return response

    def test(self, iid: str, **kwargs) -> CommandData:
        if 'args' in kwargs:
            kwargs['args'] += " 2>&1"
        return super().__call__(cmd_str=f"cgcrepair -vb instance --id {iid} test", **kwargs)


def load(nexus):
    nexus.handler.register(CGCRepair)
