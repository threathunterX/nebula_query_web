# -*- coding: utf-8 -*-

import os, logging
import traceback
from datetime import datetime
from os import path as opath

from flask import Blueprint, request, jsonify

from threathunter_common.util import ip_match
from threathunter_common.metrics.metricsagent import MetricsAgent
from threathunter_common.util import millis_now

from nebula_website import settings
from nebula_website import utils, data_client
from nebula_website.data_client import get_online_key_stat
from nebula_website.views import view_util

mod = Blueprint("incident_stat", __name__)

DEBUG_PREFIX = "==============="

logger = logging.getLogger("nebula.web.stat.incident_stat")


@mod.route('/behavior/start_time')
def PersistBeginTimeHandler():
    """
    @API
    summary: 获得最早的持久化数据时间段
    description: 获得最早可用的持久化数据的时间段
    tags:
      - platform
    responses:
      '200':
        description: 返回时间段
        schema:
          $ref: '#/definitions/time_frame'
      default:
        description: Error
        schema:
          $ref: '#/definitions/Error'
    """
    dirs = os.listdir(settings.Persist_Path)
    if not dirs:
        # 0 代表还没有持久化数据文件夹产生
        dirs = [0]
    else:
        dirs.sort()
        for d in dirs:
            if opath.exists(opath.join(settings.Persist_Path, d, 'data')):
                return jsonify(time_frame=utils.get_ts_from_hour(d))
    return jsonify(time_frame=0)



@mod.route('/behavior/statistics')
def IncidentStatsHandler():
    # 应该不用了
    pass


@mod.route('/behavior/clicks_detail')
def ClickDetailHandler():
    # 早就不用了
    pass


@mod.route('/behavior/scene_statistic')
def SceneStatHandler():
    # not now
    pass


@mod.route('/behavior/user_statistics')
def UserStatHandler():
    #确认
    pass


@mod.route('/behavior/top/clicks_location')
def ClickLocation():
    # 确认
    pass


@mod.route('/behavior/continuous_related_statistic')
def ContinuousRelatedStatHandler():
    # 弃用了?
    pass


