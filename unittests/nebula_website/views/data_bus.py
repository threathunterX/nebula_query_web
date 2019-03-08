# -*- coding: utf-8 -*-
import logging, time
from datetime import datetime
import traceback

from flask import Blueprint, request, jsonify, current_app, make_response

from threathunter_common.metrics.metricsagent import MetricsAgent

from nebula_website import data_client
from nebula_website import utils, settings
from nebula_website.utils import reduce_value_level

mod = Blueprint("data_bus", __name__)

DEBUG_PREFIX = "==============="

logger = logging.getLogger("nebula.web.stat.data_bus")

@mod.route("/stats/online", methods=["GET"])
def OnlineDataHandler():
    """
    从实时获取数据的api接口

    @API
    summary: 从online获取当前5分钟数据
    notes: 从online获取当前5分钟数据
    tags:
      - platform
    parameters:
      - name: key
        in: query
        required: false
        type: string
        description: 变量值
      - name: key_type
        in: query
        required: true
        type: string
        description: 维度
      - name: var_list
        in: query
        required: true
        type: string
        description: 变量列表
    """
    req = request.args
    key = req.get("key", "")
    key_type = req.get("key_type", "")
    var_list = req.getlist("var_list")
    logger.debug("Args receive ==== key: %s, key_type: %s, var_list:%s",
                 key, key_type, var_list)
    try:
        ret_stats = None#data_client.get_realtime_statistic(key, key_type, var_list)
        if ret_stats:
            return jsonify(status=0, values=ret_stats)
        else:
            return jsonify(status=0, values=ret_stats, msg=u"realtime数据返回为空")
    except Exception as e:
        logger.error(e)
        return jsonify(status=-1, error=e.message)

@mod.route('/stats/slot', methods=["GET"])
def SlotDataHandler():
   """
   从slot获取数据的api接口
   @todo key_type not none

   @API
   summary: 从slot获取当前小时数据
   notes: 从slot获取当前小时数据
   tags:
     - platform
   parameters:
     - name: key
       in: query
       required: false
       type: string
       description: 变量值
     - name: key_type
       in: query
       required: true
       type: string
       description: 维度
     - name: var_list
       in: query
       required: true
       type: string
       description: 变量列表
   """
   req = request.args
   key = req.get("key", "")
   key_type = req.get("key_type", "")
   var_list = req.getlist("var_list")
   logger.debug("Args receive ==== key: %s, key_type: %s, var_list:%s",
                key, key_type, var_list)
   scenes = ['VISITOR', 'ACCOUNT', 'ORDER', 'TRANSACTION', 'MARKETING', 'OTHER']
   subkeys = dict( (_,scenes) for _ in var_list if 'scene' in _)
   try:
       if settings.Enable_Online:
           if key_type == 'total':
               ret_stats = data_client.get_global_statistic(var_list, subkeys=subkeys)
           else:
               ret_stats = data_client.get_latest_statistic(key, key_type, var_list, subkeys=subkeys)
       else:
           ret_stats = None

       if ret_stats:
           return jsonify(status=0, values=ret_stats)
       else:
           return jsonify(status=0, values=ret_stats, msg=u"slot数据返回为空")
   except Exception as e:
       logger.error(e)
       return jsonify(status=-1, error=e.message)

@mod.route('/stats/slot/query_offline', methods=["POST"])
def OfflineSlotDataHandler():
    """
    从slot获取数据的api接口

    """
    req = request.get_json()
    keys = req.get('keys', None)
    timestamp = int(req.get('timestamp', 0))
    variables = req.get('variables', None)
    dimension = req.get('dimension', None)

    if not(timestamp and variables):
        return jsonify(status=400, msg='timestamp, variables不能为空')

    try:
        ret_stats = None
        ret_stats = data_client.get_offline_key_stat(keys, dimension, timestamp, variables)
        if ret_stats and isinstance(ret_stats, dict):
            reduce_value_level(ret_stats)

        if ret_stats:
            return jsonify(status=0, values=ret_stats)
        else:
            return jsonify(status=0, values=ret_stats, msg=u"slot数据返回为空")
    except Exception as e:
        logger.error(traceback.format_exc())
        return jsonify(status=-1, error=e.message)
 

