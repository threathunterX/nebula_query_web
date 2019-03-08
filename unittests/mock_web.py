# -*- coding: utf-8 -*-

import greenify;greenify.greenify()
from gevent import monkey;monkey.patch_all()
import logging
logging.basicConfig(level=logging.DEBUG,format=  '%(asctime)s\tFile \"%(filename)s\",line %(lineno)s\t%(levelname)s: %(message)s')

from flask import Flask
from flask_cors import CORS

from nebula_website.mockserver import logquery
from nebula_website import utils, settings

app = Flask(__name__)
CORS(app)

nebula_website_settings = dict( (_, getattr(settings, _)) for _ in dir(settings)
                                if not _.startswith("_"))
app.config.update(nebula_website_settings)

logger = utils.init_env("nebula.web.mockserver")

logger.info("Mock Web App is Starting..")
app.register_blueprint(logquery.mod)


