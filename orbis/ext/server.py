from flask import Flask, request, jsonify
from flask_marshmallow import Marshmallow
from orbis.controllers.base import VERSION_BANNER


def setup_api(app):
    api = Flask('orbis')
    api.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    # api.config["SQLALCHEMY_DATABASE_URI"] = app.db.engine.url
    ma = Marshmallow(api)

    @api.route('/', methods=['GET'])
    def index():
        benchmark = app.handler.get('handlers', app.plugin.benchmark, setup=True)
        return f"{VERSION_BANNER}\nServing {app.plugin.benchmark}\n{benchmark.help().output}"

    @api.route('/checkout', methods=['POST'])
    def checkout():
        benchmark_handler = app.handler.get('handlers', app.plugin.benchmark, setup=True)
        return jsonify(benchmark_handler.checkout(pid=request.form['pid'], working_dir=request.form['working_dir']))

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

    @api.route('/triplet/<vid>', methods=['GET'])
    def triplet(vid):
        benchmark_handler = app.handler.get('handlers', app.plugin.benchmark, setup=True)

        return jsonify(benchmark_handler.get_triplet(vid))

    @api.route('/manifest/<pid>', methods=['GET'])
    def manifest(pid):
        benchmark_handler = app.handler.get('handlers', app.plugin.benchmark, setup=True)

        return jsonify(benchmark_handler.get_manifest(pid))

    app.extend('api_ma', ma)
    app.extend('api', api)


def load(app):
    app.hook.register('post_setup', setup_api)

