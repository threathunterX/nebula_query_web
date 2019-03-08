# -*- coding: utf-8 -*-

import logging, traceback, csv, time
from os import path as opath
from datetime import datetime
from collections import Counter
import codecs

from nebula_website import utils
from nebula_website.cache import get_strategy_weigh
from nebula_website.models import db

import simplejson as json
from flask import Blueprint, request, jsonify, current_app, make_response, abort
from sqlalchemy import text
import gevent

from threathunter_common.metrics.metricsagent import MetricsAgent

mod = Blueprint("db_stat", __name__)

DEBUG_PREFIX = "==============="

#logger = logging.getLogger("nebula.web.stat.db_stat")
#logger = current_app.logger

VN_Query = text("SELECT decision, COUNT(decision) FROM notice WHERE expire > :timestamp AND test = FALSE GROUP BY decision")

NTC_Query = text("SELECT geo_city, COUNT(geo_city) as `count`, scene_name from notice WHERE timestamp >= :fromtime and timestamp <= :endtime GROUP BY scene_name, geo_city")

NSD_URL_Query = text('SELECT uri_stem, count(uri_stem) FROM notice WHERE timestamp >= :fromtime AND timestamp <= :endtime GROUP BY uri_stem ORDER BY count(uri_stem);')

NSD_STRATEGY_Query = text('SELECT strategy_name, test, remark, count(strategy_name) FROM notice WHERE timestamp >= :fromtime AND timestamp <= :endtime GROUP BY strategy_name, test ORDER BY count(strategy_name);')

NSD_LOCATION_QUERY = text('SELECT geo_city, count(geo_city) FROM notice WHERE timestamp >= :fromtime AND timestamp <= :endtime GROUP BY geo_city ORDER BY count(geo_city);')

#NS_Query = text('SELECT unix_timestamp(from_unixtime(timestamp/1000,"%Y:%m:%d %H:00:00"))*1000, count(*) FROM notice WHERE timestamp >= :fromtime AND timestamp <= :endtime AND test = :test GROUP BY from_unixtime(timestamp/1000, "%Y:%m:%d %H")')
NS_Query = text("SELECT count(*) FROM notice WHERE timestamp >= :fromtime AND timestamp < :endtime AND test = :test")

IS_Query = text("SELECT count(*) FROM risk_incident WHERE start_time >= :fromtime AND start_time < :endtime;")

#IS_Query = text('SELECT unix_timestamp(from_unixtime(start_time/1000,"%Y:%m:%d %H:00:00"))*1000, count(*) FROM risk_incident WHERE start_time >= :fromtime AND start_time <= :endtime GROUP BY from_unixtime(start_time/1000, "%Y:%m:%d %H")')

Strategy_Query = text("""SELECT strategy_name, count(strategy_name) as strategy_count FROM notice WHERE timestamp >= :fromtime and timestamp <= :endtime and scene_name = :scene GROUP BY count(strategy_name)""")

Tag_Query = text("""SELECT strategy_name, count(strategy_name) as strategy_count FROM notice WHERE timestamp >= :fromtime and timestamp <= :endtime GROUP BY count(strategy_name)""")

DPS_Spider_Query = text("""SELECT timestamp as min_ts,max(timestamp) as max_ts,geo_city,decision,test,strategy_name,tag,notice_stat.key as `key`, check_type,sum(notice_stat.count) as `count` from notice_stat where uri_stem=:uri_stem and timestamp>=:fromtime and timestamp<=:endtime and scene_name="VISITOR" and (tag like :query or uid like :query or geo_city like :query or ip like :query) group by ip;""")

DPS_Spider_No_Query = text("""SELECT timestamp as min_ts,max(timestamp) as max_ts,geo_city,decision,test,strategy_name,tag,notice_stat.key as `key`, check_type,sum(notice_stat.count) as `count` from notice_stat where uri_stem=:uri_stem and timestamp>=:fromtime and timestamp<=:endtime and scene_name="VISITOR" group by ip;""")

DPS_Account_Query = text("""SELECT uid,timestamp as min_ts,max(timestamp) as max_ts,ip,geo_city,decision,test,strategy_name,tag,notice_stat.key as `key`,sum(notice_stat.count) as `count` from notice_stat where timestamp>=:fromtime and timestamp<=:endtime and scene_name="ACCOUNT" and uri_stem=:uri_stem and (tag like :query or uid like :query or geo_city like :query or ip like :query) group by ip,uid;""")

DPS_Account_No_Query = text("""SELECT uid,timestamp as min_ts,max(timestamp) as max_ts,ip,geo_city,decision,test,strategy_name,tag,notice_stat.key as `key`,sum(notice_stat.count) as `count` from notice_stat where timestamp>=:fromtime and timestamp<=:endtime and scene_name="ACCOUNT" and uri_stem=:uri_stem group by ip,uid;""")