@mod.route('/behavior/related_statistics')
def RelatedStatisticHandler():
    #@todo 在线离线分开
    """
    每个维度分析页面的左下角的不同维度两两关联的top榜单api
    dict(
        ip=[
            {'value':'',
             'country':'',
             'province':'',
             'city':'',
             'related_key_type':'',
             'count':0}],
        user=[
            {'value':'',
             'related_key_type':'',
             'count':0}
        ],
        did=[{
            'value':'',
            'os':'',
            'device_type':'',
            'related_key_type':'',
            'count':0,}
        ],
        page=[
            {'value':'',
             'related_key_type':'',
             'count':0}
        ],
    )

    @API
    summary: 某个小时内关联数据排行
    description: ''
    tags:
      - platform
    parameters:
      - name: key
        in: query
        description: key_type为page时需要
        required: false
        type: string
      - name: key_type
        in: query
        description: 维度类型
        required: true
        type: string
      - name: related_key_types
        in: query
        description: 关联数据类型
        required: true
        type: string
      - name: fromtime
        in: query
        description: 起始时间
        required: true
        type: integer
        format: int64
      - name: endtime
        in: query
        description: 截止时间
        required: true
        type: integer
        format: int64
    responses:
      '200':
        description: 统计列表
        schema:
          $ref: '#/definitions/relatedStatistics'
      default:
        description: Error
        schema:
          $ref: '#/definitions/Error'
    """
    req = request.args
    fromtime = req.get('fromtime', "")
    endtime = req.get('endtime', "")
    key = req.get("key", "")
    key_type = req.get("key_type", "")
    related_key_types = req.get('related_key_types', "")
    related_key_types = related_key_types.split(',')

    fromtime = int(fromtime) / 1000.0
    endtime = int(endtime) / 1000.0
    logger.debug(DEBUG_PREFIX+u"查询的时间范围是%s ~ %s", datetime.fromtimestamp(fromtime), datetime.fromtimestamp(endtime))

    if not key_type or not related_key_types:
        logger.error('/platform/behavior/related_statistics 没有传入两个关联因素。')
        return jsonify([])
    if key_type == 'page' and not key:
        logger.error('/platform/behavior/related_statistics key_type为page,key为空')
        return jsonify([])

    # 根据key_type和related_key_type得到查询的var_list
    var_list = []
    top_list = []
    temp_dict = {}
    now_in_hour_start = utils.get_hour_start()

    # page维度只关联一个维度
    if key_type == 'page':
        related_type = related_key_types[0]
        page_var_name = 'page__visit__{}_dynamic_count__1h__slot'.format(related_type)
        var_list.append(page_var_name)

        try:
            if fromtime >= now_in_hour_start:
                logger.debug("Entry Current hour, key_type: %s", "page")
                # 当前小时数据,请求Java RPC
                # ret 结构为{variable1: {key1: value1}}
                ret = data_client.get_latest_statistic(key, key_type, var_list)
                top_statistic = ret.values()[0] if ret else {}
            else:
                logger.debug("Entry History hour, key_type: %s", "page")
                # 历史数据,离线计算查询
                # page维度只有单个key查询的值{variable: value}
                # todo
                ret = data_client.get_offline_key_stat(key, key_type, fromtime, var_list)
                top_statistic = ret.values()[0] if ret else {}

            for top, var_value in top_statistic.items():
                v = len(var_value) if isinstance(var_value, (list, set)) else var_value
                top_dict = dict()
                top_dict['value'] = top
                top_dict['related_count'] = v
                if related_type == 'ip':
                    country, province, city = utils.find_ip_geo(top)
                    top_dict['country'] = country
                    top_dict['province'] = province
                    top_dict['city'] = city

                top_list.append(top_dict)

            top_list = sorted(top_list, lambda x, y: cmp(x['related_count'], y['related_count']), reverse=True)[:100]
            return jsonify(top_list)
        except Exception as e:
            logger.error(e)
            return jsonify([])

    # 除了page维度,其他维度可关联两个维度
    else:
        for related_type in related_key_types:
            if related_type == 'click':
                var_list.append('{}__visit__dynamic_count__1h__slot'.format(key_type))
            elif related_type == 'incident':
                var_list.append('{}__visit__incident_count__1h__slot'.format(key_type))
            elif related_type == 'strategy':
                var_list.append('{}__visit__incident_distinct_strategy__1h__slot'.format(key_type))
            else:
                var_list.append('{}__visit__dynamic_distinct_{}__1h__slot'.format(key_type, related_type))
        try:
            if fromtime >= now_in_hour_start:
                logger.debug("Entry Current hour, key_type: %s", key_type)
                if not settings.Enable_Online:
                    return jsonify([])
                # 当前小时数据,请求Java RPC
                # ret数据结构为{"result": {variable1: {key: value} } }
                key_variable = var_list[0]
                ret = data_client.get_latest_baseline_statistic(key_variable, var_list)
                top_statistic = ret.get('result', {}) if ret else {}

                for top, variables in top_statistic.items():
                    top_dict = dict()

                    for i in range(len(related_key_types)):
                        related_type = related_key_types[i]
                        related_var = var_list[i]
                        related_value = variables.get(related_var, 0)
                        v = len(related_value) if isinstance(related_value, (list, set)) else related_value
                        top_dict[related_type] = v

                    temp_dict[top] = top_dict
            else:
                # 根据离线计算查询的数据,得到top key, 例:related_key_types: ['did', 'incident']
                # top_dict {variable1: {key1: set[1, 2, 3, 4]}, variable2: {key1: 3}}
                # temp_dict {key1: {'did': 4, 'incident': 3}}
                logger.debug("Entry History hour, key_type: %s", key_type)
                key = "__GLOBAL__"
                top_statistic = data_client.get_offline_key_stat(key, key_type, fromtime, var_list)
                if top_statistic:
                    for i in range(len(related_key_types)):
                        related_type = related_key_types[i]
                        var = var_list[i]
                        related_values = top_statistic.get(var, {})

                        for top, var_value in (related_values or dict()).items():
                            v = len(var_value) if isinstance(var_value, (list, set)) else var_value
                            if top in temp_dict:
                                temp_dict[top][related_type] = v
                            else:
                                temp_dict[top] = {related_type: v}

            # 将当前小时或离线计算数据组合,top_list例:
            # [{'value': '3', related_count: {'ip': 4, 'did': 5}},
            #  {'value': '4', related_count: {'ip': 10, 'did': 5}}]
            for k, v in temp_dict.items():
                if not k:
                    continue
                top_dict = dict()
                top_dict['value'] = k
                top_dict['related_count'] = {t: v.get(t, 0) for t in related_key_types}

                if key_type == 'ip' and ip_match(k):
                    country, province, city = utils.find_ip_geo(k)
                    top_dict['country'] = country
                    top_dict['province'] = province
                    top_dict['city'] = city

                top_list.append(top_dict)

            order_type = related_key_types[0]
            top_list = sorted(top_list, lambda x, y: cmp(x['related_count'][order_type], y['related_count'][order_type]), reverse=True)[:100]

            return jsonify(top_list)
        except Exception as e:
            logger.error(e)
            return jsonify([])


