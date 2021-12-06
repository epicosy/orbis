from datetime import datetime

from flask import Flask, request, jsonify
# from flask_marshmallow import Marshmallow
from orbis.controllers.base import VERSION_BANNER
from orbis.core.exc import OrbisError, CommandError
from orbis.data.results import CommandData


def setup_api(app):
    api = Flask('orbis')
    api.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    # api.config["SQLALCHEMY_DATABASE_URI"] = app.db.engine.url
    # ma = Marshmallow(api)
    benchmark_handler = app.handler.get('handlers', app.plugin.benchmark, setup=True)

    @api.route('/', methods=['GET'])
    def index():
        return f"{VERSION_BANNER}\nServing {app.plugin.benchmark}"

    @api.route('/checkout', methods=['POST'])
    def checkout():
        if request.is_json:
            data = request.get_json()

            if 'vid' not in data:
                return {'error': "This request was not properly formatted, must specify 'vid'."}, 400
            try:
                response = {}
                checkout_handler = app.handler.get('handlers', 'checkout', setup=True)
                cmd_data = benchmark_handler.checkout(vid=data['vid'], working_dir=data.get('working_dir', None),
                                                      handler=checkout_handler, root_dir=data.get('root_dir', None),
                                                      args=data.get('args', None))
                response.update(cmd_data)
                return jsonify(response)
            except OrbisError as oe:
                return {"error": str(oe)}, 500

        return {"error": "Request must be JSON"}, 415

    @api.route('/build', methods=['POST'])
    def build():
        if request.is_json:
            data = request.get_json()

            if 'iid' not in data:
                return {'error': "This request was not properly formatted, must specify 'iid'."}, 400

            try:
                context = benchmark_handler.get_context(data['iid'])
                build_handler = app.handler.get('handlers', 'build', setup=True)
                # cmd_data = CommandData.get_blank()

                try:
                    response = {}
                    benchmark_handler.set()
                    cmd_data, build_dir = benchmark_handler.build(context=context, handler=build_handler,
                                                                  args=data.get('args', None))
                    response.update(cmd_data.to_dict())
                    return jsonify(response)
                except (CommandError, OrbisError) as e:
                    # cmd_data.failed(err_msg=str(e))
                    # return {"error": cmd_data.error}, 500
                    return {"error": "cmd_data.error"}, 500
                finally:
                    benchmark_handler.unset()
                    build_handler.save_outcome("cmd_data", context)
            except OrbisError as oe:
                return {"error": str(oe)}, 500

        return {"error": "Request must be JSON"}, 415

    @api.route('/test', methods=['POST'])
    def test():
        if request.is_json:
            data = request.get_json()

            if 'iid' not in data:
                return {'error': "This request was not properly formatted, must specify 'iid'."}, 400

            if not ('tests' in data or 'povs' in data):
                return {'error': "Tests and povs not provided."}, 400

            try:
                test_handler = app.handler.get('handlers', 'test', setup=True)
                context = benchmark_handler.get_context(data['iid'])
                timeout_margin = benchmark_handler.get_test_timeout_margin()
                timeout = data.get('timeout', timeout_margin)
                
                if 'tests' in data:
                    tests = benchmark_handler.get_oracle(context.program, data.get('tests', None))
                else:
                    tests = benchmark_handler.get_oracle(context.program, data.get('povs', None), pov=True)
                
                cmd_data = CommandData.get_blank()

                try:
                    if data.get('tests', None):
                        app.log.info(f"Running {len(tests)} tests.")

                    if data.get('povs', None):
                        app.log.info(f"Running {len(povs)} povs.")

                    cmd_data = benchmark_handler.test(context=context, handler=test_handler, tests=tests, 
                                                      args=data.get('args', None), timeout=timeout)
                    return jsonify(cmd_data.to_json())
                except (OrbisError, CommandError) as e:
                    cmd_data.failed(err_msg=str(e))
                    return {"error": cmd_data.error}, 500
                finally:
                    benchmark_handler.unset()
            except OrbisError as oe:
                return {"error": str(oe)}, 500

        return {"error": "Request must be JSON"}, 415

    @api.route('/manifest/<pid>', methods=['GET'])
    def manifest(pid):
        try:
            return benchmark_handler.get(pid).manifest.jsonify()
        except OrbisError as oe:
            app.log.error(str(oe))
            return {}

    @api.route('/program/<pid>', methods=['GET'])
    def program(pid):
        try:
            return benchmark_handler.get(pid).jsonify()
        except OrbisError as oe:
            app.log.error(str(oe))
            return {}

    @api.route('/programs', methods=['GET'])
    def programs():
        try:
            return {k: v for p in benchmark_handler.all() for k, v in p.jsonify().items()}
        except OrbisError as oe:
            app.log.error(str(oe))
            return {}

    @api.route('/vuln/<vid>', methods=['GET'])
    def vuln(vid):
        try:
            for p in benchmark_handler.all():
                for k, v in p.manifest.jsonify().items():
                    if k == vid:
                        return {k: v}

        except OrbisError as oe:
            app.log.error(str(oe))

        return {}

    @api.route('/vulns', methods=['GET'])
    def vulns():
        try:
            return {k: v for p in benchmark_handler.all() for k, v in p.manifest.jsonify().items()}
        except OrbisError as oe:
            app.log.error(str(oe))
            return {}

    #    app.extend('api_ma', ma)
    app.extend('api', api)


def load(app):
    app.hook.register('post_setup', setup_api)
