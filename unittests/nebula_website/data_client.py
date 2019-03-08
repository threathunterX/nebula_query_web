# -*- coding: utf-8 -*-
import time
import logging, traceback

from threathunter_common.event import Event
from threathunter_common.util import millis_now,curr_timestamp

from nebula_website import babel
from .utils import dict_merge

DEBUG_PREFIX = "==============="

logger = logging.getLogger('nebula.web.stat.data_client')

statQueryClient = babel.get_statquery_client()
GlobalSlotQueryClient = babel.get_globalslot_query_client()
Baseline_Query_client = babel.get_baseline_query_client()
RiskEventInfoClient = babel.get_risk_event_info_query_client()

OfflineBaselineClient = babel.get_offline_baseline_query_client()
OfflineKeyStatClient = babel.get_offline_keystat_query_client()
OfflineContinuousClient = babel.get_offline_continuous_query_client()

eventQueryClient = babel.get_eventquery_client()
licenseInfoClient = babel.get_licenseinfo_client()

ProfileQueryClient = babel.getProfileQueryClient()
ProfileAccountRiskClient = babel.getProfileAccountRiskClient()
ProfileAccountPageRiskClient = babel.getProfileAccountPageRiskClient()

ProfileTopPagesClient = babel.getProfileTopPagesClient()
ProfileCrawlerRiskClient = babel.getProfileCrawlerRiskClient()
ProfileCrawlerPageRiskClient = babel.getProfileCrawlerPageRiskClient()

OnlineSlotQueryClient = babel.get_online_slot_query_client()
OfflineMergeClient = babel.get_offline_merge_query_client()

last_get_ts = 0
cached_data = None
cached_key = None


def get_latest_events(key, key_type, fromtime=None, size=None, event_id=None, only_count=False):
    logger.debug(DEBUG_PREFIX+u"获取最近的事件们key:%s, type:%s, key_type:%s", key, type(key), key_type)

    prop_dict = dict(key_type=key_type, only_count=only_count)
    if fromtime:
        prop_dict['fromtime'] = fromtime
    if size:
        prop_dict['size'] = size
    if event_id:
        prop_dict['eventid'] = event_id

    request = Event("__all__", "eventquery_request", key, millis_now(), prop_dict)
    response = eventQueryClient.send(request, key, block=False, timeout=5)

    if response[0]:
        value = response[1].property_values.get("result")
        logger.debug(DEBUG_PREFIX+"有返回的结果是:%s, 返回的结果是%s", response, value)
    else:
        logger.debug(DEBUG_PREFIX+"当前没有事件..., 返回的是%s", response)

    return cached_data


def get_latest_statistic(key, key_type, var_list, subkeys=None):
    data = {"app": "nebula", "count": 100, "var_list": var_list, "key_type": key_type}
    if subkeys:
        data['subkeys'] = subkeys
    logger.debug(DEBUG_PREFIX+u"获取最近的事件们key:%s, type:%s, key_type:%s, 变量列表:%s", key, type(key), key_type,
                 var_list)
    request = Event("__all__", "keystatquery_request", key, millis_now(), data)
    response = statQueryClient.send(request, key, block=False, timeout=5)

    if response[0]:
        if isinstance(response[1], list):
            result = dict()
            for r in response[1]:
                logger.debug(DEBUG_PREFIX+"返回的一个event:%s", r)
                result = dict_merge(result, r.property_values.get("result", {}))
        else:
            result = response[1].property_values.get("result", {})
        
        logger.debug(DEBUG_PREFIX+"有返回的结果是:%s, 返回的结果是%s", response, result)
    else:
        logger.debug(DEBUG_PREFIX+"当前没有事件..., 返回的是%s", response)
        result = dict()

    return result


Incident_Query_Client = babel.get_incident_query_client()


def get_latest_incident(var_list, key='', key_variable='', count=20, page=0):
    data = dict()
    data['app'] = 'nebula'
    data['count'] = count
    data['page'] = page
    if key:
        data['key'] = key
    if key_variable:
        data['key_variable'] = key_variable
    data['var_list'] = var_list

    request = Event("nebula_web", "incidentquery", key, millis_now(), data)
    response = Incident_Query_Client.send(request, key, 10)
    if response[0] and isinstance(response[1], list):
        values = [event.property_values for event in response[1]]
        result = dict()
        for value in values:
            result = dict_merge(result, value)

        logger.debug(DEBUG_PREFIX+"有返回的结果是:%s, 返回的结果是%s", response, result)
    else:
        logger.debug(DEBUG_PREFIX+"当前没有事件..., 返回的是%s", response)
        result = dict()

    return result