@mod.route('/behavior/continuous_top_related_statistic')
def ContinuousTopRelatedStatHandler():
    """
    获取指定时间点击数最高的7位用户点击量

    @API
    summary: 获取用户历史点击量
    description: ''
    tags:
      - platform
    parameters:
      - name: from_time
        in: query
        description: 起始时间
        required: true
        type: integer
      - name: end_time
        in: query
        description: 结束时间
        required: true
        type: integer
      - name: key
        in: query
        description: 关键字
        required: true
        type: string
      - name: key_type
        in: query
        description: 关键字类型
        required: true
        type: string
    responses:
      '200':
        description: 返回点击统计列表
        schema:
          $ref: '#/definitions/clickStatistics'
      default:
        description: Error
        schema:
          $ref: '#/definitions/Error'
    """
    req = request.args
    from_time = req.get('from_time', "")
    end_time = req.get('end_time', "")
    key = req.get("key", "")
    key_type = req.get("key_type", "")

    if not (from_time and end_time and key and key_type):
        return jsonify(status=400, msg='parameters error')

    interval = 60 * 60 * 1000
    db = 'default'
    metrics_name = 'click.related.{}'.format(key_type)
    top_related = get_current_top_related(key_type, key)
    top_related_keys = top_related.keys()
    if key_type == 'ip':
        group_tags = ['user']
        filter_tags = {'user': top_related_keys}
    else:
        group_tags = ['ip']
        filter_tags = {'ip': top_related_keys}

    try:
        metrics = MetricsAgent.get_instance().query(db, metrics_name, 'sum', from_time,
                                                    end_time, interval, filter_tags, group_tags)
        click_statistics = {top: [] for top in top_related_keys}
        for time_frame in range(from_time, end_time, interval):
            clicks = metrics.get(time_frame, {})
            related_tops = {tags[0]: int(value) for tags, value in clicks.iteritems()}

            for top in top_related_keys:
                if top in related_tops:
                    click_statistics[top].append(dict(time_frame=time_frame, count=related_tops[top]))
                else:
                    click_statistics[top].append(dict(time_frame=time_frame, count=0))

        ts = utils.get_current_hour_timestamp()
        if end_time > ts:
            for top, count in top_related.iteritems():
                click_statistics[top][-1]['count'] = count

        return jsonify(click_statistics)
    except Exception as e:
        logger.error(e)
        return jsonify(status=400, msg='fail to statistics click')


def get_current_top_related(key_type, key):
    if key_type == 'ip':
        var = 'ip__visit__user_dynamic_count__1h__slot'
    else:
        var = '{}__visit__ip_dynamic_count__1h__slot'.format(key_type)
    variables = data_client.get_latest_statistic(key=key, key_type=key_type, var_list=[var])
    if variables:
        top_related = variables[var]
        sorted_top_related = sorted(top_related.items(), lambda x, y: cmp(x[1], y[1]), reverse=True)
        len_related = 7 if len(sorted_top_related) >= 7 else len(sorted_top_related)
        return {sorted_top_related[i][0]: sorted_top_related[i][1] for i in range(len_related)}

    return False


