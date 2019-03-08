# -*- coding: utf-8 -*-

import logging
import sys
from datetime import datetime
import click

from threathunter_common.redis.redisctx import RedisCtx
from threathunter_common.event import Event
from threathunter_common.util import millis_now

from nebula_website import babel, settings
from .utils import dict_merge, get_hour_strs_fromtimestamp

is_debug = False
logger = None
DEBUG_PREFIX = "==============="


@click.group()
@click.option('--debug', '-d', is_flag=True, help="debug switch")
def OfflineBabelQuery(debug):
    global is_debug
    if debug:
        is_debug = True
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig()


@OfflineBabelQuery.command()
@click.option('--count', "-c", default=100, help="key's limit")
@click.option("--key", "-k", help="key to query")
@click.option("--dimension", "-i", help="key's dimension to query")
@click.option("--timestamp", "-t", type=int, help="timestamp to query")
@click.option("--var_list", "-v", type=str, help="variables to query")
def key_stat(count, key, dimension, timestamp, var_list):
    global logger
    logger = init_env("offline.query.keystat")
    
    data = dict()
    data['app'] = 'nebula'
    data["key"] = key
    data["count"] = count
    data["var_list"] = var_list.split(",")
    data["dimension"] = dimension
    data["timestamp"] = timestamp

    logger.debug(DEBUG_PREFIX+u"查询的时间是%s", datetime.fromtimestamp(int(timestamp)/1000.0)) 
    req = Event("nebula", "offlinekeystatquery", key, millis_now(), data)
    KeyStatClient = babel.get_offline_keystat_query_client()
    response = KeyStatClient.send(req, key, block=False, timeout=5)
    if response[0] and isinstance(response[1], list):
        if isinstance(response[1], list):
            result = dict()
            for r in response[1]:
                logger.debug(DEBUG_PREFIX+"返回的一个event:%s", r)
                result = dict_merge(result, r.property_values.get("result", {}) or dict())
        else:
            result = response[1].property_values.get("result", {})
        logger.debug(DEBUG_PREFIX+"有返回的结果是:%s, 返回的结果是%s", response, result)
    else:
        logger.debug(DEBUG_PREFIX+"当前没有事件..., 返回的是%s", response)


@OfflineBabelQuery.command()
@click.option('--count', "-c", default=100, help="first search key limit")
@click.option("--topcount", default=1, help="second search top's limit")
@click.option("--key_variable", "-k", type=str, help="first search key's variable")
@click.option("--key_dimension", "-d", type=str, help="first search key's dimension")
@click.option("--var_list", "-v", type=str, help="variables need return directly")
@click.option("--merge_list", "-m", type=str, help="variables need merge every key's data")
@click.option("--timestamp", "-t", help="timestamp to query")
def baseline(count, topcount, key_variable, key_dimension,var_list, merge_list, timestamp):
    global logger
    logger = init_env("offline.query.baseline")
    data = dict()
    data['count'] = count
    data['topCount'] = topcount
    data['key_variable'] = [key_variable,]
    data['key_dimension'] = key_dimension
    data['var_list'] = var_list.split(",")
    data['merge_list'] = merge_list.split(",")
    data["timestamp"] = int(timestamp)
    
    req = Event("nebula", "offline_baselinekeystatquery", "", millis_now(), data)
    BaselineClient = babel.get_offline_baseline_query_client()
    response = BaselineClient.send(req, "", timeout=10)
    if response[0]:
        if isinstance(response[1], list):
            result = dict()
            for r in response[1]:
                logger.debug(DEBUG_PREFIX+"返回的一个event:%s", r)
                result = dict_merge(result, r.property_values.get("result", {}) or dict())
        else:
            result = response[1].property_values.get("result", {})
        logger.debug(DEBUG_PREFIX+"有返回的结果是:%s, 返回的结果是%s", response, result)
    else:
        logger.debug(DEBUG_PREFIX+"当前没有事件..., 返回的是%s", response)


@OfflineBabelQuery.command()
@click.option("--key", "-k", default="",type=str,help="key to query")
@click.option("--dimension", "-i", help="key's dimension to query")
@click.option("--var_list", "-v", type=str, help="variables need return directly")
@click.option("--fromtime", "-f", type=int, help="query start timestamp, ex.1486620000000")
@click.option("--endtime", "-e", type=int, help="query end timestamp, ex.1494309599999")
def continuous(key, dimension, var_list, fromtime, endtime):
    global logger
    logger = init_env("offline.query.continuous")
    
    ts = int(fromtime) / 1000.0
    end_ts = int(endtime) / 1000.0
    now = millis_now()
    now_in_hour_start = now / 1000 / 3600 * 3600
    logger.debug(DEBUG_PREFIX+u"查询的时间范围是%s ~ %s", datetime.fromtimestamp(ts), datetime.fromtimestamp(end_ts))
    if end_ts >= now_in_hour_start:
        timestamps = get_hour_strs_fromtimestamp(ts, now_in_hour_start-1)
    else:
        timestamps = get_hour_strs_fromtimestamp(ts, end_ts)
    
    timestamps = map(lambda x: str(x), timestamps)

    data = dict()
    data["key"] = key
    data["dimension"] = dimension
    data["var_list"] = var_list.split(",")
    data["timestamps"] = timestamps
    req = Event("nebula", "continuousquery", key, millis_now(), data)
    ContinuousClient = babel.get_offline_continuous_query_client()
    response = ContinuousClient.send(req, key, block=False, timeout=5)
        
    if response[0]:
        if isinstance(response[1], list):
            result = dict()
            for r in response[1]:
                logger.debug(DEBUG_PREFIX+"返回的一个event:%s", r)
                result = dict_merge(result, r.property_values.get("result", {}) or dict())
        else:
            result = response[1].property_values.get("result", {})
        logger.debug(DEBUG_PREFIX+"有返回的结果是:%s, 返回的结果是%s", response, result)
    else:
        logger.debug(DEBUG_PREFIX+"当前没有事件..., 返回的是%s", response)


def init_env(logger_name):
    logger = logging.getLogger(logger_name)
    logger.debug("=================== Enter Debug Level.=====================")
    # 配置redis
    RedisCtx.get_instance().host = settings.Redis_Host
    RedisCtx.get_instance().port = settings.Redis_Port
    # 初始化 metrics 服务
    try:
        from threathunter_common.metrics.metricsagent import MetricsAgent
    except ImportError:
        logger.error(u"from threathunter_common.metrics.metricsagent import MetricsAgent 失败")
        sys.exit(-1)

    MetricsAgent.get_instance().initialize_by_dict(settings.metrics_dict)
    logger.info(u"成功初始化metrics服务: {}.".format(MetricsAgent.get_instance().m))
    
    return logger


if __name__ == '__main__':
    OfflineBabelQuery()
