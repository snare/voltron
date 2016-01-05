import json

from flask import Flask, request, Response
from flask_restful import Resource, Api

import voltron

app = Flask(__name__)
api = Api(app)


class ConfigAPI(Resource):
    def get(self):
        return Response(json.dumps(voltron.config.to_dict()), status=200, mimetype='application/json')

    def post(self):
        voltron.config.update(request.json)
        voltron.config.save()
        return self.get()


api.add_resource(ConfigAPI, '/config')