@mod.route('/behavior/page_statistics')
def RelatedPageStatisticHandler():
    """
    page维度分析的左中的数据表格api
    return:
    {
    total_page:
    data: dict( host = '',
      url = '',
      alarm_count = 0,
      click_count = 0,
      ip_count = 0,
      top_3_ip_click = 0,
      top_3_ip_click_percent = 0,
      user_count = 0,
      top_3_user_click = 0,
      top_3_user_click_percent = 0,
      did_count = 0,
      top_3_did_click=0,
      top_3_did_click_percent=0)
    }

    @API
    summary: 获取某个时间段内Page访问的统计排行情况
    description: 获取一个小时内的页面访问及统计数据分析排行
    parameters:
      - name: endtime
        in: query
        description: 结束时间
        required: true
        type: integer
        format: int64
      - name: fromtime
        in: query
        description: 起始时间
        required: true
        type: integer
        format: int64
      - name: type
        in: query
        type: string
        enum:
          - host
          - url
        required: true
        description: 数据聚合类型
      - name: query
        in: query
        description: 过滤字段
        required: false
        type: string
      - name: query_scope
        in: query
        type: string
        enum:
          - host
          - url
          - all
        description: 查询范围
        required: false
    responses:
      '200':
        description: 返回点击列表
        schema:
          $ref: '#/definitions/pageStatistics'
      default:
        description: Error
        schema:
          $ref: '#/definitions/Error'
    """
    req = request.args
    fromtime = req.get('fromtime', None)
    endtime = req.get('endtime', None)
    ttype = req.get('type', '')
    query = req.get('query', '')
    query_scope = req.get('query_scope', '')
    fromtime = int(fromtime) / 1000.0
    endtime = int(endtime) / 1000.0
    logger.debug(DEBUG_PREFIX+u"查询的时间范围是%s ~ %s", datetime.fromtimestamp(fromtime), datetime.fromtimestamp(endtime))
    # @issue 还不能支持只有url_path段的查询
    # @issue 只填host， 也只是把host当成page来的查的
    ret_list = []

    # vars: blacklist_count_page, click_count_page, ip_distinctcount_page, ip_count_top_byip_page, user_distinctcount_page, user_count_top_byuser_page,
    # 从总的里面找, 也就能搜索了 点击之后没有表格 @确认
    incident_count_var_name = 'page__visit__incident_count__1h__slot'
    incident_count_name = 'incident_count'
    click_count_var_name = 'page__visit__dynamic_count__1h__slot'
    click_count_name = 'click_count'
    ip_count_var_name = 'page__visit__ip_dynamic_count__1h__slot'
    ip_count_name = 'ip_count'
    ip_distinct_var_name = 'page__visit__dynamic_distinct_ip__1h__slot'
    user_count_var_name = 'page__visit__user_dynamic_count__1h__slot'
    user_count_name = 'user_count'
    user_distinct_var_name = 'page__visit__dynamic_distinct_user__1h__slot'
    did_count_var_name = 'page__visit__did_dynamic_count__1h__slot'
    did_count_name = 'did_count'
    did_distinct_var_name = 'page__visit__dynamic_distinct_did__1h__slot'
    ip_top_count_var_name = 'page__visit__ip_dynamic_count__1h__slot'
    ip_top_name = 'top_3_ip_click'
    ip_top_percent_name = 'top_3_ip_click_percent'
    user_top_count_var_name = 'page__visit__user_dynamic_count__1h__slot'
    user_top_name = 'top_3_user_click'
    user_top_percent_name = 'top_3_user_click_percent'
    did_top_count_var_name = 'page__visit__did_dynamic_count__1h__slot'
    did_top_name = 'top_3_did_click'
    did_top_percent_name = 'top_3_did_click_percent'
    var_names = [incident_count_var_name, click_count_var_name, ip_count_var_name, ip_top_count_var_name, user_count_var_name, user_top_count_var_name, did_count_var_name, did_top_count_var_name]

    key_type = 'page'
    now_in_hour_start = utils.get_hour_start()
    logger.debug('fromtime: %s, this hour start timestamp:%s', fromtime, now_in_hour_start)
    logger.debug(DEBUG_PREFIX+u"查询的时间范围是%s ~ %s", datetime.fromtimestamp(fromtime), datetime.fromtimestamp(endtime))
    try:
        if fromtime >= now_in_hour_start:
            logger.debug(DEBUG_PREFIX+"在当前小时去获取...")
            # 当前小时
            # {var: key :}
            var_list = [incident_count_var_name, ip_count_var_name, ip_distinct_var_name, user_count_var_name,
                        user_distinct_var_name, did_count_var_name, did_distinct_var_name]
            ret = data_client.get_latest_baseline_statistic(click_count_var_name, var_list, count=100, topcount=100)
        else:
            ret = data_client.get_offline_baseline(click_count_var_name, key_type, var_names, set(), int(fromtime*1000), count=100, topcount=100)
        if ret:
            page_ret = ret.get('result', dict())
        else:
            page_ret = dict()
        page_dict = dict()
        flag = False
        for url, url_vars in page_ret.iteritems():
            if not flag:
                logger.debug("url: %s, d : %s", url, url_vars)
            url_dict = {}
            host, url_path = utils.parse_host_url_path(url)
            if ttype == 'host':
                key = host
            else:
                url_dict['url'] = url_path
                key = url
            url_dict['host'] = host
            url_dict[incident_count_name] = url_vars.get(incident_count_var_name, 0)
            url_dict[click_count_name] = url_vars.get(click_count_var_name, 0)
            url_dict[ip_count_name] = url_vars.get(ip_distinct_var_name, 0)
            url_dict[ip_top_name] = url_vars.get(ip_count_var_name, {})
            url_dict[did_count_name] = url_vars.get(did_distinct_var_name, 0)
            url_dict[did_top_name] = url_vars.get(did_count_var_name, {})
            url_dict[user_count_name] = url_vars.get(user_distinct_var_name, 0)
            url_dict[user_top_name] = url_vars.get(user_top_count_var_name, {})

            if not flag:
                logger.debug("url_dict: %s", url_dict)
            if key in page_dict:
                page_dict[key][incident_count_name] += url_dict[incident_count_name]
                page_dict[key][click_count_name] += url_dict[click_count_name]
                page_dict[key][ip_count_name] += url_dict[ip_count_name]
                page_dict[key][did_count_name] += url_dict[did_count_name]
                page_dict[key][user_count_name] += url_dict[user_count_name]
                utils.dict_merge(page_dict[key][ip_top_name], url_dict[ip_top_name])
                utils.dict_merge(page_dict[key][did_top_name], url_dict[did_top_name])
                utils.dict_merge(page_dict[key][user_top_name], url_dict[user_top_name])
            else:
                page_dict[key] = url_dict
            if not flag:
                logger.debug("page_dict: %s", page_dict)
                flag = True

        # 获取数据后，计算点击数前三的ip、did、user
        for url, url_vars in page_dict.iteritems():
            # 计算ip_top
            ip_top = url_vars.get(ip_top_name, {})
            ip_top_list = sorted((ip_top or dict()).items(), key=lambda x: x[1], reverse=True)
            ip_top_3 = ip_top_list[:3]
            logger.debug("ip_top_3: %s", ip_top_3)
            url_vars[ip_top_name] = sum([_[1] for _ in ip_top_3])
            url_vars[ip_top_percent_name] = url_vars[ip_top_name] / float(url_vars[click_count_name]) * 100 if url_vars[click_count_name] else 0

            # 计算did_top
            did_top = url_vars.get(did_top_name, {})
            did_top_list = sorted((did_top or dict()).items(), key=lambda x: x[1], reverse=True)
            did_top_3 = did_top_list[:3]
            url_vars[did_top_name] = sum([_[1] for _ in did_top_3])
            url_vars[did_top_percent_name] = url_vars[did_top_name] / float(url_vars[click_count_name]) * 100 if url_vars[click_count_name] else 0

            # 计算user_top
            user_top = url_vars.get(user_top_name, {})
            user_top_list = sorted((user_top or dict()).items(), key=lambda x: x[1], reverse=True)
            user_top_3 = user_top_list[:3]
            url_vars[user_top_name] = sum([_[1] for _ in user_top_3])
            url_vars[user_top_percent_name] = url_vars[user_top_name] / float(url_vars[click_count_name]) * 100 if url_vars[click_count_name] else 0

            ret_list.append(url_vars)
        logger.debug(DEBUG_PREFIX+"过滤的查询词是 %s, 范围是%s, 查询前的大小是%s", str(query), str(query_scope), len(ret_list))
        if query_scope == 'all':
            ret_list = [ _ for _ in ret_list if query in _.get('host','') or query in _.get('url', '')]
        elif query_scope == 'host':
            ret_list = [ _ for _ in ret_list if query in _.get('host','')]
        elif query_scope == 'url':
            ret_list = [ _ for _ in ret_list if query in _.get('url','')]
        # @未来 这个访问的分页, 是在遍历key的时候跳过n个?再限定一下数量?
        ret_list.sort(key=lambda x: x['incident_count'], reverse=True)
        return jsonify(total_page=len(ret_list), data=ret_list[:100])
    except Exception as e:
        logger.error(e)
        return jsonify(status=-1, error=e.message)

