# -*- coding: utf-8 -*-
import greenify;greenify.greenify()
from gevent import monkey;monkey.patch_all()
import gevent
import logging
logging.basicConfig(level=logging.DEBUG)

from flask import Flask
from flask_apscheduler import APScheduler
from apscheduler.schedulers.gevent import GeventScheduler

from nebula_website.views import db_stat, logquery
from nebula_website.managers.logquery import LogQueryServer
from nebula_website import utils, settings
from nebula_website.models import db
from nebula_website.cache import cache,fetch_config, get_config, update_web_config#,strategies_weigh_worker
from nebula_website.services.notice_mail import Service_Name, send_alarm_task

app = Flask(__name__)

nebula_website_settings = dict( (_, getattr(settings, _)) for _ in dir(settings)
                                if not _.startswith("_"))

app.config.update(nebula_website_settings)
app.logger.setLevel(logging.DEBUG if nebula_website_settings["DEBUG"] else logging.INFO)

utils.init_env("nebula.web.db_stat_query")

app.logger.info("DB Stat Query Web App is Starting..")
app.register_blueprint(db_stat.mod,url_prefix='/platform')
# app.register_blueprint(logquery.mod) #note:注释本接口， 此接口已经由java-web实现并且运行time：2018-10-24

cache.init_app(app)
cache.app = app
db.init_app(app)
db.app = app

lq_server = LogQueryServer(app)
lq_server.start()

fetch_config()
gs = GeventScheduler()

scheduler_configs = dict(
    JOBS = [
        {
            'id': "fetch_config",
            'func': update_web_config,
            'trigger': 'interval',
            'minutes': 1,
            'timezone': 'UTC'
        },
        {
            'id': Service_Name,
            'func':send_alarm_task,
            'args':(nebula_website_settings["Notice_RPC_Template_Path"],),
            'trigger': 'interval',
            'minutes': int(get_config("alerting.delivery_interval", '60')),
            'timezone': 'UTC'
        }
    ],
    SCHEDULER_API_ENABLED = True,
    SCHEDULER_OBJ = gs
)
app.config.update(scheduler_configs)
scheduler = APScheduler(gs, app)
scheduler.start()
#nm_server = NoticeMailServer(app, nebula_website_settings["Notice_RPC_Template_Path"])
#nm_server.start()