"""
select * from notice_stat where uri_stem='u.panda.tv/ajax_aeskey';

select min(timestamp) as min_ts,max(timestamp) as max_ts,scene_name,uid,ip,geo_city,strategy_name,tag,notice_stat.key as `key`, check_type, sum(notice_stat.count) as `count` from notice_stat where uri_stem='u.panda.tv/ajax_aeskey' and scene_name="VISITOR" group by ip;

mysql> select uid,ip,geo_city,strategy_name,tag,notice_stat.key, check_type, sum(notice_stat.count),decision,test from notice_stat where uri_stem='u.panda.tv/ajax_aeskey' group by ip;
+------+--------------+-----------+-------------------+--------+--------------+------------+------------------------+
| uid  | ip           | geo_city  | strategy_name     | tag    | key          | check_type | sum(notice_stat.count) |
+------+--------------+-----------+-------------------+--------+--------------+------------+------------------------+
| NULL | NULL         | 美国      | visit_serverua_ip | 撞库   | 162.77.204.2 | IP         |                     76 |
|      | 162.77.204.2 | 美国      | visit_serverua_ip | 撞库   | 162.77.204.2 | IP         |                     12 |
|      | 23.62.114.93 | 荷兰      | visit_serverua_ip | 撞库   | 23.62.114.93 | IP         |                     12 |
|      | 68.149.11.19 | 加拿大    | visit_serverua_ip | 撞库   | 68.149.11.19 | IP         |                     12 |
|      | 90.61.65.109 | 法国      | visit_serverua_ip | 撞库   | 90.61.65.109 | IP         |                     12 |
+------+--------------+-----------+-------------------+--------+--------------+------------+------------------------+
"""


def NTC_Stat_Query(DB_Engine, fromtime, endtime, result_dict=None):
    if result_dict is None:
        result_dict = dict()
    
    for _ in ("account_attack_top", "http_attack_top", "fraud_attack_top",
              "other_attack_top"):
        if not result_dict.has_key(_):
            result_dict[_] = Counter()
    
    q = DB_Engine.execute(Strategy_Query, fromtime=fromtime, endtime=endtime)
    
    for geo_city, count, scene_name in q.fetchall():
        if scene_name == "OTHER":
            c = result_dict["other_attach_top"]
        elif scene_name == "VISITOR":
            c = result_dict["http_attach_top"]
        elif scene_name == "ACCOUNT":
            c = result_dict["account_attack_top"]
        elif scene_name in ("ORDER","TRANSACTION", "MARKETING"):
            c = result_dict["fraud_attack_top"]
        else:
            c = result_dict["other_attach_top"]
            current_app.logger.warn("Notice Top City Statistic unknown scene_name : %s", scene_name)
        c[geo_city] = count

    return result_dict


@mod.route('/noticestats', methods=["GET"])
def NoticeTopCityStat():
    """
    Get top 10 cities notice stats

    @API
    summary: Get top 10 cities notice stats
    notes: get top 10 cities with more notices than others
    tags:
      - platform
    parameters:
      -
        name: duration
        in: query
        required: false
        type: long
        default: 3600
        description: the result notices should have timestamp in the past duration
    produces:
      - application/json
    """
    req = request.args
    duration = int(req.get('duration', 3600))
    query_result = dict()
    endtime = int(time.time() * 1000)
    fromtime = endtime - duration * 1000
    DB_Engine = db.get_engine()
    
    with gevent.Timeout(10, False):
        try:
            gs = [gevent.spawn(NTC_Stat_Query,DB_Engine, fromtime, endtime, query_result), ]
            gevent.joinall(gs, timeout=8, count=len(gs), raise_error=True)
        except Exception:
            current_app.logger.error(traceback.format_exc())
        finally:
            if gs:
                gevent.killall(gs, block=False)
                
    # format
    result = dict()
    for k, c in query_result.iteritems():
        result[k] = [ dict(name=_[0], value=_[1]) for _ in c.most_common(10) ]
    return jsonify(result)
    

def VN_Stat_Query(DB_Engine, result_dict=None):
    if result_dict is None:
        result_dict = dict()
    
    now = int(time.time() * 1000)
    q = DB_Engine.execute(timestamp=now)
    
    for decision, count in q.fetchall():
        result_dict[decision] = count
        
    return result_dict
    

@mod.route('/alarm/valid_count', methods=["GET"])
def ValidNoticeStat():
    """
    Get the valid alarm count

    @API
    summary: valid alarm count
    notes: Get the valid alarm count
    tags:
      - platform
    produces:
      - application/json
    """
    query_result = dict()
    DB_Engine = db.get_engine()
    
    with gevent.Timeout(4, False):
        try:
            gs = [gevent.spawn(VN_Stat_Query, DB_Engine, query_result), ]
            gevent.joinall(gs, timeout=3, count=len(gs), raise_error=True)
        except Exception:
            current_app.logger.error(traceback.format_exc())
        finally:
            if gs:
                gevent.killall(gs, block=False)
                
    # format
    result = dict()
    result["incident_list"] = query_result.get("review", 0) + query_result.get("reject", 0)
    result["white_list"] = query_result.get("accept", 0)
    return jsonify(result)

# 2018-10-16 注释，此接口已由nginx转发到8080端口（java-web）