Baseline_Query_client = babel.get_baseline_query_client()


def get_latest_baseline_statistic(key_variable, var_list, merge_list=None, count=100, topcount=1):
    data = dict()
    data['app'] = 'nebula'
    data['count'] = count
    data['topcount'] = topcount
    data['key_variable'] = key_variable
    data['var_list'] = var_list
    if merge_list:
        data['merge_list'] = merge_list

    request = Event("nebula_web", "baselinekeystatquery", '', millis_now(), data)
    response = Baseline_Query_client.send(request, '', 7)
    if response[0] and isinstance(response[1], list):
        values = [event.property_values for event in response[1]]
        result = dict()
        for value in values:
            result = dict_merge(result, value)
        logger.debug(DEBUG_PREFIX+"有返回的结果是:%s, 返回的结果是%s", response, result)
    else:
        logger.debug(DEBUG_PREFIX+"当前没有事件..., 返回的是%s", response)
        result = dict()

    return result


Online_Detail_Client = babel.get_online_detail_client()


def get_online_clicks_period(key, key_type, fromtime, endtime):
    query_type = 'clicks_period'
    res = get_online_detail_data(key, key_type, fromtime, endtime, query_type)
    return res.get(query_type, None)


def get_online_visit_stream(key, key_type, fromtime, endtime):
    query_type = 'visit_stream'
    res = get_online_detail_data(key, key_type, fromtime, endtime, query_type)
    return res.get(query_type, None)


def get_online_clicks(key, key_type, fromtime, endtime, limit, query=None):
    query_type = 'clicks'
    res = get_online_detail_data(key, key_type, fromtime, endtime, query_type, query=query, log_limit=limit)
    return res.get(query_type, None)


def get_online_detail_data(key, key_type, fromtime, endtime, query_type, log_limit=None, stream_limit=None, query=None):
    if not query:
        query = []

    if log_limit is None:
        log_limit = 20

    prop = dict(
        clickscount=log_limit,
        query=query,
        query_type=query_type,
        from_time=int(fromtime),
        end_time=int(endtime),
        dimension=key_type,
    )
    req = Event("nebula", "clickstreamrequest", key, millis_now(), prop)
    res = Online_Detail_Client.send(req, key, block=False, timeout=5, least_ret=1)
    if res[0]:
        result = res[1][0].property_values if isinstance(res[1], list) else res[1].property_values
        logger.debug(DEBUG_PREFIX+"有返回的结果是:%s, 返回的结果是%s", res, result)
    else:
        logger.debug(DEBUG_PREFIX+"当前没有事件..., 返回的是%s", res)
        result = dict()

    return result


def get_offline_merged_variable(keys, dimension, var_list, fromtime, endtime):
    """
    获取一段时间内变量的聚合数据

    :return:
    """

    data = dict()
    data['app'] = 'nebula'
    data['keys'] = keys
    if isinstance(var_list, list):
        data['var_list'] = var_list
    elif isinstance(var_list, (str, unicode)):
        data['var_list'] = var_list.split(',')
    else:
        return dict()

    fromtime = int(fromtime) / 3600000 * 3600000
    endtime = int(endtime) / 3600000 * 3600000
    time_list = range(fromtime, endtime + 1, 3600000)
    data["dimension"] = dimension
    data["time_list"] = time_list

    req = Event("nebula", "offline_merge_variablequery_request", '__GLOBAL__', millis_now(), data)
    response = OfflineMergeClient.send(req, '', block=False, timeout=5)
    if response[0]:
        if isinstance(response[1], list):
            result = dict()
            for r in response[1]:
                logger.debug(DEBUG_PREFIX+"返回的一个event:%s", r)
                result = dict_merge(result, r.property_values.get("result", {}) or dict())
        else:
            result = response[1].property_values.get("result", {})

        logger.debug(DEBUG_PREFIX+"有返回的结果是:%s, 返回的结果是%s", response, result)
        return result
    else:
        logger.debug(DEBUG_PREFIX+"当前没有事件..., 返回的是%s", response)


