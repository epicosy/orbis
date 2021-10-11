import json
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
        cmd_data = super().__call__(cmd_str=f"cgcrepair database metadata --cid {pid}", raise_err=False, **kwargs)

        if not cmd_data.error:
            try:
                return json.loads(cmd_data.output.replace("'", '"'))
            except json.decoder.JSONDecodeError as jde:
                self.app.log.error(str(jde))
                return {}

        return {}

    def get_vulns(self) -> Dict[str, Any]:
        vulns_data = super().__call__(cmd_str=f"cgcrepair database vulns", raise_err=True)

        if not vulns_data.error:
            try:
                response = {}
                print(vulns_data.output)
                for line in vulns_data.output.splitlines():
                    program = json.loads(line.replace("'", '"'))
                    pid = program['id']
                    del program['id']
                    response[pid] = program

                return response
            except json.decoder.JSONDecodeError as jde:
                self.app.log.error(str(jde))
                return {}

        return {}

    def get_vuln(self, vid: str, **kwargs) -> Dict[str, Any]:
        vuln_data = super().__call__(cmd_str=f"cgcrepair database vulns --vid {vid}", raise_err=True)

        if not vuln_data.error:
            try:
                return json.loads(vuln_data.output.replace("'", '"'))
            except json.decoder.JSONDecodeError as jde:
                self.app.log.error(str(jde))
                return {}

        return {}

    def get_programs(self, **kwargs) -> Dict[str, Any]:
        cmd_data = super().__call__(cmd_str=f"cgcrepair database metadata", raise_err=False, **kwargs)

        if not cmd_data.error:
            try:
                response = {}

                for line in cmd_data.output.splitlines():
                    program = json.loads(line.replace("'", '"'))
                    pid = program['id']
                    del program['id']
                    response[pid] = program

                return response
            except json.decoder.JSONDecodeError as jde:
                self.app.log.error(str(jde))
                return {}

        return {}

    def get_manifest(self, pid: str, **kwargs) -> Dict[str, List[AnyStr]]:
        manifest_cmd = self(cmd_str=f"cgcrepair corpus --cid {pid} manifest", raise_err=True, **kwargs)

        return {'manifest': manifest_cmd.output.splitlines()}

    def checkout(self, pid: str, working_dir: str = None, root_dir: str = None, **kwargs) -> Dict[str, Any]:
        cmd_str = f"cgcrepair corpus --cid {pid} checkout -rp"

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
        return super().__call__(cmd_str=f"cgcrepair instance --id {iid} make", **kwargs)

    def compile(self, iid: str, **kwargs) -> Dict[str, Any]:
        cmd_data = super().__call__(cmd_str=f"cgcrepair instance --id {iid} compile", **kwargs)
        build_dir = self.match_build(cmd_data.output)

        response = cmd_data.to_dict()
        response.update({'iid': iid, 'build': build_dir})

        return response

    def test(self, iid: str, **kwargs) -> Dict[str, Any]:
        cmd_data = super().__call__(cmd_str=f"cgcrepair instance --id {iid} test", **kwargs)
        return cmd_data.to_dict()


def load(nexus):
    nexus.handler.register(CGCRepair)