# @mod.route('/network/statistics', methods=["GET"])
# def TrafficStat():
#     """
#     获取metrics网络流量统计数据
#     @API
#     summary: all the http count
#     notes: 获取网络流量统计数据
#     tags:
#       - platform
#       - metrics
#     produces:
#       - application/json
#     """
#     minute = 60 * 1000
#     hour = 60 * minute
#     interval = 5 * minute
#     now = int(time.time() * 1000)
#     endtime = now - (now % interval)
#     fromtime = endtime - hour
#     try:
#         network_statistics = MetricsAgent.get_instance().query(
#             'nebula.online', 'events.income.count', 'sum', fromtime, endtime, interval)
#     except Exception as e:
#         current_app.logger.error(e)
#         return jsonify(dict(status=-1, msg='fail to get metrics'))
#
#     # 按照时间戳顺序解析network statistics结果
#     statistics_timeframe = network_statistics.keys()
#     network_list = list()
#     try:
#         for time_frame in range(fromtime, endtime, interval):
#             network = dict(time_frame=time_frame, count=0)
#
#             if time_frame in statistics_timeframe:
#                 ts_data = network_statistics[time_frame]
#                 for legend, value in ts_data.iteritems():
#                     network['count'] = int(value)
#
#             network_list.append(network)
#
#         return jsonify(network_list)
#     except Exception as e:
#         current_app.logger.error(e)
#         return jsonify(dict(status=-1, msg='fail to get network statistics'))


@mod.route('/alarm/statistics_detail', methods=["GET"])
def NoticeStatDetail():
    """
    Get the assorted alarm statistics detail for the specified period of time
    获取时间范围内报警的url, location, strategy榜单。
    @总览首页

    @API
    summary: alarm statistics detail
    notes: Get the assorted alarm statistics detail for the specified period of time
    tags:
      - platform
    parameters:
      -
        name: fromtime
        in: query
        required: true
        type: integer
        description: start time
      -
        name: endtime
        in: query
        required: true
        type: integer
        description: end time
    produces:
      - application/json
    """
    req = request.args
    fromtime = int(req.get('fromtime', 0))
    endtime = int(req.get('endtime', 0))
    query_result = {'url': [], 'location': [], 'strategy': []}
    now_in_hour_start = utils.get_hour_start() * 1000
    
    if not all(_ for _ in (fromtime, endtime)):
        return abort_response(400, "fromtime, endtime query args are required.")

    app = current_app._get_current_object()
    DB_Engine = db.get_engine()
    current_app.logger.error("""当前小时开始时间 %s\n查询开始时间:%s, 查询结束时间:%s,
                             允许当前小时模块查询? %s""",
                             datetime.fromtimestamp(now_in_hour_start/1000.0),
                             datetime.fromtimestamp(fromtime/1000.0),
                             datetime.fromtimestamp(endtime/1000.0),
                             not app.config["Enable_Online"])

    if fromtime >= now_in_hour_start and not app.config["Enable_Online"]:
        return jsonify(query_result)
        
    
    def url_query(fromtime, endtime, query_result):
        result = DB_Engine.execute(NSD_URL_Query, fromtime=fromtime, endtime=endtime)
        for url, count in result.fetchall():
            query_result['url'].append({'value': url, 'count': count})

    def location_query(fromtime, endtime, query_result):
        result = DB_Engine.execute(NSD_LOCATION_QUERY, fromtime=fromtime, endtime=endtime)
        for location, count in result.fetchall():
            query_result['location'].append(
                {'value': location, 'count': count})
    
    def strategy_query(fromtime, endtime, query_result):
        result = DB_Engine.execute(NSD_STRATEGY_Query, fromtime=fromtime, endtime=endtime)
        for strategy, test, remark, count in result.fetchall():
            query_result['strategy'].append(
                {'value': strategy, 'test': bool(test), 'remark': remark, 'count': count})
            
    querys = (url_query, location_query, strategy_query)
    gs = None
    with gevent.Timeout(10, False):
        try:
            gs = [gevent.spawn(_, fromtime, endtime, query_result) for _ in querys]
            gevent.joinall(gs, timeout=5, count=len(gs), raise_error=True)
        except Exception:
            current_app.logger.error(traceback.format_exc())
        finally:
            if gs:
                gevent.killall(gs, block=False)

    return jsonify(query_result)


def NS_Stat_Query(DB_Engine, fromtime, endtime, is_test=True, result_dict=None):
    if result_dict is None:
        result_dict = dict()
    
    test = 1 if is_test else 0
    q = DB_Engine.execute(NS_Query, fromtime=fromtime, endtime=endtime,
                          test=test)
    
    r = q.fetchone()
    count = 0
    if r:
        count = r[0]

    if result_dict.has_key(fromtime):
        d = result_dict[fromtime]
    else:
        d = result_dict[fromtime] = dict()

    if is_test:
        d["test_count"] = count
    else:
        d["production_count"] = count
        
    return result_dict