# nginx转发到了8080端口（Java-web）
# @mod.route('/online/visit_stream')
# def OnlineVisitStreamHandler():
#     """
#     获取当前小时内一段时间范围内每条记录的 user, 时间戳, 是否有报警
#     当前小时散点图，已经和离线散点图功能上合并，@todo合并api
#     Return:
#     values: [{user:, timestamp:, if_notice:}, ... ]
#     @API
#     summary: 获取一个小时内每30s的访问数据
#     description: 获取一个小时内每30s的访问数据
#     tags:
#       - platform
#     parameters:
#       - name: from_time
#         in: query
#         description: 起始时间
#         required: false
#         type: integer
#         format: int64
#       - name: end_time
#         in: query
#         description: 结束时间
#         required: false
#         type: integer
#         format: int64
#       - name: key
#         in: query
#         description: 名单，可以为IP等
#         required: true
#         type: string
#       - name: key_type
#         in: query
#         description: 事件类型
#         required: true
#         type: string
#     responses:
#       '200':
#         description: 返回点击列表
#         schema:
#           $ref: '#/definitions/clickItems'
#       default:
#         description: Error
#         schema:
#           $ref: '#/definitions/Error'
#     """
#     req = request.args
#     fromtime = req.get('from_time', 0)
#     endtime = req.get('end_time', 0)
#     key = req.get("key", "")
#     key_type = req.get("key_type", "")
#
#     if not fromtime or not endtime or not key or not key_type:
#         return jsonify(status=-1, error='参数不完整, 无法查询')
#     min_ts = int(fromtime)
#     max_ts = int(endtime)
#     try:
#         result = data_client.get_online_visit_stream(key, key_type, min_ts, max_ts)
#         return jsonify(status=0, values=result)
#     except Exception as e:
#         logger.error(e)
#         return jsonify(status=-1, error=e.message)