@mod.route('/stats/slot_baseline', methods=["GET"])
def SlotBaseLineDataHandler():
    req = request.args    
    key_var = req.get("key_var", "")
    key_type = req.get("key_type", "")
    var_list = req.getlist("var_list")
    merge_list = req.getlist("merge_list")
    logger.debug("Args receive ==== key_var: %s, key_type: %s, var_list:%s, merge_list:%s",
                 key_var, key_type, var_list, merge_list)
    if len(var_list) < 1:
        return jsonify(status=-1, error=u"两次连续的查询的变量列表不能为空")
    
    try:
        ret_stats = data_client.get_latest_baseline_statistic(key_var, var_list, merge_list)
        if ret_stats:
            return jsonify(status=0, values=ret_stats)
        else:
            return jsonify(status=0, values=ret_stats, msg=u"slot数据返回为空")
    except Exception as e:
        logger.error(e)
        return jsonify(status=-1, error=e.message)

#@mod.route('/stats/offline', methods=["GET"])
#def OfflineDataHandler():
#    req = request.args    
#    from_time = req.get('from_time', '')
#    end_time = req.get('end_time', '')
#    key = req.get("key", "")
#    key_type = req.get("key_type", "")
#    var_list = req.getlist("var_list")
#    
#    from_time = int(from_time) / 1000.0
#    end_time = int(end_time) / 1000.0
#    logger.debug(DEBUG_PREFIX+u"查询的时间是%s", datetime.fromtimestamp(from_time))
#    
#    logger.debug("Args receive ==== key: %s, key_type: %s, var_list:%s",
#                 key, key_type, var_list)
#    try:
#        # @todo format key && key_type
#        if not key:
#            key = "__GLOBAL__"
#        if key_type == "total":
#            key_type = "global"
#        ret_stats = data_client.get_offline_key_stat(key, key_type, from_time, var_list)
#        if ret_stats:
#            if isinstance(ret_stats, dict):
#                reduce_value_level(ret_stats)
#            return jsonify(status=0, values=ret_stats)
#        else:
#            return jsonify(status=0, values=ret_stats, msg=u"offline数据返回为空")
#    except Exception as e:
#        logger.error(e)
#        return jsonify(status=-1, error=e.message)

@mod.route('/stats/offline_baseline', methods=["GET"])
def OfflineBaseLineDataHandler():
    req = request.args    
    from_time = req.get('from_time', '')
    end_time = req.get('end_time', '')
    key_var = req.get("key_var", "")
    key_type = req.get("key_type", "")
    var_list = req.getlist("var_list")
    merge_list = req.getlist("merge_list")
    logger.debug("Args receive ==== key_var: %s, key_type: %s, var_list:%s, merge_list:%s",
                 key_var, key_type, var_list, merge_list)
    if len(var_list) < 1 or not key_type:
        return jsonify(status=-1, error=u"两次连续的查询的变量列表var_list为空 或者查询的全局统计信息的key_type未知")

    from_time = int(from_time) / 1000.0
    end_time = int(end_time) / 1000.0
    logger.debug(DEBUG_PREFIX+u"查询的时间是%s", datetime.fromtimestamp(from_time))

    try:
        ret_stats = data_client.get_offline_baseline(key_var, key_type, var_list, merge_list, int(from_time*1000))
        if ret_stats:
            return jsonify(status=0, values=ret_stats)
        else:
            return jsonify(status=0, values=ret_stats, msg=u"offline数据返回为空")
    except Exception as e:
        logger.error(e)
        return jsonify(status=-1, error=e.message)

