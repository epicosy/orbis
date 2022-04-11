"""
    REST API extension
"""
import re
from inspect import signature
from typing import List, Callable
from pydoc import locate
from flask import Flask, request, jsonify
# from flask_marshmallow import Marshmallow
from orbis.controllers.base import VERSION_BANNER
from orbis.core.exc import OrbisError, CommandError, OrbisError400
from orbis.data.results import CommandData
from orbis.ext.database import Instance


def has_param(data, key: str):
    if key not in data:
        raise OrbisError400(f"This request was not properly formatted, must specify '{key}'.")


def check_tests(args):
    if 'tests' not in args:
        raise OrbisError400("Tests not provided.")


def replace_tests_name(replace_fmt, tests: List[str]) -> List[str]:
    """
        Replaces the name of the tests.

        :param replace_fmt: list with pattern and replacement value
        :param tests: list with test names
        :return:
    """

    if not isinstance(replace_fmt, list) and len(replace_fmt) != 2:
        raise OrbisError400("'replace_fmt' must be a list of two strings.")

    pattern, repl = replace_fmt

    return [re.sub(pattern, repl, t) for t in tests]


def get_method_parameters(method: Callable, replace: dict, drop: list, insert: dict):
    parameters = insert

    for p_name, p in signature(method).parameters.items():
        _type = 'any'
        default = None
        p_str = str(p)

        if p_name in drop:
            continue

        if p_name == 'args':
            parameters[p_name] = ['list', []]
            continue

        if p_name == 'kwargs':
            parameters[p_name] = ['dict', {}]
            continue

        if '=' in p_str:
            p_str, default = p_str.split('=')
            default = default.strip()

            if default == "None":
                default = None

        if ':' in p_str:
            p_str, _type = p_str.split(':')
            _type = _type.strip()
            t = locate(_type)

            if default:
                default = t(default)

        if p_name in replace:
            _type = replace[p_name]

        parameters[p_name] = [_type, default]

    return parameters


