# -*- coding: utf-8 -*-

import greenify
greenify.greenify()
from gevent import monkey;monkey.patch_all()
import logging
logging.basicConfig(level=logging.DEBUG,format=  '%(asctime)s\tFile \"%(filename)s\",line %(lineno)s\t%(levelname)s: %(message)s')
from flask import Flask

from nebula_website.views import data_bus, incident_stat, system_stats, variable
from nebula_website import utils, settings

app = Flask(__name__)

nebula_website_settings = dict( (_, getattr(settings, _)) for _ in dir(settings)
                                if not _.startswith("_"))
app.config.update(nebula_website_settings)

logger = utils.init_env("nebula.web.stat_query")

logger.info("Query Stat Web App is Starting..")
app.register_blueprint(data_bus.mod, url_prefix='/platform')
app.register_blueprint(incident_stat.mod, url_prefix='/platform')
# app.register_blueprint(system_stats.mod)
app.register_blueprint(variable.mod, url_prefix='/platform')

logger.info("Query Stat Web App has started.")


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9999, debug=False)