@mod.route('/stats/offline_serial', methods=["GET"])
def OfflineSerialDataHandler():
    """
    从Aerospike获取一些连续小时的统计数据

    @API
    summary: 从Aerospike获取一些连续小时的统计数据
    notes: 从Aerospike获取一些连续小时的统计数据
    tags:
      - platform
    parameters:
      -
        name: from_time
        in: query
        required: true
        type: integer
        description: 起始时间
      -
        name: end_time
        in: query
        required: true
        type: integer
        description: 结束时间
      -
        name: key_type
        in: query
        required: true
        type: string
        description: 维度
      -
        name: key
        in: query
        required: false
        type: string
        description: 变量值
      -
        name: var_list
        in: query
        required: false
        type: string
        description: 变量名列表
    """
    req = request.args
    from_time = req.get('from_time', '')
    end_time = req.get('end_time', '')
    key = req.get("key", "")
    key_type = req.get("key_type", "")
    var_list = req.getlist("var_list")
    logger.debug("Args receive ==== key_var: %s, key_type: %s, var_list:%s",
                 key, key_type, var_list)

    ### TODO: ugly hack
    if key_type == 'user':
        key_type = 'uid'

    if not (from_time and end_time and key_type):
        return jsonify(status=-1, msg=u"参数错误，没有查询时间范围, 或者没有指定维度")

    ts = int(from_time) / 1000 / 3600 * 3600
    end_ts = (int(end_time) / 1000 + 1) / 3600 * 3600
    now = int(time.time() * 1000)
    now_in_hour_start = now / 1000 / 3600 * 3600
    logger.debug(DEBUG_PREFIX+u"查询的时间范围是%s ~ %s", datetime.fromtimestamp(ts), datetime.fromtimestamp(end_ts))

    if key_type == "total":
        key_type = "global"
    if not key:
        # 默认取全局的数据时 key_type = 'total'
        key = '__GLOBAL__'

    try:
        if end_ts >= now_in_hour_start:
            timestamps = utils.get_hour_strs_fromtimestamp(ts, now_in_hour_start-1)
        else:
            timestamps = utils.get_hour_strs_fromtimestamp(ts, end_ts)

        timestamps = map(lambda x: str(x).split(".")[0] + ".0", timestamps)
        #logger.debug(DEBUG_PREFIX+u"查询的时间戳: %s", timestamps)
        records = None
        if timestamps:
            records = data_client.get_offline_continuous(key, key_type, timestamps, var_list)
        if not records:
            records = dict()
        
        # logger.debug(DEBUG_PREFIX+u"查询的key: %s, key_type:%s, 返回的查询结果是:%s", key, key_type, records)
        logger.debug(DEBUG_PREFIX + u"查询的key: {}, key_type:{}".format(key,key_type))
        ret_stats = dict( (int(float(ts)*1000), v)  for ts,v in records.iteritems())
        if ret_stats:
            return jsonify(status=0, values=ret_stats)
        else:
            return jsonify(status=0, values=[])
#            return jsonify(status=0, values=ret_stats, msg=u"offline数据返回为空")
    except:

        logger.error(traceback.format_exc())
        return jsonify(status=-1, error=traceback.format_exc())


@mod.route('/stats/metrics', methods=["GET"])
def MetricsDataHandler():
    """
    从metrics监控系统获取统计数据
    
    values: { timepoint1: {tag1:count, tag2:count}, timepoint2:{tag1:count, tag2:count}}
    """
    req = request.args
    from_time = int(req.get('from_time', 0))
    end_time = int(req.get('end_time', 0))
    group_tags = req.getlist('group_tag')
    filter_tags = req.getlist('filter_tag')
    db = req.get('db', 'default')
    metrics_name = req.get('metrics_name', None)
    interval = req.get('interval', 0)
    aggregation = req.get('aggregation', 'sum')
    
    if not metrics_name:
        return jsonify(status=-1, msg=u"参数错误，查询的metrics_name为空")
        
    logger.debug(DEBUG_PREFIX+u"查询的时间范围是%s ~ %s", datetime.fromtimestamp(from_time/1000.0), datetime.fromtimestamp(end_time/1000.0))
    logger.debug(DEBUG_PREFIX+u"查询的db: %s, metrics_name:%s, aggregation:%s, from_time:%s, end_time:%s, group_tags:%s, filter_tags:%s, interval:%s", db, metrics_name, aggregation, from_time, end_time, group_tags, filter_tags, interval)
    try:
        ret_stats = MetricsAgent.get_instance().query(db, metrics_name, aggregation, from_time, end_time, interval, filter_tags, group_tags)
        return jsonify(status=0, values=ret_stats)
    except Exception as e:
        logger.error(e)
        return jsonify(status=-1, error=e.message)

@mod.route('/stats/geo', methods=["GET"])
def GEODataHandler():
    """
    ip,mobile地理信息的数据源
    
    """
    req = request.args    
    ips = req.getlist('ip')
    mobiles = req.getlist('mobile')
        
    try:
        ret_stats = dict()
        ip_dict = ret_stats['ip'] = dict()
        mobile_dict = ret_stats['mobile'] = dict()
        for ip in ips:
            ip_dict[ip] = data_client.find_ip_geo(ip)
        for mobile in mobiles:
            mobile_dict[ip] = data_client.find_mobile_geo(mobile)
        return jsonify(status=0, values=ret_stats)
    except Exception as e:
        logger.error(e)
        return jsonify(status=-1, error=e.message)