# TODO: create a flask wrapper instead
def setup_api(app):
    api = Flask('orbis')
    api.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # api.config["SQLALCHEMY_DATABASE_URI"] = app.db.engine.url
    # ma = Marshmallow(api)

    @api.route('/', methods=['GET'])
    def index():
        return f"{VERSION_BANNER}\nServing {app.plugin.benchmark}"

    @api.route('/describe', methods=['GET'])
    def describe():
        benchmark_handler = app.handler.get('handlers', app.plugin.benchmark, setup=True)
        methods = {
            'checkout': benchmark_handler.checkout,
            'build': benchmark_handler.build,
            'test': benchmark_handler.test,
            'gen_povs': benchmark_handler.gen_povs,
            'gen_tests': benchmark_handler.gen_tests,
        }

        # TODO: improve endpoints and methods to avoid this
        replace = {k: {} for k in methods.keys()}
        drop = {k: ['context', 'project'] for k in methods.keys()}
        insert = {k: {} for k in methods}
        insert['build'] = {'iid': ['str', None]}
        insert['test'] = {'iid': ['str', None]}
        insert['gen_tests'] = {'pid': ['str', None]}
        insert['gen_povs'] = {'pid': ['str', None]}
        replace['test']['tests'] = 'list'

        return {endpoint: get_method_parameters(method, replace[endpoint], drop[endpoint], insert=insert[endpoint]) for endpoint, method in methods.items()}

    @api.route('/checkout', methods=['POST'])
    def checkout():
        if request.is_json:
            data = request.get_json()
            app.log.debug(data)

            if 'vid' not in data:
                return {'error': "This request was not properly formatted, must specify 'vid'."}, 400
            try:
                response = {}
                benchmark_handler = app.handler.get('handlers', app.plugin.benchmark, setup=True)
                cmd_data = benchmark_handler.checkout(vid=data['vid'], working_dir=data.get('working_dir', None),
                                                      root_dir=data.get('root_dir', None), args=data.get('args', None))
                response.update(cmd_data)
                return jsonify(response)
            except OrbisError as oe:
                return {"error": str(oe)}, 500

        return {"error": "Request must be JSON"}, 415

    @api.route('/build', methods=['POST'])
    def build():
        if request.is_json:
            data = request.get_json()
            app.log.debug(data)
            kwargs = data.get('args', {})

            has_param(data, key='iid')

            try:
                benchmark_handler = app.handler.get('handlers', app.plugin.benchmark, setup=True)
                context = benchmark_handler.get_context(data['iid'])
                cmd_data = CommandData.get_blank()

                try:
                    response = {}
                    benchmark_handler.set(project=context.project)
                    cmd_data = benchmark_handler.build(context=context, **kwargs)
                    response.update(cmd_data.to_dict())
                    return jsonify(response)
                except (CommandError, OrbisError) as e:
                    cmd_data.failed(err_msg=str(e))
                    app.log.debug(str(e))
                    return {"error": "cmd_data.error"}, 500
                finally:
                    benchmark_handler.unset()
                    benchmark_handler.build_handler.save_outcome(cmd_data, context)
            except OrbisError as oe:
                app.log.debug(str(oe))
                return {"error": str(oe)}, 500

        return {"error": "Request must be JSON"}, 415

    @api.route('/test', methods=['POST'])
    def test():
        if request.is_json:
            data = request.get_json()
            app.log.debug(data)
            kwargs = data.get('args', {})

            if not kwargs:
                kwargs = data.copy()

            try:
                has_param(data, key='iid')
                # TODO: improve this spaghetti
                if 'iid' in kwargs:
                    del kwargs['iid']
                if 'timeout' in kwargs:
                    del kwargs['timeout']
                check_tests(kwargs)
            except OrbisError400 as oe:
                app.log.debug(str(oe))
                return {'error': str(oe)}, 400

            try:
                benchmark_handler = app.handler.get('handlers', app.plugin.benchmark, setup=True)
                context = benchmark_handler.get_context(data['iid'])
                benchmark_handler.set(project=context.project)
                timeout_margin = benchmark_handler.get_test_timeout_margin()
                timeout = data.get('timeout', timeout_margin)

                request_tests = kwargs['tests']

                if isinstance(kwargs['tests'], str):
                    request_tests = [request_tests]

                if "replace_pos_fmt" in kwargs:
                    request_tests = replace_tests_name(replace_fmt=kwargs["replace_pos_fmt"], tests=request_tests)

                if "replace_neg_fmt" in kwargs:
                    request_tests = replace_tests_name(replace_fmt=kwargs["replace_neg_fmt"], tests=request_tests)

                # Get tests
                tests = context.project.oracle.copy(request_tests)

                # If no tests, get povs
                if not tests:
                    version = context.project.get_version(sha=context.instance.sha)
                    tests = version.vuln.oracle.copy(request_tests)

                # If no tests nor povs, return error
                if not tests:
                    app.log.debug(f"Tests not found.")
                    return {'error': f"Tests not found."}, 400

                del kwargs['tests']

                cmd_data = CommandData.get_blank()

                try:
                    app.log.info(f"Running {len(tests)} tests.")
                    tests_outcome = benchmark_handler.test(context=context, tests=tests, timeout=timeout, **kwargs)
                    # TODO: fix this quick fix
                    app.log.debug(str(tests_outcome[0].to_dict()))
                    return jsonify([t.to_dict() for t in tests_outcome])
                except (OrbisError, CommandError) as e:
                    cmd_data.failed(err_msg=str(e))
                    app.log.debug(str(e))
                    return {"error": cmd_data.error}, 500
                except OrbisError400 as oe:
                    app.log.debug(str(oe))
                    return {'error': str(oe)}, 400
                finally:
                    benchmark_handler.unset()
            except OrbisError as oe:
                app.log.debug(str(oe))
                return {"error": str(oe)}, 500

        return {"error": "Request must be JSON"}, 415

    @api.route('/gen_tests', methods=['POST'])
    def gen_tests():
        if request.is_json:
            data = request.get_json()
            app.log.debug(data)
            kwargs = data.get('args', {})
            has_param(data, key='pid')

            try:
                benchmark_handler = app.handler.get('handlers', app.plugin.benchmark, setup=True)
                project = benchmark_handler.get(data['pid'])
                benchmark_handler.set(project=project)

                cmd_data = CommandData.get_blank()

                try:
                    app.log.info(f"Generating tests for project {project.name}.")
                    _ = benchmark_handler.gen_tests(project=project, **kwargs)
                    # TODO: fix this quick fix