def get_offline_key_stat(keys, dimension, timestamp, var_list):
    """
    获取离线slot变量数据
    :return:
    """

    data = dict()
    data['app'] = 'nebula'
    data["keys"] = keys
    if isinstance(var_list, list):
        data["var_list"] = var_list
    elif isinstance(var_list, (str, unicode)):
        data["var_list"] = var_list.split(",")
    else:
        return dict()
    data["dimension"] = dimension
    data["timestamp"] = timestamp

    if not keys:
        top = True
    else:
        top = False

    if top:
        data['keys'] = ['__GLOBAL__']
        data['dimension'] = 'global'

    req = Event("nebula", "offlinekeystatquery", '__GLOBAL__', millis_now(), data)
    least_ret = None
    if dimension != "global":
        least_ret = 1
    response = OfflineKeyStatClient.send(req, '', block=False, timeout=5,
                                         least_ret=least_ret)
    if response[0]:
        if isinstance(response[1], list):
            result = dict()
            for r in response[1]:
                logger.debug(DEBUG_PREFIX+"返回的一个event:%s", r)
                result = dict_merge(result, r.property_values.get("result", {}) or dict())
        else:
            result = response[1].property_values.get("result", {})

        if top and result:
            result = result['__GLOBAL__']

        logger.debug(DEBUG_PREFIX+"有返回的结果是:%s, 返回的结果是%s", response, result)
        return result
    else:
        logger.debug(DEBUG_PREFIX+"当前没有事件..., 返回的是%s", response)


def get_online_key_stat(keys, dimension, timestamp, var_list):
    """
    获取在线slot变量数据
    :return:
    """

    data = dict()
    data['app'] = 'nebula'
    data["keys"] = keys
    if isinstance(var_list, list):
        data["var_list"] = var_list
    elif isinstance(var_list, (str, unicode)):
        data["var_list"] = var_list.split(",")
    else:
        return dict()
    data["dimension"] = dimension
    data["timestamp"] = timestamp

    if not keys:
        top = True
    else:
        top = False

    if top:
        data['keys'] = ['__GLOBAL__']
        data['dimension'] = 'global'

    req = Event("nebula", "online_slot_variablequery", '__GLOBAL__', millis_now(), data)
    least_ret = None
    response = OnlineSlotQueryClient.send(req, '', block=False, timeout=5,
                                          least_ret=least_ret)
    if response[0]:
        if isinstance(response[1], list):
            result = dict()
            for r in response[1]:
                logger.debug(DEBUG_PREFIX+"返回的一个event:%s", r)
                result = dict_merge(result, r.property_values.get("result", {}) or dict())
        else:
            result = response[1].property_values.get("result", {})

        if top and result:
           result = result['__GLOBAL__']
            # result = {k: v['value'] for k, v in result.iteritems()}

        logger.debug(DEBUG_PREFIX+"有返回的结果是:%s, 返回的结果是%s", response, result)
        return result
    else:
        logger.debug(DEBUG_PREFIX+"当前没有事件..., 返回的是%s", response)


def get_offline_baseline(key_variable, key_dimension, var_list, merge_list, timestamp, count=100, topcount=1):
    data = dict()
    data['count'] = count
    data['topcount'] = topcount
    data['key_variable'] = key_variable if isinstance(key_variable, list) else [key_variable, ]

    data['key_dimension'] = key_dimension
    data['var_list'] = var_list
    data['merge_list'] = list(merge_list)
    data["timestamp"] = timestamp
    
    req = Event("nebula", "offline_baselinekeystatquery", "", millis_now(), data)
#    BaselineClient = babel.get_offline_baseline_query_client()
    response = OfflineBaselineClient.send(req, "", timeout=10)
    if response[0]:
        if isinstance(response[1], list):
            result = dict()
            for r in response[1]:
                logger.debug(DEBUG_PREFIX+"返回的一个event:%s", r)
                result = dict_merge(result, r.property_values or dict())
        else:
            result = response[1].property_values or dict()
        logger.debug(DEBUG_PREFIX+"有返回的结果是:%s, 返回的结果是%s", response, result)
        return result
    else:
        logger.debug(DEBUG_PREFIX+"当前没有事件..., 返回的是%s", response)


def get_offline_continuous(key, dimension, timestamps, var_list):
    data = dict()
    data["key"] = key
    data["dimension"] = dimension
    data["var_list"] = var_list
    data["timestamps"] = timestamps
    req = Event("nebula", "continuousquery", key, millis_now(), data)
