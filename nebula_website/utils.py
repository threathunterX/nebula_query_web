# -*- coding: utf-8 -*-
import time,logging, sys
from os import path as opath

from jinja2 import FileSystemLoader, Environment

from threathunter_common.redis.redisctx import RedisCtx
from threathunter_common.geo import threathunter_ip

from nebula_website import settings

def render(template_path, context):
    """
    Assuming a template at /some/path/my_tpl.html, containing:

    Hello {{ firstname }} {{ lastname }}!

    >> context = {
    'firstname': 'John',
    'lastname': 'Doe'
    }
    >> result = render('/some/path/my_tpl.html', context)
    >> print(result)
    Hello John Doe!
    """

    path, filename = opath.split(template_path)
    return Environment(
        loader=FileSystemLoader(path or './')
    ).get_template(filename).render(context).encode('utf8')


def get_hour_strs_fromtimestamp(fromtime, endtime):
    # fromtime, endtime is float timestamp
    if fromtime >= endtime:
        return []
    ts = []
    while fromtime < endtime:
        ts.append(fromtime)
        fromtime = fromtime + 3600

    if ts and ts[-1] + 3600 < endtime:
        ts.append(endtime)
    return ts


def get_hour_start(point=None):
    """
    获取point时间戳所在的小时的开始的时间戳, 默认获取当前时间所在小时的开始时的时间戳
    """
    if point is None:
        p = time.time()
    else:
        p = point

    return ((int(p) / 3600) * 3600) * 1.0


def get_current_hour_timestamp():
    return int(get_hour_start() * 1000)


def get_ts_from_hour(time_str, f="%Y%m%d%H"):
    """
    ex. 2016010212(str) -> timestamp * 1000(int)
    """
    return int(time.mktime(time.strptime(time_str, f)) * 1000)


def find_ip_geo(ip):
    
    info = threathunter_ip.find(ip)
    info_segs = info.split()
    len_info_segs = len(info_segs)
    country = ''
    province = ''
    city = ''
    if len_info_segs == 1:
        if info_segs[0] != u'未分配或者内网IP':
            country = info_segs[0]
    elif len_info_segs == 2:
        country = info_segs[0]
        province = info_segs[1]
        city = ""
    elif len_info_segs == 3:
        country = info_segs[0]
        province = info_segs[1]
        city = info_segs[2]
    else:
        print 'length: {}, ip: {}'.format(len_info_segs, ip)
    return country, province, city


def dict_merge(src_dict, dst_dict):
    """
    将两个dict中的数据对应键累加,
    不同类型值的情况:
    >>> s = dict(a=1,b='2')
    >>> d = {'b': 3, 'c': 4}
    >>> dict_merge(s,d)
    >>> t = {'a': 1, 'b': 5, 'c': 4}
    >>> s == t
    True
    >>> s = dict(a=set([1,2]), )
    >>> d = dict(a=set([2, 3]),)
    >>> dict_merge(s,d)
    >>> t = {'a':set([1,2,3])}
    >>> s == t
    True
    >>> s = dict(a={'a':1, 'b':2})
    >>> d = dict(a={'a':1, 'b':2})
    >>> dict_merge(s, d)
    >>> t = dict(a={'a':2, 'b':4})
    >>> s == t
    True
    """

    result = dict()
    if not any( isinstance(_, dict) for _ in [src_dict, dst_dict]):
        return result

    if src_dict is None and dst_dict is not None:
        return dst_dict
    if dst_dict is None and src_dict is not None:
        return src_dict

    for k in dst_dict.keys():
        if k not in src_dict:
            result[k] = dst_dict.pop(k)
        else:
            v = dst_dict.pop(k)
            if isinstance(v, (basestring, int, float)):
                result[k] = int(v) + int(src_dict.pop(k))
            elif isinstance(v, set):
                assert type(v) == type(src_dict[k]), 'key %s,dst_dict value: %s type: %s, src_dict value: %s type:%s' % (k, v, type(v), src_dict[k], type(src_dict[k]))
                v.update(src_dict.pop(k))
                result[k] = v
            elif isinstance(v, dict):
                result[k] = dict_merge(src_dict.pop(k), v)
    for k, v in src_dict.items():
        result[k] = v
    return result


def parse_host_url_path(url):
    if url.find('/') == -1:
        # ex. 183.131.68.9:8080, auth.maplestory.nexon.com:443
        host = url
        url_path = ''
    else:
        if url.startswith('http') or url.startswith('https'):
            # 有协议的, 需要扩充
            segs = url.split('/',3)
            host = '/'.join(segs[:3])
            url_path = segs[-1]
        else:
            host, url_path = url.split('/',1)
    return host, url_path


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


def reduce_value_level(d):
    """
    >>> a = {'a' : {'value' : 1}}
    >>> reduce_value_level(a)
    >>> a
    {'a': 1}
    >>> a  = dict(a=1, b=dict(a=1), c=dict(value=1))
    >>> reduce_value_level(a)
    >>> a
    {'a': 1, 'c': 1, 'b': {'a': 1}}
    >>> a = {'value': 1}
    >>> reduce_value_level(a)
    >>> a
    {'value': 1}
    >>> a  = dict(a=1, b=dict(a=1), c=dict(a=1, b=dict(value=2)))
    >>> reduce_value_level(a)
    >>> a
    {'a': 1, 'c': {'a': 1, 'b': 2}, 'b': {'a': 1}}
    """

    for k in d.keys():
        v = d.get(k)
        if isinstance(v, dict) and len(v) == 1 and v.has_key('value'):
            d[k] = v['value']
        elif isinstance(v, dict):
            reduce_value_level(v)
            d[k] = v


def transfer_dict_to_traditional(origin):
    result = {}
    for item in origin:
        result[item['key']] = item['value']
    return result

