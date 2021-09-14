from flask import Flask, request, jsonify
#from flask_marshmallow import Marshmallow
from orbis.controllers.base import VERSION_BANNER
from orbis.core.exc import OrbisError


def setup_api(app):
    api = Flask('orbis')
    api.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    # api.config["SQLALCHEMY_DATABASE_URI"] = app.db.engine.url
    #ma = Marshmallow(api)
    benchmark_handler = app.handler.get('handlers', app.plugin.benchmark, setup=True)

    @api.route('/', methods=['GET'])
    def index():
        return f"{VERSION_BANNER}\nServing {app.plugin.benchmark}\n{benchmark_handler.help().output}"

    @api.route('/checkout', methods=['POST'])
    def checkout():
        if request.is_json:
            data = request.get_json()

            if 'pid' not in data:
                return {'error': "This request was not properly formatted, must specify 'pid'."}, 400
            try:
                return jsonify(benchmark_handler.checkout(pid=data['pid'], working_dir=data.get('working_dir', None),
                                                          root_dir=data.get('root_dir', None),
                                                          args=data.get('args', None)))
            except OrbisError as oe:
                return {"error": str(oe)}, 500

        return {"error": "Request must be JSON"}, 415

    @api.route('/compile', methods=['POST'])
    def compile():
        if request.is_json:
            data = request.get_json()

            if 'iid' not in data:
                return {'error': "This request was not properly formatted, must specify 'iid'."}, 400

            try:
                return jsonify(benchmark_handler.compile(iid=data['iid'], args=data.get('args', None)))
            except OrbisError as oe:
                return {"error": str(oe)}, 500

        return {"error": "Request must be JSON"}, 415

    @api.route('/test', methods=['POST'])
    def test():
        if request.is_json:
            data = request.get_json()

            if 'iid' not in data:
                return {'error': "This request was not properly formatted, must specify 'iid'."}, 400

            try:
                return jsonify(benchmark_handler.test(iid=data['iid'], args=data.get('args', None)))
            except OrbisError as oe:
                return {"error": str(oe)}, 500

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

#    app.extend('api_ma', ma)
    app.extend('api', api)


def load(app):
    app.hook.register('post_setup', setup_api)