#    ContinuousClient = babel.get_offline_continuous_query_client()
    response = OfflineContinuousClient.send(req, key, block=False, timeout=10)
        
    if response[0] or isinstance(response[1], list):
        if isinstance(response[1], list):
            result = dict()
            for r in response[1]:
                logger.debug(DEBUG_PREFIX+"返回的一个event:%s", r)
                result = dict_merge(result, r.property_values.get("result", {}) or dict())
        else:
            result = response[1].property_values.get("result", {})
        logger.debug(DEBUG_PREFIX+"有返回的结果是:%s, 返回的结果是%s", response, result)
        return result
    else:
        logger.debug(DEBUG_PREFIX+"当前没有事件..., 返回的是%s", response)


def get_global_statistic(keys, var_list):
    data = {"app": "nebula", "var_list": var_list, "keys":keys}
    key = '__GLOBAL__'
    request = Event("__all__", "globalslotquery_request", key, millis_now(), data)
    response = GlobalSlotQueryClient.send(request, key, block=False, timeout=5)

    if response[0] and isinstance(response[1], list):
        values = [event.property_values.get("result") for event in response[1]]
        logger.debug(DEBUG_PREFIX + "有返回的结果是:%s, 返回的结果是%s", response, values)
        result = None
        if values:
            if isinstance(values[0], (int, float)):
                result = sum(values)
            elif isinstance(values[0], dict):
                result = dict()
                for value in values:
                    result = dict_merge(result, value)
    else:
        logger.debug(DEBUG_PREFIX+"当前没有事件..., 返回的是%s", response)
        result = dict()

    return result


def get_realtime_statistic(key, key_type, var_list):
    # rabbitmq conf conflicts cause query_web won't work.
    return dict()


def get_threat_map(from_time, end_time, limit=1000):
    # 初始化incidenteventinfoquery RPC client
    property_values = {
        'from_time': from_time,
        'end_time': end_time,
        'limit': limit
    }
    request = Event("nebula_web", "riskeventsinfoquery", '', millis_now(), property_values)
    response = RiskEventInfoClient.send(request, '', False, 10)
    # logging.debug("response:{} response_dir{}".format(response,dir(response)))
    if response[0]:
        result = response[1][0].get_dict()["propertyValues"].get("result", [])
        if result is None:
            return False, '导弹图参数错误'
        else:
            return True, result
    else:
        return False, '导弹图查询超时'


def find_ip_geo(ip):
    from threathunter_common.geo import threathunter_ip
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
        logger.error('get ip geo fail, length: %s, ip: %s', len_info_segs, ip)
    return country, province, city


def find_mobile_geo(mobile, country_code=None):
    from threathunter_common.geo import phonelocator
    
    info = phonelocator.get_geo(mobile, country_code)
    country, description = info.split()
    
    return country, description


def get_license_info():
    try:
        event = Event('nebula_web', 'licenseinfo', '', millis_now(), {})
        bbc, bbc_data = licenseInfoClient.send(event, '', True, 5)
        if bbc:
            licenseinfo = dict()
            licenseinfo['expire'] = bbc_data.property_values.get(
                'days', '')
            licenseinfo['version'] = bbc_data.property_values.get(
                'info', '')
            return licenseinfo
        else:
            return None
    except Exception as e:
        logger.error(e)
        return None


def get_profile_data(key, key_type, variables):
    # 初始化profilequery RPC client
    property_values = {
        'profile_key_value': key,
        'profile_key_type': key_type,
        'variables': variables
    }
    event = Event('nebula_web', 'profile_query', '',
                  millis_now(), property_values)

    # client发送event，如果RPC正常返回，则返回RPC server返回数据
    bbc, bbc_data = ProfileQueryClient.send(event, '', True, 10)
    profile_values = bbc_data.property_values if bbc else False
    return profile_values


def get_profile_account_risk(current_day, start_day, end_day):
    """
    查询profile账号安全场景
    
    new in 2.10
    不支持polling.
    Return:
    (sucess, dict or string)
    False, error message(string)
    True, data(any type)
    """
    bn = "ProfileAccountRiskClient"
    # babel request
    property_values = {
        'current_day': current_day,
        'start_day': start_day,
        'end_day': end_day
    }
    event = Event('nebula_web', 'profile_account_risk',
                  '', millis_now(), property_values)
    success, res = ProfileAccountRiskClient.send(event, '', True, 10)

    # babel request fail
    if not success:
        msg = u"%s Babel request fail, event: %s" % (bn, event)
        logger.error(msg)
        return False, msg

    # bad request
    _ = res.property_values
    if _.has_key("status"):
        msg = u"Bad %s response event: %s, status: %s, msg:%s " % (\
                     bn, event, _.get("status"), _.get("msg"))
        logger.error(msg)
        return False,msg
    
    return True, _