@mod.route('/stats/threat_map', methods=["GET"])
def ThreatMapDataHandler():
    """
    导弹图接口，查询开始时间和结束时间之间的1000次风险事件访问数据

    @API
    summary: threat map
    tags:
      - platform
    parameters:
      - name: from_time
        in: query
        description: 开始时间
        required: true
        type: timestamp
      - name: end_time
        in: query
        description: 结束时间
        required: true
        type: timestamp
      - name: limit
        in: query
        description: 攻击事件个数，默认为1000
        required: false
        type: number
        default: 1000
    """
    req = request.args
    try:
        from_time = int(req.get('from_time', 0))
        end_time = int(req.get('end_time', 0))
        limit = int(req.get('limit', 1000))

        # 开始时间和结束时间不能为空
        if from_time and end_time:
            res, result = data_client.get_threat_map(from_time, end_time, limit)

            # RPC正常返回为攻击城市信息列表，超时返回为False，
            if res:
                return jsonify(status=200, values=result)
            else:
                return jsonify(status=500, msg=result)
        else:
            return jsonify(status=400, msg='开始时间和结束时间不能为空')
    except:
        logger.error(traceback.format_exc())
        return jsonify(status=500, msg='导弹图查询失败')

@mod.route("/stats/profile", methods=["POST"])
def ProfileStatHandler():
    """
    获取id获取档案变量列表类型和值，封装Java RPC client

    @API
    summary: 档案
    notes: 档案变量类型和值
    tags:
      - platform
    parameters:
      -
        name: profile
        in: body
        required: true
        type: json
        description: 档案id和变量列表
    produces:
      - application/json
    """
    # No more data format transform
    # debug in 3 level
    ip_location_variable = 'user__account__ip_last10_login_timestamp__profile'
    alarm_increment_variable = 'user__visit__alarm_increment_times__profile'
    hour_merge_variable = 'user__visit__hour_merge__profile'

    profile = request.get_json()
    key = profile.get('key', None)
    key_type = profile.get('key_type', None)
    variables = profile.get('variables', None)

    if not(key and key_type and variables):
        return jsonify(status=400, msg='档案id、类型及查询信息不能为空')

    if not(key_type in['user', 'ip', 'did', 'page'] and isinstance(variables, list)):
        return jsonify(status=400, msg='档案类型必须为user/ip/did/page且查询信息类型为列表')

    try:
        profile_values = data_client.get_profile_data(key, key_type, variables)
        # RPC返回超时，profile_values为False，正确返回时，判断status是否为200
        if profile_values is False:
            return jsonify(dict(status=500, msg='服务器处理超时'))
        else:
            status = profile_values.get('status', 500)
            if status == 200:
                # 返回profile_values格式，例：
                # {"status":200,"content":{"user__visit__alarm_increment_times__profile":{"type":"long","value":10}}}
                # 只取变量的值，不需要其他type等信息
                content = profile_values.get('content', {})
                profile_variables = {key: values[
                    'value'] for key, values in content.items() if 'value' in values}

                # ip_location_variable变量需要添加IP的location信息,按照timestamp大小排序
                if ip_location_variable in profile_variables:
                    ip_location_dict = profile_variables.get(
                        ip_location_variable, {})
                    sort_timestamp_ip = sorted(ip_location_dict.items(
                    ), lambda x, y: cmp(x[1], y[1]), reverse=True)
                    ip_location_list = []
                    for ip, ts in sort_timestamp_ip:
                        country, province, city = utils.find_ip_geo(ip)
                        ip_location_list.append({'ip': ip,
                                                 'timestamp': ts, 'location': city})
                    profile_variables[
                        ip_location_variable] = ip_location_list

                # alarm_increment_variable变量需要加上默认值0
                if alarm_increment_variable not in profile_variables:
                    profile_variables[alarm_increment_variable] = 0

                # hour_merge_variable变量需要每个小时的数据，默认值为0
                hour_merge_value = profile_variables.get(
                    hour_merge_variable, {})
                profile_variables[hour_merge_variable] = [
                    hour_merge_value.get(format(i, '02d'), 0) for i in range(1, 25)]

                return jsonify({'status': status,
                                'msg': 'ok', 'values': profile_variables})
            else:
                return jsonify({'status': status,
                                'msg': profile_values.get('msg', '服务器处理异常')})
    except Exception as e:
        logger.error(e)
        return jsonify(status=500, msg='档案查询失败')

