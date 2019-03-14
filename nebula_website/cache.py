# -*- coding: utf-8 -*-

import json
import urllib2
import time
import traceback
import logging
import gevent
from flask_caching import Cache

from nebula_website import settings


cache = Cache()

logger = logging.getLogger("nebula_website.cache")


def get_weigh(s):
    config = json.loads(s.config)
    terms = config.get('terms', [])
    for term in terms:
        if term['left']['subtype'] == 'setblacklist':
            blacklist_info = term['left']['config']
            if blacklist_info is None:
                logger.error(u'app:%s, name:%s 的策略没有设置黑名单的配置', s.app, s.name)
                continue
            return {
                'app': s.app,
                'name': s.name,
                'tags': (s.tags or '').split(','),
                'category': s.category,
                'score': s.score,
                'expire': s.endeffect,
                'remark': s.remark,
                'test': True if s.status == 'test' else False,
                'scope': term.get('scope', ''),
                'checkpoints': blacklist_info.get('checkpoints', ''),
                'checkvalue': blacklist_info.get('checkvalue', ''),
                'checktype': blacklist_info.get('checktype', ''),
                'decision': blacklist_info.get('decision', ''),
                'ttl': blacklist_info.get('ttl', 300)
            }


Strategies_Weigh = None
Strategy_Time = 0


def fetch_strategy_weigh():
    global Strategies_Weigh
    
    if Strategies_Weigh is None:
        Strategies_Weigh = dict()
    
    strategy_weighs = dict()
    url = 'http://{}:{}/nebula/strategyweigh?auth={}'.format(
        settings.WebUI_Address, settings.WebUI_Port, settings.Auth_Code)
    try:
        res = json.loads(urllib2.urlopen(url).read())
        if res and res.get('msg', '') == 'ok':
            strategies = res.get('values', [])
            for strategy in strategies:
                if not strategy:
                    continue
                name = strategy.pop('name')
                strategy_weighs[name] = strategy
    except Exception:
        logger.error("Error when fetch strategy weigh from web: %s", traceback.format_exc())
        return
    Strategies_Weigh = strategy_weighs
    print Strategies_Weigh


def strategies_weigh_worker():
    while True:
        fetch_strategy_weigh()
        gevent.sleep(60)


def get_strategy_weigh():
    """
    每次返回Strategies_Weigh之后都置空， 然后由cache保留1min, 1min之内命中cache， 之后再访问才去触发拉取
    """
    global Strategies_Weigh, Strategy_Time
    try:
        n = time.time()
        if Strategies_Weigh is None or n - Strategy_Time >= 60:
            fetch_strategy_weigh()
            Strategy_Time = n
        return Strategies_Weigh
    finally:
        Strategies_Weigh = None


Configs = None
Config_time = 0


def fetch_config():
    global Configs
    global Config_time
    
    if Configs is None:
        Configs = dict()
#    logger.debug("enter fetch config")
    configs = dict()
    url = 'http://{}:{}/platform/config?auth={}'.format(
        settings.WebUI_Address, settings.WebUI_Port, settings.Auth_Code)
    try:
        res = json.loads(urllib2.urlopen(url).read())
#        logger.debug("fetch config response:%s", res)
        if res and res.get('status', -1) == 0:
            cfs = res.get('values', [])
            for cf in cfs:
                if not cf:
                    continue
                configs[cf["key"]] = cf["value"]
#            logger.debug("fetch nebula config: %s", configs)
        if res.get("status", -1) != 0:
            logger.error("fetch nebula config fail: %s", res.get("msg"))
    except Exception:
        logger.error("Error when fetch configs from web: %s", traceback.format_exc())
        return
    Configs = configs
    Config_time = time.time()


def get_config(key, default_value):
    """
    当拿不到config, 应该返回默认值， 处理情况等同于没有config配置项的情况。相当于一种约定的熔断方式
    """

    global Configs, Config_time
        
    n = time.time()
#    logger.debug("configs: %s, config_time:%s", Configs, Config_time)
    if Configs is None or n - Config_time >= 600:
        fetch_config()
    # todo if config is broken

#    logger.debug("fetch configs: %s", Configs)
    if Configs is None:
        return default_value
    return Configs.get(key, default_value)


def task_exception_handler(greenlet):
    logger.warn('{0}'.format(greenlet.exception))


def get_configs():
    """
    每次返回configs之后都置空， 然后由cache保留10min, 10min之内命中cache， 之后再访问才去触发拉取
    """    
    global Configs, Config_time
    n = time.time()
    if Configs is None or n - Config_time >= 600:
        fetch_config()

    if Configs:
        return Configs
    else:
        logger.error("Can't fetch config from web")
        return dict()


def update_web_config():
    fetch_config()
    gs = cache.app.config["SCHEDULER_OBJ"]
    jobs = cache.app.config["JOBS"]
    Service_Name = jobs[1]['id']
    j = gs.get_job(Service_Name)
    new_interval = int(get_config("alerting.delivery_interval", '60')) * 60
    if int(j.trigger.interval.total_seconds()) != new_interval:
        logger.info("%s old next run time: %s", Service_Name, j.next_run_time)
        gs.reschedule_job(Service_Name, trigger='interval', seconds=new_interval, timezone="UTC")
        logger.info("%s new next run time: %s", Service_Name, j.next_run_time)