@mod.route("/alarm/statistics", methods=["GET"])
def NoticeStat():
    """
    Get the alarm statistics for the specified period of time
    获取一段时间内每小时的风险名单的测试、生产的数量统计
    @风险名单管理 页面顶部曲线图

    @Return:
    [{"production_count": 0, "test_count": 0, "time_frame": 1491901200000}, {"production_count": 0, "test_count": 0, "time_frame": 1491904800000}]
    
    @API
    summary: alarm statistics
    notes: Get the alarm statistics for the specified period of time
    tags:
      - platform
    parameters:
      -
        name: fromtime
        in: query
        required: true
        type: integer
        description: start time
      -
        name: endtime
        in: query
        required: true
        type: integer
        description: end time
    produces:
      - application/json
    """
    req = request.args
    fromtime = int(req.get('fromtime', 0))
    endtime = int(req.get('endtime', 0))
    current_app.logger.error("""查询开始时间:%s, 查询结束时间:%s""",
                             datetime.fromtimestamp(fromtime/1000.0),
                             datetime.fromtimestamp(endtime/1000.0))
    if not all(_ for _ in (fromtime, endtime)):
        return abort_response(400, "fromtime, endtime query args are required.")

    hours = map( lambda x: int(x*1000),
                 utils.get_hour_strs_fromtimestamp(fromtime/1000.0, endtime/1000.0))
    hours.append(endtime)
    gs = None
    query_result = dict()
    app = current_app._get_current_object()
    DB_Engine = db.get_engine()
    with gevent.Timeout(15, False):
        try:
            gs = [ gevent.spawn(NS_Stat_Query, DB_Engine, _, hours[i+1], is_test, query_result)
                   for i,_ in enumerate(hours[:-1]) for is_test in (True, False)]
            
#            gs = [gevent.spawn(NS_Stat_Query, fromtime, endtime, _, query_result)
#                  for _ in (True, False)]
            gevent.joinall(gs, timeout=12, count=len(gs), raise_error=True)
        except Exception:
            current_app.logger.error(traceback.format_exc())
        finally:
            if gs:
                gevent.killall(gs, block=False)
                
    # format
    result = []
    for ts, d in query_result.iteritems():
        d["time_frame"] = ts
        result.append(d)
    result.sort(key=lambda x:x["time_frame"])
    return jsonify(result)


def IS_Stat_Query(DB_Engine, fromtime, endtime, result_dict=None):
    if result_dict is None:
        result_dict = dict()
    
    q = DB_Engine.execute(IS_Query, fromtime=fromtime, endtime=endtime)
    
    r = q.fetchone()
    count = 0
    if r:
        count = r[0]
    result_dict[fromtime] = count
#    for ts, count in q.fetchall():
#        result_dict[ts] = count
        
    return result_dict


