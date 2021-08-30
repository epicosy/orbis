from flask import Flask, request, jsonify
from flask_marshmallow import Marshmallow


def setup_api(app):
    api = Flask('orbis')
    api.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    # api.config["SQLALCHEMY_DATABASE_URI"] = app.db.engine.url
    ma = Marshmallow(api)

    @api.route('/compile', methods=['POST'])
    def compile():
        benchmark_handler = app.handler.get('handlers', app.plugin.benchmark, setup=True)
        program = benchmark_handler.get(vuln=request.form['vuln'])
        cmd_data = benchmark_handler.compile(program=program, args=request.form['args'])

        return jsonify(cmd_data.to_dict())

    @api.route('/test', methods=['GET'])
    def test():
        benchmark_handler = app.handler.get('handlers', app.plugin.benchmark, setup=True)
        program = benchmark_handler.get(vuln=request.form['vuln'])
        cmd_data = benchmark_handler.test(program=program, args=request.form['args'])

        return jsonify(cmd_data.to_dict())

    app.extend('api_ma', ma)
    app.extend('api', api)


def load(app):
    app.hook.register('post_setup', setup_api)