#                    app.log.debug(str(tests_outcome[0].to_dict()))
#                    return jsonify([t.to_dict() for t in tests_outcome])
                    return jsonify(project.jsonify())
                except (OrbisError, CommandError) as e:
                    cmd_data.failed(err_msg=str(e))
                    app.log.debug(str(e))
                    return {"error": cmd_data.error}, 500
                except OrbisError400 as oe:
                    app.log.debug(str(oe))
                    return {'error': str(oe)}, 400
                finally:
                    benchmark_handler.unset()
            except OrbisError as oe:
                app.log.debug(str(oe))
                return {"error": str(oe)}, 500

        return {"error": "Request must be JSON"}, 415

    @api.route('/gen_povs', methods=['POST'])
    def gen_povs():
        if request.is_json:
            data = request.get_json()
            app.log.debug(data)
            kwargs = data.get('args', {})
            setup = kwargs.get('setup', {})
            has_param(data, key='pid')

            try:
                benchmark_handler = app.handler.get('handlers', app.plugin.benchmark, setup=True)
                project = benchmark_handler.get(data['pid'])
                benchmark_handler.set(project=project, **setup)

                cmd_data = CommandData.get_blank()

                try:
                    app.log.info(f"Generating POVs for project {project.name}.")
                    cmds = benchmark_handler.gen_povs(project=project, **kwargs)

                    return jsonify([cmd.to_dict() for cmd in cmds])
                except (OrbisError, CommandError) as e:
                    cmd_data.failed(err_msg=str(e))
                    app.log.debug(str(e))
                    return {"error": cmd_data.error}, 500
                except OrbisError400 as oe:
                    app.log.debug(str(oe))
                    return {'error': str(oe)}, 400
                finally:
                    benchmark_handler.unset()
            except OrbisError as oe:
                app.log.debug(str(oe))
                return {"error": str(oe)}, 500

        return {"error": "Request must be JSON"}, 415

    @api.route('/manifest/<pid>', methods=['GET'])
    def manifest(pid):
        try:
            benchmark_handler = app.handler.get('handlers', app.plugin.benchmark, setup=True)
            return benchmark_handler.get(pid).manifest.jsonify()
        except OrbisError as oe:
            app.log.error(str(oe))
            return {}

    @api.route('/project/<pid>', methods=['GET'])
    def project(pid):
        try:
            benchmark_handler = app.handler.get('handlers', app.plugin.benchmark, setup=True)
            return benchmark_handler.get(pid).jsonify()
        except OrbisError as oe:
            app.log.error(str(oe))
            return {}

    @api.route('/projects', methods=['GET'])
    def projects():
        try:
            benchmark_handler = app.handler.get('handlers', app.plugin.benchmark, setup=True)
            return {k: v for p in benchmark_handler.get_projects() for k, v in p.jsonify().items()}
        except OrbisError as oe:
            app.log.error(str(oe))
            return {}

    @api.route('/instances', methods=['GET'])
    def instances():
        try:
            res = app.db.query(Instance)

            if res:
                return {i.id: i.to_dict() for i in res}
            return {}
        except OrbisError as oe:
            app.log.error(str(oe))
            return {}

    @api.route('/vuln/<vid>', methods=['GET'])
    def vuln(vid):
        try:
            benchmark_handler = app.handler.get('handlers', app.plugin.benchmark, setup=True)
            return {k: v for k, v in benchmark_handler.get_vuln(vid).jsonify().items()}

        except OrbisError as oe:
            app.log.error(str(oe))

        return {}

    @api.route('/vulns', methods=['GET'])
    def vulns():
        try:
            benchmark_handler = app.handler.get('handlers', app.plugin.benchmark, setup=True)
            return {vuln.id: vuln.jsonify() for vuln in benchmark_handler.get_vulns()}
        except OrbisError as oe:
            app.log.error(str(oe))
            return {}

    @api.route('/classpath/<iid>', methods=['GET'])
    def classpath(iid):
        try:
            benchmark_handler = app.handler.get('handlers', app.plugin.benchmark, setup=True)
            if hasattr(benchmark_handler, 'classpath'):
                context = benchmark_handler.get_context(iid)
                benchmark_handler.set(project=context.project)
                return benchmark_handler.classpath(context, iid)
            else:
                return {'error': f"classpath not found."}, 400
        except OrbisError as oe:
            app.log.error(str(oe))
            return {}

    #    app.extend('api_ma', ma)
    app.extend('api', api)


def load(app):
    app.hook.register('post_setup', setup_api)
