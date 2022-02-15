"""
    REST API extension
"""
import re
from flask import Flask, request, jsonify
# from flask_marshmallow import Marshmallow
from orbis.controllers.base import VERSION_BANNER
from orbis.core.exc import OrbisError, CommandError
from orbis.data.results import CommandData


# TODO: create a flask wrapper instead

def setup_api(app):
    api = Flask('orbis')
    api.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # api.config["SQLALCHEMY_DATABASE_URI"] = app.db.engine.url
    # ma = Marshmallow(api)

    @api.route('/', methods=['GET'])
    def index():
        return f"{VERSION_BANNER}\nServing {app.plugin.benchmark}"

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

            if 'iid' not in data:
                app.log.debug("This request was not properly formatted, must specify 'iid'.")
                return {'error': "This request was not properly formatted, must specify 'iid'."}, 400

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

            if 'iid' not in data:
                app.log.debug("This request was not properly formatted, must specify 'iid'.")
                return {'error': "This request was not properly formatted, must specify 'iid'."}, 400

            if 'tests' not in kwargs:
                app.log.debug("Tests not provided.")
                return {'error': "Tests not provided."}, 400

            try:
                benchmark_handler = app.handler.get('handlers', app.plugin.benchmark, setup=True)
                context = benchmark_handler.get_context(data['iid'])
                benchmark_handler.set(project=context.project)
                timeout_margin = benchmark_handler.get_test_timeout_margin()
                timeout = data.get('timeout', timeout_margin)

                request_tests = kwargs['tests']

                if isinstance(kwargs['tests'], str):
                    request_tests = [request_tests]

                if "replace_pos_fmt" in data:
                    if not isinstance(data["replace_pos_fmt"], tuple):
                        app.log.debug("'replace_fmt' must be a tuple of two strings.")
                        return {'error': "'replace_fmt' must be a tuple of two strings."}, 400

                    request_tests = [re.sub(data["replace_pos_fmt"][0], data["replace_pos_fmt"][1], t) for t in request_tests]

                if "replace_neg_fmt" in data:
                    if not isinstance(data["replace_neg_fmt"], tuple):
                        app.log.debug("'replace_neg_fmt' must be a tuple of two strings.")
                        return {'error': "'replace_neg_fmt' must be a tuple of two strings."}, 400

                    request_tests = [re.sub(data["replace_neg_fmt"][0], data["replace_neg_fmt"][1], t) for t in request_tests]

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
                    return jsonify([t.to_dict() for t in tests_outcome])
                except (OrbisError, CommandError) as e:
                    cmd_data.failed(err_msg=str(e))
                    app.log.debug(str(e))
                    return {"error": cmd_data.error}, 500
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

    @api.route('/program/<pid>', methods=['GET'])
    def program(pid):
        try:
            benchmark_handler = app.handler.get('handlers', app.plugin.benchmark, setup=True)
            return benchmark_handler.get(pid).jsonify()
        except OrbisError as oe:
            app.log.error(str(oe))
            return {}

    @api.route('/programs', methods=['GET'])
    def programs():
        try:
            benchmark_handler = app.handler.get('handlers', app.plugin.benchmark, setup=True)
            return {k: v for p in benchmark_handler.get_projects() for k, v in p.jsonify().items()}
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

    #    app.extend('api_ma', ma)
    app.extend('api', api)


def load(app):
    app.hook.register('post_setup', setup_api)