# 由NGINX转发到Java-web，暂行注释 2018-10-24
# @mod.route('/behavior/visit_stream')
# def OfflineVisitStreamHandler():
#     # 被'/online/visit_stream'取代, 之后合并api @todo
#     req = request.args
#     fromtime = req.get('from_time', 0)
#     endtime = req.get('end_time', 0)
#     key = req.get("key", "")
#     key_type = req.get("key_type", "")
#
#     if not fromtime or not endtime or not key or not key_type:
#         return jsonify(status=-1, error='参数不完整, 无法查询')
#     min_ts = int(fromtime)
#     max_ts = int(endtime)
#     try:
#         result = data_client.get_online_visit_stream(key, key_type, min_ts, max_ts)
#         return jsonify(status=0, values=result)
#     except Exception as e:
#         logger.error(e)
#         return jsonify(status=-1, error=e.message)

# 由NGINX转发到Java-web，暂行注释 2018-10-24
# @mod.route('/online/clicks_period')
# def OnlineClicksPeriodHandler():
#     """
#     获取当前小时内每30s的DYNAMIC event的数量, 暂时没有当前小时
#     产品角度: 各个维度的风险分析，点击流页面， 当点击了某一个小时的访问柱状条之后，会显示每30s的 DYNAMIC event的数量及是否有报警的 数据.
#     Return:
#     values:{ timestamp:{count:, if_notice:}}
#     @API
#     summary: 获取一个小时内每30s的访问数据
#     description: 获取一个小时内每30s的访问数据
#     tags:
#       - platform
#     parameters:
#       - name: from_time
#         in: query
#         description: 起始时间
#         required: false
#         type: integer
#         format: int64
#       - name: end_time
#         in: query
#         description: 结束时间
#         required: false
#         type: integer
#         format: int64
#       - name: key
#         in: query
#         description: 名单，可以为IP等
#         required: true
#         type: string
#       - name: key_type
#         in: query
#         description: 事件类型
#         required: true
#         type: string
#     responses:
#       '200':
#         description: 返回点击列表
#         schema:
#           $ref: '#/definitions/clickItems'
#       default:
#         description: Error
#         schema:
#           $ref: '#/definitions/Error'
#     """
#     # 被'/online/visit_stream'取代, 之后合并api @todo
#     req = request.args
#     fromtime = req.get('from_time', "")
#     endtime = req.get('end_time', "")
#     key = req.get("key", "")
#     key_type = req.get("key_type", "")
#
#     if not fromtime or not endtime or not key or not key_type:
#         return jsonify(status=-1, error='参数不完整, 无法查询')
#     ts = int(fromtime)
#     end_ts = int(endtime)
#     try:
#         result = data_client.get_online_clicks_period(key, key_type, ts, end_ts)
#         return jsonify(status=0, values=result)
#     except Exception as e:
#         logger.error(e)
#         return jsonify(status=-1, error=e.message)

