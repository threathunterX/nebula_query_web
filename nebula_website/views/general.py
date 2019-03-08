# -*- coding: utf-8 -*-

from flask import Blueprint, current_app, jsonify
from flask_swagger import swagger

mod = Blueprint("general", __name__)


@mod.route("/api/profile", methods=["GET"])
def spec():
    swag = swagger(current_app._get_current_object())
    return jsonify(swag)
