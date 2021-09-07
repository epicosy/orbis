from flask import Flask, request, jsonify
from flask_marshmallow import Marshmallow
from orbis.controllers.base import VERSION_BANNER


def setup_api(app):
    api = Flask('orbis')
    api.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    # api.config["SQLALCHEMY_DATABASE_URI"] = app.db.engine.url
    ma = Marshmallow(api)
    benchmark_handler = app.handler.get('handlers', app.plugin.benchmark, setup=True)

    @api.route('/', methods=['GET'])
    def index():
        return f"{VERSION_BANNER}\nServing {app.plugin.benchmark}\n{benchmark_handler.help().output}"

    @api.route('/checkout', methods=['POST'])
    def checkout():
        if request.is_json:
            data = request.get_json()

            if not 'pid' in data:
                return {'error': "Resquest must specify a pid"}, 415

            return jsonify(benchmark_handler.checkout(pid=data['pid'], working_dir=data.get('working_dir', None)))

        return {"error": "Request must be JSON"}, 415


    @api.route('/compile', methods=['POST'])
    def compile():
        if request.is_json:
            data = request.get_json()

            if not 'iid' in data:
                return {'error': "Resquest must specify a iid"}, 415

            cmd_data = benchmark_handler.compile(iid=data['iid'], args=data.get('args', None))

            return jsonify(cmd_data.to_dict())

        return {"error": "Request must be JSON"}, 415

    @api.route('/test', methods=['POST'])
    def test():
        if request.is_json:
            data = request.get_json()

            if not 'iid' in data:
                return {'error': "Resquest must specify a iid"}, 415

            cmd_data = benchmark_handler.test(iid=data['iid'], args=data.get('args', None))

            return jsonify(cmd_data.to_dict())

        return {"error": "Request must be JSON"}, 415

    @api.route('/manifest/<pid>', methods=['GET'])
    def manifest(pid):
        return jsonify(benchmark_handler.get_manifest(pid))

    @api.route('/program/<pid>', methods=['GET'])
    def program(pid):
        return jsonify(benchmark_handler.get_program(pid))

    @api.route('/programs', methods=['GET'])
    def programs():
        return jsonify(benchmark_handler.get_programs())

    @api.route('/vuln/<vid>', methods=['GET'])
    def vuln(vid):
        return jsonify(benchmark_handler.get_vuln(vid))

    @api.route('/vulns', methods=['GET'])
    def vulns():
        return jsonify(benchmark_handler.get_vulns())

    app.extend('api_ma', ma)
    app.extend('api', api)


def load(app):
    app.hook.register('post_setup', setup_api)