def get_profile_account_page_risk(current_day, pages):
    """
    new in 2.10
    不支持polling
    Return:
    (sucess, dict or string)
    False, error message(string)
    True, data(any type)
    """
    bn = "ProfileAccountPageRiskClient"
    # 查询profile账号来源分析
    property_values = {
        'current_day': current_day,
        'pages': pages
    }
    event = Event('nebula_web', 'profile_account_page_risk',
                  '', millis_now(), property_values)

    success, res = ProfileAccountPageRiskClient.send(event, '', True, 10)

    # babel request fail
    if not success:
        msg = u"%s Babel request fail, event: %s" % (bn, event)
        logger.error(msg)
        return False, msg

    # bad request
    _ = res.property_values
    if _.has_key("status"):
        msg = u"Bad %s response event: %s, status: %s, msg:%s " % (\
                     bn, event, _.get("status"), _.get("msg"))
        logger.error(msg)
        return False,msg
    
    return True, _


def get_profile_top_pages(current_day, top_start, top_limit, top_type):
    """
    New in 2.11
    不支持polling
    Return:
    (sucess, dict or string)
    False, error message(string)
    True, data(any type)
    """
    bn = "ProfileTopPagesClient"
    prop = dict(current_day=current_day,
                start=top_start,
                limit=top_limit,
                type=top_type,
            )
    event = Event("nebula_web", "profile_top_pages",
                  "", millis_now(), prop)
    success, res = ProfileTopPagesClient.send(event, "", block=False, timeout=5)

    # babel request fail
    if not success:
        msg = u"%s Babel request fail, event: %s" % (bn, event)
        logger.error(msg)
        return False, msg
    
    # bad request
    _ = res.property_values
    if _.has_key("status"):
        msg = u"Bad %s response event: %s, status: %s, msg:%s " % \
              (bn, event, _.get("status"), _.get("msg"))
        logger.error(msg)
        return False, msg

    return True, _.get("pages", None)


def get_profile_crawler_risk(current_day, start_day, end_day):
    """
    new in 2.11
    不支持polling.
    Return:
    (sucess, dict or string)
    False, error message(string)
    True, data(any type)
    """
    bn = "ProfileCrawlerRiskClient"
    # babel request
    property_values = {
        'current_day': current_day,
        'start_day': start_day,
        'end_day': end_day
    }
    event = Event('nebula_web', 'profile_crawler_risk',
                  '', millis_now(), property_values)
    success, res = ProfileCrawlerRiskClient.send(event, '', True, 10)

    # babel request fail
    if not success:
        msg = u"%s Babel request fail, event: %s" % (bn, event)
        logger.error(msg)
        return False, msg

    # bad request
    _ = res.property_values
    if _.has_key("status"):
        msg = u"Bad %s response event: %s, status: %s, msg:%s " % (\
                     bn, event, _.get("status"), _.get("msg"))
        logger.error(msg)
        return False,msg
    
    return True, _


def get_profile_crawler_page_risk(current_day, pages):
    """
    爬虫dashboard pages们的分时分析
    new in 2.11
    不支持polling
    Return:
    (sucess, dict or string)
    False, error message(string)
    True, data(any type)
    """
    bn = "ProfileCrawlerRiskClient"
    property_values = {
        'current_day': current_day,
        'pages': pages
    }
    event = Event('nebula_web', 'profile_crawler_page_risk',
                  '', millis_now(), property_values)

    try:
        success, res = ProfileCrawlerPageRiskClient.send(event, '', True, 10)
    except Exception:
        msg = "Exception During %s Babel Request: %s", bn, traceback.format_exc()
        logger.error(msg)
        return False, msg

    # babel request fail
    if not success:
        msg = u"%s Babel request fail, event: %s" % (bn, event)
        logger.error(msg)
        return False, msg

    # bad request
    _ = res.property_values
    if _:
        if _.has_key("status"):
            msg = u"Bad %s response event: %s, status: %s, msg:%s " % (\
                     bn, event, _.get("status"), _.get("msg"))
            logger.error(msg)
            return False,msg
    
        return True, _
    return False, "%s Babel event's property_values is blank." % bn