@mod.route("/stats/profile_top_pages", methods=["GET"])
def ProfileTopPagesHandler():
    req = request.args
    try:
        current_day = int(req.get('current_day', 0))
        top_start = int(req.get('start', 0))
        top_limit = int(req.get('limit', 100))
        is_focus = req.get("is_focus", False)
        top_type = "followed" if is_focus == "true" else "all"
        
    except Exception:
        return make_response(("current_day, start, limit args is invalid.",
                              400, dict()))
        
    if not (current_day and top_start and top_limit):
        return make_response(("current_day, start, limit args is required.",
                              400, dict()))

    try:
        success, d = data_client.get_profile_top_pages(current_day, top_start, top_limit,
                                                       top_type)
    except Exception:
        if success:
            return jsonify(d)
        else:
            return make_response((d, 503, dict()))
    except Exception:
        msg = traceback.format_exc()
        current_app.logger.error(msg)
        return make_response((msg, 500, dict()))

@mod.route("/stats/crawler_risk", methods=["GET"])
def ProfileCrawlerStatHandler():
    """
    查询dashboard 爬虫风险趋势，一周趋势、今日统计接口

    @API
    summary: 查询一周趋势、今日统计
    tags:
      - platform
    parameters:
      - name: current_day
        in: query
        required: true
        type: timestamp
        description: 查询今日统计的日期时间戳
      - name: start_day
        in: query
        required: true
        type: timestamp
        description: 一周趋势统计开始日期时间戳
      - name: end_day
        in: query
        required: true
        type: timestamp
        description: 一周趋势统计开始日期时间戳
    produces:
      - application/json
    """
    req = request.args
    try:
        current_day = int(req.get('current_day', 0))
        start_day = int(req.get('start_day', 0))
        end_day = int(req.get('end_day'), 0)
    except Exception:
        return make_response(("current_day, start_day, end_day args is invalid.",
                              400, dict()))

    if not (current_day and start_day and end_day):
        return make_response(("current_day, start_day, end_day args is required.",
                              400, dict()))

    try:
        success, d = data_client.get_profile_crawler_risk(current_day, start_day, end_day)

        if success:
            return jsonify({'status': 200, 'msg': 'ok', 'values':d})
        else:
            return make_response((d, 503, dict()))
    except Exception:
        msg = traceback.format_exc()
        current_app.logger.error(msg)
        return make_response((msg, 500, dict()))

def count_func(iterable):
    if not iterable:
        return 0
    return reduce(lambda x,y: x+y, iterable)