# nginx转发到了8080端口（Java-web） 2018-10-24
# @mod.route('/behavior/clicks_period')
# def OfflineClicksPeriodHandler():
#     # 被'/online/clicks_period'取代, 之后合并api @todo
#     req = request.args
#     fromtime = req.get('from_time', "")
#     endtime = req.get('end_time', "")
#     key = req.get("key", "")
#     key_type = req.get("key_type", "")
#
#     if not fromtime or not endtime or not key or not key_type:
#         return jsonify(status=-1, error='参数不完整, 无法查询')
#     ts = int(fromtime)
#     end_ts = int(endtime)
#     try:
#         result = data_client.get_online_clicks_period(key, key_type, ts, end_ts)
#         return jsonify(status=0, values=result)
#     except Exception as e:
#         logger.error(e)
#         return jsonify(status=-1, error=e.message)

# nginx转发到了8080端口（Java-web） 2018-10-24
# @mod.route('/online/clicks', methods=["POST"])
# def OnlineClickListHandler():
#     """
#     获取当前小时内的点击列表
#     @API
#     summary: 获取时间段内的点击列表
#     description: 获取指定时间段内指定名单的所有点击资料
#     tags:
#       - platform
#     parameters:
#       - name: query_body
#         in: body
#         description: 日志查询条件
#         required: true
#         type: json
#     responses:
#       '200':
#         description: 返回点击列表
#         schema:
#           $ref: '#/definitions/clickItems'
#       default:
#         description: Error
#         schema:
#           $ref: '#/definitions/Error'
#     """
#     query_body = request.json
#     from_time = query_body.get('from_time', 0)
#     end_time = query_body.get('end_time', 0)
#     key = query_body.get('key', '')
#     if key:
#         key = key.encode('utf-8')
#     key_type = query_body.get('key_type', '')
#     size = query_body.get('size', 20)
#     query = query_body.get('query', [])
#
#     if not (from_time and end_time and key and key_type):
#         return jsonify(status=-1, msg="接口参数不能为空")
#     try:
#         result = data_client.get_online_clicks(key, key_type, from_time, end_time, size, query)
#         return jsonify(status=0, values=result)
#     except Exception as e:
#         logger.error(e)
#         return jsonify(status=-1, msg=e.message)

# nginx转发到了8080端口（Java-web）
# @mod.route('/behavior/clicks', methods=["POST"])
# def OfflineClickListHandler():
#     # 被'/online/clicks'取代, 之后合并api @todo
#     query_body = request.json
#     from_time = query_body.get('from_time', 0)
#     end_time = query_body.get('end_time', 0)
#     key = query_body.get('key', '')
#     if key:
#         key = key.encode('utf-8')
#     key_type = query_body.get('key_type', '')
#     size = query_body.get('size', 20)
#     query = query_body.get('query', [])
#
#     if not (from_time and end_time and key and key_type):
#         return jsonify(status=-1, msg="接口参数不能为空")
#     try:
#         result = data_client.get_online_clicks(key, key_type, from_time, end_time, size, query)
#         return jsonify(status=0, values=result)
#     except Exception as e:
#         logger.error(e)
#         return jsonify(status=-1, msg=e.message)