@mod.route("/risks/statistics", methods=["GET"])
def IncidentStat():
    """
    get risk incident statistics list
    获取一段时间内风险事件的统计曲线。
    @风险事件管理 页面 顶部统计曲线图
    @Return
    [{"1491901200000": 0}, {"1491904800000": 0}, {"1491908400000": 0}, {"1491912000000": 0}, {"1491915600000": 0}]

    @API
    summary: get risk incident statistics list
    notes: list split every hour
    tags:
      - platform
    parameters:
      -
        name: start_time
        in: query
        required: true
        type: integer
        description: start time of the list
      -
        name: end_time
        in: query
        required: true
        type: integer
        description: start time of the list
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
    fromtime = int(req.get('start_time', 0))
    endtime = int(req.get('end_time', 0))
#    fromtime = int(req.get('fromtime', 0))
#    endtime = int(req.get('endtime', 0))
    
    current_app.logger.error("""查询开始时间:%s, 查询结束时间:%s""",
                             datetime.fromtimestamp(fromtime/1000.0),
                             datetime.fromtimestamp(endtime/1000.0))
    if not all(_ for _ in (fromtime, endtime)):
        return abort_response(400, "fromtime, endtime query args are required.")

    hours = map( lambda x: int(x*1000),
                 utils.get_hour_strs_fromtimestamp(fromtime/1000.0, endtime/1000.0))
    
    gs = None
    query_result = dict()
    DB_Engine = db.get_engine()
    with gevent.Timeout(10, False):
        try:
            gs = [ gevent.spawn(IS_Stat_Query, DB_Engine, _, hours[i+1], query_result)
                   for i,_ in enumerate(hours[:-1])]
                
#            gs = [gevent.spawn(IS_Stat_Query, fromtime, endtime, query_result)]
            gevent.joinall(gs, timeout=5, count=len(gs), raise_error=True)
        except Exception:
            current_app.logger.error(traceback.format_exc())
        finally:
            if gs:
                gevent.killall(gs, block=False)

    # format
    result = [ {ts:query_result.get(ts,0)} for ts in xrange(fromtime, endtime, 3600000)]
    return jsonify(result)


def SS_Stat_Query(DB_Engine, fromtime, endtime, scene, result_dict=None):
    if result_dict is None:
        result_dict = dict()
    
    q = DB_Engine.execute(Strategy_Query, fromtime=fromtime, endtime=endtime,
                          scene=scene)
    
    for strategy, count in q.fetchall():
        result_dict[strategy] = count
    return result_dict


@mod.route("/behavior/strategy_statistic", methods=["GET"])
def StrategyStat():
    """
    获取各场景的命中策略统计前8的榜单
    @策略管理 页面 顶部 左侧
    @Return
    [{strategy1:0}, {strategy2:0}]

    @API
    summary: 获取时间段内的每个小时的命中策略统计数
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
      - name: scene
        in: query
        description: 策略场景
        required: true
        type: string
    """
    req = request.args
    fromtime = int(req.get('from_time', 0))
    endtime = int(req.get('end_time', 0))
    scene = req.get("scene", "")
#    fromtime = int(req.get('fromtime', 0))
#    endtime = int(req.get('endtime', 0))
    current_app.logger.error("""查询开始时间:%s, 查询结束时间:%s, 查询的场景: %s""",
                             datetime.fromtimestamp(fromtime/1000.0),
                             datetime.fromtimestamp(endtime/1000.0), scene)
    if not all(_ for _ in (fromtime, endtime, scene)):
        return abort_response(400, "fromtime, endtime, scene query args are required.")

    DB_Engine = db.get_engine()
    query_result = dict()
    with gevent.Timeout(10, False):
        try:
            gs = [gevent.spawn(SS_Stat_Query, DB_Engine, fromtime, endtime, scene, query_result), ]
            gevent.joinall(gs, timeout=5, count=len(gs), raise_error=True)
        except Exception:
            current_app.logger.error(traceback.format_exc())
        finally:
            if gs:
                gevent.killall(gs, block=False)
    # format
    result = [ dict(strategy=count) for strategy, count in query_result.iteritems()]
    return jsonify(result)


def TS_Stat_Query(DB_Engine, fromtime, endtime, result_dict=None):
    if result_dict is None:
        result_dict = dict()
    
    q = DB_Engine.execute(Strategy_Query, fromtime=fromtime, endtime=endtime)
    
    for strategy, count in q.fetchall():
        result_dict[strategy] = count
    return result_dict


@mod.route('/behavior/tag_statistics', methods=["GET"])
def TagStat():
    """
    获取当前小时tags的统计
    @监控大屏 页面
    @Return
    [ {'name':tag, 'count':1}, {'name':tag, 'count':0} ]

    @API
    summary: 获取当前小时tags的统计
    description: ''
    tags:
      - platform
    """
    fromtime = utils.get_hour_start() * 1000
    endtime = int(time.time() * 1000)
    query_result = dict()
    DB_Engine = db.get_engine()
    
    with gevent.Timeout(10, False):
        try:
            gs = [gevent.spawn(TS_Stat_Query, DB_Engine, fromtime, endtime, query_result), ]
            gevent.joinall(gs, timeout=5, count=len(gs), raise_error=True)
        except Exception:
            current_app.logger.error(traceback.format_exc())
        finally:
            if gs:
                gevent.killall(gs, block=False)

    result = []
    tmp_dict = dict()
    # format
    strategy_weighs = get_strategy_weigh()
    if strategy_weighs:
        for strategy, count in query_result.iteritems():
            tags = strategy_weighs.get(strategy, {}).get('tags', [])
            for tag in tags:
                utils.dict_merge(tmp_dict, dict(tag=count))
        sorted_tags = sorted(tmp_dict.items(), lambda x, y: cmp(x[1], y[1]),
                             reverse=True)[:10]
        result = [{'name': tag, 'count': count} for tag, count in sorted_tags]
    return jsonify(result)


@mod.route("/stats/dashboard_page_search",methods=["GET", "POST"])
def DashboardPageSearch():
    """
    获取关于某一个page的风险信息
    @爬虫、账户 Dashboard 页面
    @Return
    {
    "status": 0,
    "values":[
    {"key":"",
     "first_time": "HH:mm:ss",
     "last_time": "HH:mm:ss",
     "risk_score": 10,
     "is_test": true,
     "is_white": true,
     "origin": [{"source_ip":"1.1.1.1",
                 "geo_city" :"",
                 "tags":{"爬虫":100, "访客":100}
                 }]
    }],
    "total_count": 10
    }
    
    @API
    summary: get a page statistics from dashboard.
    notes: get a page statistics from dashboard.
    tags:
      - platform
    parameters:
      -
        name: uri_stem
        in: query
        required: true
        type: string
        description: a page url with args.
      -
        name: fromtime
        in: query
        required: true
        type: integer
        description: search start time
      -
        name: endtime
        in: query
        required: true
        type: integer
        description: search end time
      -
        name: dashboard
        in: query
        required: true
        type: string
        description: source dashboard, ex. spider, account
      -
        name: page
        in: query
        required: true
        type: integer
        description: the which page of data list
      -
        name: page_limit
        in: query
        required: true
        type: integer
        description: the size of one data page
      -
        name: query
        in: query
        required: false
        type: string
        description: query
    produces:
      - application/json

    """
    # =============== Request Input Args ===============
    req = request.args
    fromtime = int(req.get('fromtime', 0))
    endtime = int(req.get('endtime', 0))
    page = int(req.get("page",1))
    page_limit = int(req.get("page_limit",20))
    query = req.get("query")
    uri_stem = req.get("uri_stem")
    dashboard_type = req.get("dashboard", "account")
    
    start_offset = (page-1) * page_limit
    end_offset = start_offset + page_limit
    if not all(_ for _ in (fromtime, endtime, uri_stem)):
        return abort_response(400, "uri_stem, fromtime, endtime query args are required.")
    
    # 如果查询的是当天的数据，endtime会以半个小时做缓存.
    # 因为API会以查询条件做本地文件缓存, 所以当天如果以当天最晚时间来查询，会缓存第一次查询的数据，之后打的数据就无法展示
    # @totest
    now = time.time()
    half_hour_seconds = 1800 # half hour have 1800 sec
    current_app.logger.debug("input endtime:%s, now:%s", endtime, int(now*1000))
    if endtime >= int(now * 1000):
        hour_start = utils.get_hour_start(now)
        if now >= hour_start + half_hour_seconds:
            endtime = int((hour_start + half_hour_seconds) * 1000)
        else:
            endtime = int(hour_start*1000)
    current_app.logger.debug("fixed endtime:%s, now:%s", endtime, int(now*1000))

    download_prefix = "/download/" # for nginx api route
    tmp_fn = "DPS-%s-%s-%s-%s.csv" % (uri_stem.replace("/", ""), fromtime, endtime, query)
    tmp_count_fn = "DPS-%s-%s-%s-%s_count" % (uri_stem.replace("/",""), fromtime, endtime, query)
    if opath.exists("/data/tmp"):
        tmp_dir = "/data/tmp"
    else:
        tmp_dir = "./"
    
    fp = opath.join(tmp_dir, tmp_fn)
    tmp_count_fn = opath.join(tmp_dir, tmp_count_fn)
    current_app.logger.debug("check for file: %s", fp)
    query_result = dict()
    msg = list()
    
    account_cols = ("key", "first_time", "last_time", "risk_score", "is_test", "is_white", "origin")
    spider_cols = ("key", "first_time", "last_time", "key_type", "is_test", "is_white", "ratio", "geo_city", "tags")
        
    AccountDashboardType = "account"
    SpiderDashboardType = "spider"
    
    query_map = {
        AccountDashboardType:(DPS_account_query, account_cols),
        SpiderDashboardType:(DPS_spider_query, spider_cols)
    }
    if not query_map.has_key(dashboard_type):
        return abort_response(400, "Invalid dashboard %s" % dashboard_type)
    
    query_func,show_cols = query_map.get(dashboard_type)
    # 相同查询条件产生的数据文件已经产生.
    if opath.exists(fp):
        if request.method == "GET":
            # 翻页
            result = []
            try:
                result = DPS_read_fn(fp, start_offset, end_offset, show_cols, result)
                total = DPS_read_count(tmp_count_fn)
            except AttributeError:
                # the local file don't match input show_cols
                # Perhaps the local file is modify by hand.
                msg.append(traceback.format_exc())
            return jsonify(dict(status=0, values=result, total_count=total,
                                msg=msg))
        elif request.method == "POST":
            # 导出
            return jsonify({"status":0,
                            "file":download_prefix+tmp_fn})
        abort(405)#405 method not allowed
        return 

    # 没有文件，查询，写入文件，返回
    query_result = []
    result_dict = dict()
    err = None
    DB_Engine = db.get_engine()

    # 查询
    with gevent.Timeout(10, False):
        try:
            g = gevent.spawn(query_func, DB_Engine, fromtime, endtime,
                             uri_stem, query, result_dict)
            g.link_exception(lambda x: logging.warn('{0}'.format(x.exception)))
            gevent.joinall([g, ], raise_error=True)
        except Exception:
            gevent.killall([g,], block=False)
            err = traceback.format_exc()
            current_app.logger.error("Exception when query notice_stat: %s", err)

    # if can't gain query data, quit.
    if not result_dict:
        return abort_response(503, "There is no data.")

    # output format
    for k,v in result_dict.iteritems():
        if k == "total":
            # total is special key for count total
            continue

        r = dict()
        # required cols
        if dashboard_type == AccountDashboardType:
            r["key"] = k
        elif dashboard_type == SpiderDashboardType:
            r["key"] = v["key"]

        for _ in ("is_test", "is_white"):
            r[_] = v[_]
        for _ in ("first_time", "last_time"):
            r[_] = datetime.fromtimestamp(v[_] / 1000.0).strftime("%H:%M:%S")
        
        # optional cols
        for _ in ("key_type", "tags", "geo_city"):
            if v.has_key(_):
                r[_] = v[_]
        
        if v.has_key("count"):
            r["ratio"] =  v["count"]/ float(result_dict["total"] or 1) *100
        if v.has_key("strategys"):
            r["risk_score"] = DPS_get_risk_score(v.pop("strategys"))
        if v.has_key("origin"):
            ip_dicts = v.pop("origin", dict())
            r["origin"] = [ _ for _ in ip_dicts.itervalues()]
        query_result.append(r)
    
    if dashboard_type == AccountDashboardType:
        query_result = sorted(query_result, key=lambda x: x["risk_score"], reverse=True)
    elif dashboard_type == SpiderDashboardType:
        query_result = sorted(query_result, key=lambda x: x["ratio"], reverse=True)

    # 写入文件
    try:
        if query_result:
            # 查询不到数据不会写到文件，否则一旦有文件，就不会再查询了
            DPS_write_fn(fp, show_cols, query_result)
            DPS_write_count(tmp_count_fn, len(query_result))
    except IOError:
        msg.append(["IOError when save query result to disk: %s" % traceback.format_exc()])

    # 返回
    if request.method == "GET":
        return jsonify(dict(status=0, total_count=len(query_result), msg=msg,
                            values=query_result[start_offset:end_offset]))
    elif request.method == "POST":
        return jsonify({"status":0,
                        "file":download_prefix+tmp_fn,
                        "msg":msg})
    # only if method besides get and post
    abort(405)
    return
    
    # 拼名字 DPS-uri-fromtime-endtime-query.csv
    # total count file: DPS-uri-fromtime-endtime-query_count
    # 清理原则 每天清理一下/data/tmp/DPS-*
    # GET:
    # 如果有文件，返回(page-1)*page_limit ~ (page-1)*page_limit +page_limit行
    # 没有文件, 查询, 写入文件, 返回
    # POST:
    # 如果有文件，返回地址 nginx直接返回
    # 没有文件，查询，写入文件，返回地址 nginx直接返回
    # query 为空的时候? like? 还是另外的sql? @todo


def abort_response(status, msg):
    return make_response((msg, status, dict()))


def DPS_get_risk_score(strategy_dict):
    """
    因为报警都是相同场景，这里获得风险分值的方法是算所有策略的总分(权重*命中次数)然后除总命中次数的平均值
    Input: {strategy1:count, strategy2:count}
    """
    strategy_weighs = get_strategy_weigh()
    if not strategy_dict:
        return 0
    total_score = 0
    total_count = 0
    for strategy, count in strategy_dict.iteritems():
        total_score += strategy_weighs.get(strategy, dict()).get("score", 0) * count
        total_count += count
    if total_count == 0:
        current_app.logger.warn("total_count is 0, total_score is %s, return risk score 0", total_score)
        return 0
    return float(total_score) / float(total_count*10)


def DPS_write_fn(fp, show_cols, query_result):
    # max 65536 line to avoid excel 2003 limit
    line_count = 0
    with open(fp, 'w') as f:
        writer = csv.writer(f)
        writer.writerow(show_cols)
        line_count += 1
        for d in query_result:
            if line_count >= 65536:
                break
            row = list()
            for col in show_cols:
                v = d.get(col, None)
                if col in ("origin", "tags"):
                    if v:
                        s = json.dumps(v)
                    else:
                        # avoid json.dumps(None) -> 'null'
                        # json.dumps('') -> '""'
                        s = None
                    row.append(s)
                elif isinstance(v, unicode):
                    row.append(v.encode("utf8"))
                else:
                    row.append(v)
            writer.writerow(row)
            line_count += 1


def DPS_read_fn(fp, start_offset, end_offset, show_cols, result_list=None):
    """
    从fp目录的csv文件中读取指定行数的数据
    使用show_cols(list)去检验csv文件的数据列符合预期。
    """
    if result_list is None:
        result_list = list()
    if not (0<= start_offset < end_offset):
        err = "invalid offset: start from %s end with %s" % (start_offset, end_offset)
        current_app.logger.warn(err)
        raise AttributeError, err
    with open(fp, 'r') as f:
        # 读取字段名说明
        reader = csv.reader(f)
        fp_cols = reader.next()
        if fp_cols != list(show_cols):
            err = "file %s, expect cols: %s, got: %s" % (fp, show_cols, fp_cols)
            current_app.logger.error(err)
            raise AttributeError, err
        for l in xrange(0, end_offset):
            try:
                if l < start_offset:
                    reader.next()
                else:
                    line = reader.next()
                    if not line:
                        continue
                    line_dict = dict(zip(show_cols, line))
                    for c in ("origin", "tags"):
                        if line_dict.has_key(c):
                            line_dict[c] = safe_loads(line_dict[c])
                    for c in ("is_test", "is_white"):
                        if line_dict.has_key(c):
                            line_dict[c] = safe_int(line_dict.get(c, 0))
                    for c in ("ratio", "risk_score"):
                        if line_dict.has_key(c):
                            line_dict[c] = safe_float(line_dict.get(c, 0))
                    for c in ("geo_city",):
                        if line_dict.has_key(c):
                            line_dict[c] = safe_unicode(line_dict.get(c, ''))
                    result_list.append(line_dict)
            except StopIteration:
                break
    return result_list


def safe_unicode(obj):
    try:
        return obj.decode("utf8")
    except Exception:
        logging.warn(traceback.format_exc())
    return u''


def safe_float(obj):
    try:
        return float(obj)
    except Exception:
        logging.warn(traceback.format_exc())
    return float(0)


def safe_int(obj):
    try:
        return int(obj)
    except Exception:
        logging.warn(traceback.format_exc())
    return 0


def safe_loads(obj):
    try:
        return json.loads(obj)
    except Exception:
        logging.warn(traceback.format_exc())
    return None


def DPS_write_count(tmp_count_fn, total_count):
    # write total count from a file like: DPS-$(uri)-$(fromtime)-$(endtime)-$(query)_count
    try:
        with open(tmp_count_fn, 'w') as f:
            f.write(str(total_count))
    except Exception:
        current_app.logger.error("Can't write total count to %s : %s", tmp_count_fn, traceback.format_exc())


def DPS_read_count(tmp_count_fn):
    # read total count from a file like: DPS-$(uri)-$(fromtime)-$(endtime)-$(query)_count
    try:
        with open(tmp_count_fn, 'r') as f:
            total = int(f.readline())
    except Exception:
        current_app.logger.error("Can't read %s 's count: %s", tmp_count_fn, traceback.format_exc())
        total = 0
    return total


def DPS_spider_query(DB_Engine, fromtime, endtime, uri_stem, query, result_dict=None):
    """
    Input: result_dict dict
    Output:
    {
      key:key_type:{
        first_time:
        last_time:
        key_type:
        key:
        is_test:
        is_white:
        tags: {tag1:count}
        geo_city:
        count:
      }
      total:count
    }
    """
    if result_dict is None:
        result_dict = dict()

    if not query:
        q = DB_Engine.execute(DPS_Spider_No_Query, fromtime=fromtime,
                              endtime=endtime, uri_stem=uri_stem)
    else:
        query = "%%%s%%" % query
        q = DB_Engine.execute(DPS_Spider_Query, fromtime=fromtime, query=query,
                              endtime=endtime, uri_stem=uri_stem)

    total = 0
    for _ in q.fetchall():
        if not _["key"]:
            key = ""
        else:
            key = _["key"]
        k = "%s:%s" % (key, _["check_type"])
        count = int(_["count"])
        total += count
        if result_dict.has_key(k):
            r = result_dict.get(k)
            if _["min_ts"] < r["first_time"]:
                r["first_time"] = _["min_ts"]
            if _["max_ts"] > r["last_time"]:
                r["last_time"] = _["max_ts"]
            # 所有记录都是测试才显示测试
            if not (r["is_test"] == 1 and _['test'] == 1):
                r["is_test"] = 0
            # 所有记录都是白名单才显示白名单
            if not (r["is_white"] == 1 and _['decision'] == "accept"):
                r["is_white"] = 0
            
            if r["tags"].has_key(_["tag"]):
                r["tags"][_["tag"]] += count
            else:
                r["tags"][_["tag"]] = count
            r["count"] = r.get("count", 0) + count
        else:
            r = result_dict[k] = dict()
            r["first_time"] = _["min_ts"]
            r["last_time"] = _["max_ts"]
            r["key"] = key
            r["key_type"] = _["check_type"]
            r["is_test"] = _['test']
            r["geo_city"]=_["geo_city"]
            r["tags"]={_["tag"]: count}
            r["count"] = count
            if _["decision"] == "accept":
                r["is_white"] = 1
            else:
                r["is_white"] = 0

    result_dict['total'] = total
    logging.debug("after fetch data: %s", result_dict)
    return result_dict


def DPS_account_query(DB_Engine, fromtime, endtime, uri_stem, query, result_dict=None):
    """
    Input: result_dict dict
    Output:
    {
      uid:{
        first_time:
        last_time:
        is_test:
        is_white:
        strategys: {strategy1:count}
        origin: { ip:{
                    tags: {tag1:count}
                    source_ip:
                    geo_city:
                    
                  }
        }
      }
    }
    """
    if result_dict is None:
        result_dict = dict()

    if not query:
        q = DB_Engine.execute(DPS_Account_No_Query, fromtime=fromtime,
                              endtime=endtime, uri_stem=uri_stem)
    else:
        query = "%%%s%%" % query
        q = DB_Engine.execute(DPS_Account_Query, fromtime=fromtime, query=query,
                              endtime=endtime, uri_stem=uri_stem)

    for _ in q.fetchall():
        if not _["uid"]:
            user = ""
        else:
            user = _["uid"]
        count = int(_["count"])
        if result_dict.has_key(user):
            r = result_dict.get(user)
            if _["min_ts"] < r["first_time"]:
                r["first_time"] = _["min_ts"]
            if _["max_ts"] > r["last_time"]:
                r["last_time"] = _["max_ts"]
            # 所有记录都是测试才显示测试
            if not (r["is_test"] == 1 and _['test'] == 1):
                r["is_test"] = 0
            # 所有记录都是白名单才显示白名单
            if not (r["is_white"] == 1 and _['decision'] == "accept"):
                r["is_white"] = 0
            
            strategy_dict = r.get("strategys", dict())
            strategy_dict[_["strategy_name"]] = count + \
                                                strategy_dict.get(_["strategy_name"], 0)
            r["strategys"] = strategy_dict

            ro = r["origin"]
            if not ro.has_key(_["ip"]):
                ro[_["ip"]] = dict(source_ip=_["ip"], geo_city=_["geo_city"],
                                   tags={_["tag"]: count})
            else:
                tag_dict = ro[_["ip"]].get("tags", dict())
                tag_dict[_["tag"]] = tag_dict.get(_["tag"], 0) + count
                ro[_["ip"]]["tags"] = tag_dict
                
        else:
            r = result_dict[user] = dict()
            r["first_time"] = _["min_ts"]
            r["last_time"] = _["max_ts"]
            r["is_test"] = _['test']
            if _["decision"] == "accept":
                r["is_white"] = 1
            else:
                r["is_white"] = 0
            r['strategys'] = {_["strategy_name"]:count}
            ro = r["origin"] = dict()
            ro[_["ip"]] = dict(source_ip=_["ip"], geo_city=_["geo_city"],
                               tags={_["tag"]: count})

    logging.debug("after fetch data: %s", result_dict)
    return result_dict