PCPS_keys = ('00', '01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '20', '21', '22', '23')
    
@mod.route("/stats/crawler_page_risk", methods=["GET"])
def ProfileCrawlerPageStatHandler():
    """
    爬虫dashboard分时分析

    @API
    summary: 爬虫dashboard分时分析
    tags:
      - platform
    parameters:
      - name: body
        in: body
        required: true
        type: json
        description: 账号来源分析参数
    produces:
      - application/json
    """
    req = request.args
    current_day = int(req.get('current_day', 0))
    top_start = int(req.get('start', 0))
    top_limit = int(req.get('limit', 100))
    is_focus = req.get("is_focus", False)
    pages = req.getlist("pages")
    
    # @todo upload_bytes unit..
    top_type = "followed" if is_focus == "true" else "all"
    if not current_day:
        return make_response(("json args: current_day is required.",
                              400, dict()))
        
    try:
        if not pages:
            suc, _ = data_client.get_profile_top_pages(current_day, top_start, top_limit,
                                                       top_type)
            if suc:
                pages = _
            if (suc and not _) or not suc:
                return make_response((_ or "Can't get top pages.", 503, dict()))
            
        success, d = data_client.get_profile_crawler_page_risk(current_day, pages)
        if success:
            # custmize format
            result = []
            for url in pages:
                counter = d.get(url)
                if not counter:
                    continue
                _ = dict()
                _["url"] = url
                counts = counter.get("page__crawler_request_amount__profile", dict())
                _["count"] = count_func(counts.values())
                _["crawler_count"] = count_func(counter.get("page__crawler_crawler_risk_amount__profile", dict()).values())
                mean_latencys = counter.get("page__crawler_latency__profile", dict())
                total_latency = 0
                for k,v in mean_latencys.iteritems():
                    total_latency += v * counts.get(k, 1)
                _["latency"] =  total_latency / float(_["count"] or 1)
                _["upload_bytes"] = count_func(counter.get("page__crawler_upstream_size__profile", dict()).values())
                continuous_data = dict()
                for k in PCPS_keys:
                    tmp_d = continuous_data[k] = dict()
                    tmp_d["count"] = counter.get("page__crawler_request_amount__profile", dict()).get(k,0)
                    tmp_d["crawler_count"] = counter.get("page__crawler_crawler_risk_amount__profile", dict()).get(k,0)
                    tmp_d["latency"] = counter.get("page__crawler_latency__profile", dict()).get(k,0)# / float(tmp_d["count"] or 1)
                    tmp_d["upload_bytes"] = counter.get("page__crawler_upstream_size__profile", dict()).get(k,0)
                    tmp_d["2XX"] = counter.get("page__crawler_status_2__profile", dict()).get(k,0)
                    tmp_d["3XX"] = counter.get("page__crawler_status_3__profile", dict()).get(k,0)
                    tmp_d["4XX"] = counter.get("page__crawler_status_4__profile", dict()).get(k,0)
                    tmp_d["5XX"] = counter.get("page__crawler_status_5__profile", dict()).get(k,0)
                    
                _["continuous_data"] = continuous_data
                result.append(_)
#            result.sort(key=lambda x:x.get("count", 0), reverse=True)
            return jsonify({'status': 200, 'msg': 'ok', 'values':result})
        else:
            return make_response((d, 503, dict()))
    except Exception:
        msg = traceback.format_exc()
        current_app.logger.error(msg)
        return make_response((msg, 500, dict()))

@mod.route('/stats/account_risk', methods=["GET"])
def ProfileAccountStatHandler():
    """
    查询账户安全报表，一周趋势、今日统计接口

    @API
    summary: 查询一周趋势、今日统计
    tags:
      - platform
    parameters:
      - name: current_day
        in: query
        required: true
        type: timestamp
        description: 查询今日统计的日期时间戳
      - name: start_day
        in: query
        required: true
        type: timestamp
        description: 一周趋势统计开始日期时间戳
      - name: end_day
        in: query
        required: true
        type: timestamp
        description: 一周趋势统计开始日期时间戳
    produces:
      - application/json
    """
    req = request.args
    try:
        current_day = int(req.get('current_day', 0))
        start_day = int(req.get('start_day', 0))
        end_day = int(req.get('end_day'), 0)
    except Exception:
        return make_response(("current_day, start_day, end_day args is invalid.",
                              400, dict()))

    if not (current_day and start_day and end_day):
        return make_response(("current_day, start_day, end_day args is required.",
                              400, dict()))

    try:
        success, d = data_client.get_profile_account_risk(current_day, start_day, end_day)

        if success:
            
            return jsonify({'status': 200, 'msg': 'ok', 'values':d})
        else:
            return make_response((d, 503, dict()))
    except Exception:
        msg = traceback.format_exc()
        current_app.logger.error(msg)
        return make_response((msg, 500, dict()))

@mod.route('/stats/account_page_risk', methods=["POST"])
def ProfileAccountPageStatHandler():
    """
    账号来源分析接口

    @API
    summary: 账号来源分析，登录、注册page详情
    tags:
      - platform
    parameters:
      - name: body
        in: body
        required: true
        type: json
        description: 账号来源分析参数
    produces:
      - application/json
    """
    body = request.get_json()
    current_day = int(body.get('current_day', 0))
    pages = body.get('pages', [])
    if not (current_day and pages):
        return make_response(("json args: current_day, pages is required.",
                              400, dict()))

    try:
        success, d = data_client.get_profile_account_page_risk(current_day, pages)

        if success:
            return jsonify({'status': 200, 'msg': 'ok', 'values':d})
        else:
            return make_response((d, 503, dict()))
    except Exception:
        msg = traceback.format_exc()
        current_app.logger.error(msg)
        return make_response((msg, 500, dict()))
        
@mod.route('/stats/clean_cache')
def CleanCacheHandler():
    offline_stat_path = "/tmp/uwsgi_cache"
    import shutil
    try:
        shutil.rmtree(offline_stat_path)
    except Exception as e:
        logger.error(e)
        return jsonify(status=-1, error=e.message)
    return jsonify(status=0)