@mod.route('/risks/realtime', methods=["GET"])
def LiveRiskIncident():
    """
    get risk incident realtime list

    @API
    summary: get risk incident realtime list
    notes: risk incident list
    tags:
      - platform
    parameters:
      -
        name: offset
        in: query
        required: false
        type: integer
        description: the page of the list
      -
        name: limit
        in: query
        required: false
        type: integer
        description: the limit of one page
      -
        name: keyword
        in: query
        required: false
        type: string
        description: query key word of the incident
    responses:
      '200':
        description: incidents
        schema:
          $ref: '#/definitions/RiskStatistics'
      default:
        description: Unexcepted error
        schema:
          $ref: '#/definitions/Error'
    """
    req = request.args

    keyword = req.get('keyword', '')
    offset = int(req.get('offset', 1))
    limit = int(req.get('limit', 10))
    blank_return = dict(count=0, items=[], status={i: 0 for i in range(0, 4)})
    logger.debug("uri /risks/realtime settings.enable_online={}".format(settings.Enable_Online))
    if not settings.Enable_Online:
        logging.debug("setting error settings.enable_online is not open")
        return jsonify(blank_return)

    incident_statistics = get_realtime_incident(offset, limit, keyword)
    if not incident_statistics:
        incident_statistics = dict(count=0, items=[])

    try:
        incident_statistics['status'] = {i: 0 for i in range(0, 4)}
        if 'total_count' in incident_statistics:
            incident_statistics['status'][0] = incident_statistics.get('total_count', 0)
            del incident_statistics['total_count']

        return jsonify(incident_statistics)
    except Exception as e:
        logger.error(e)
        return jsonify(dict(status=400, msg='fail to statistic risks'))


def get_realtime_incident(page, limit, keyword):
    try:
        incident_statistics = {}
        key_variable = 'ip__visit_incident_score_top100__1h__slot'
        top100 = get_online_key_stat(['__GLOBAL__'], 'ip', millis_now(), [key_variable])
        top100 = top100['__GLOBAL__'][key_variable]['value']
        top100 = [_['key']for _ in top100]

        detail_variables = [
            'ip__visit_incident_first_timestamp__1h__slot',
            'ip__visit_dynamic_distinct_count_uid__1h__slot',
            'ip_page__visit_dynamic_count_top20__1h__slot',
            'ip_scene_strategy__visit_incident_group_count__1h__slot',
            'ip_uid__visit_dynamic_count_top20__1h__slot',
            'ip_did__visit_dynamic_count_top20__1h__slot',
            'ip_tag__visit_incident_count_top20__1h__slot',
            'ip__visit_incident_max_rate__1h__slot'
        ]
        if top100:
            detail = get_online_key_stat(top100, 'ip', millis_now(), detail_variables)
        else:
            detail = {}
        incident_list = list()

        if top100:
            for key in top100:
                if not ip_match(key):
                    continue

                if keyword and keyword not in key:
                    continue

                key_detail = detail[key]

                incident = dict()
                incident['ip'] = key
                incident['associated_events'] = list()
                incident['start_time'] = key_detail.get(
                    'ip__visit_incident_first_timestamp__1h__slot', {}).get('value') or 0
                strategy_detail = key_detail.get('ip_scene_strategy__visit_incident_group_count__1h__slot', {}).get('value', {})
                strategy_detail = view_util.mapping_name_to_visual(strategy_detail)
                incident['strategies'] = strategy_detail
                incident['hit_tags'] = key_detail.get('ip_tag__visit_incident_count_top20__1h__slot', {}).get('value', [])
                incident['risk_score'] = key_detail.get('', 0)
                incident['uri_stems'] = key_detail.get('ip_page__visit_dynamic_count_top20__1h__slot', {}).get('value', [])
                incident['hosts'] = dict()
                for item in incident['uri_stems']:
                    uri = item['key']
                    count = item['value']
                    host, _ = utils.parse_host_url_path(uri)
                    if incident['hosts'].get(host, None):
                        incident['hosts'][host] += count
                    else:
                        incident['hosts'][host] = count
                incident['associated_users'] = key_detail.get('ip_uid__visit_dynamic_count_top20__1h__slot', {}).get('value', [])
                incident['users_count'] = len(incident['associated_users'])
                incident['dids'] = key_detail.get('ip_did__visit_dynamic_count_top20__1h__slot', {}).get('value', [])
                incident['most_visited'] = sorted(incident['uri_stems'], lambda x, y: cmp(
                    x['value'], y['value']), reverse=True)[0]['key'] if incident['uri_stems'] else ''
                incident['peak'] = key_detail.get('ip__visit_incident_max_rate__1h__slot', {}).get('value', 0)
                incident['associated_orders'] = dict()
                incident['status'] = ''
                incident_list.append(incident)

            incident_list.sort(key=lambda v: v['start_time'], reverse=True)
            total_count = len(incident_list)
            incident_list = incident_list[((page-1) * limit):(page*limit)]
            incident_statistics['items'] = incident_list
            incident_statistics['total_count'] = total_count

        incident_statistics['count'] = len(top100)
        return incident_statistics
    except:
        logger.error(traceback.format_exc())
        return incident_statistics
