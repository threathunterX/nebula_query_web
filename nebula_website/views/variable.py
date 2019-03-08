# -*- coding: utf-8 -*-

"""
所有变量相关的操作，目前会包含一些遗留的接口，后续会统一化为变量接口

"""

import traceback
from flask import Blueprint, jsonify, request, current_app

from nebula_website import data_client
from nebula_website.utils import get_current_hour_timestamp, reduce_value_level
from nebula_website import settings


mod = Blueprint("variable", __name__)


# @mod.route('/stats/slot/query', methods=["POST"])
# def SlotStatsQueryHandler():
#     """
#     从slot获取数据的api接口, 遗留接口，将被替换.
#     note: 2018-10-16 注释此接口，此接口目前由java_web那边提供服务
#
#     """
#
#     req = request.get_json()
#     keys = req.get('keys', list())
#     timestamp = int(req.get('timestamp', 0))
#     variables = req.get('variables', list())
#     dimension = req.get('dimension', None)
#
#     if not (timestamp and variables):
#         return jsonify(status=400, msg='timestamp, variables不能为空')
#
#     current_hour_ts = get_current_hour_timestamp()
#     try:
#         ret_stats = None
#         if timestamp >= current_hour_ts and settings.Enable_Online:
#             ret_stats = data_client.get_online_key_stat(keys, dimension, timestamp, variables)
#         if timestamp < current_hour_ts:
#             ret_stats = data_client.get_offline_key_stat(keys, dimension, timestamp, variables)
#             if ret_stats and isinstance(ret_stats, dict):
#                 reduce_value_level(ret_stats)
#
#         if ret_stats:
#             return jsonify(status=200, values=ret_stats)
#         else:
#             return jsonify(status=200, values=ret_stats, msg=u"slot数据返回为空")
#     except Exception as e:
#         current_app.logger.error(traceback.format_exc())
#         return jsonify(status=-1, error=e.message)


@mod.route('/stats/slot/mergequery', methods=["POST"])
def SlotStatsMergeQueryHandler():
    """
    从slot获取merge数据的api接口, 遗留接口，将被替换.

    /stats/slot/query 只会返回1个小时的数据，需要返回n个小时的数据.
    """

    req = request.get_json()
    keys = req.get('keys', list())
    variables = req.get('variables', list())
    timerange = req.get('timerange', list())
    dimension = req.get('dimension', None)

    if not variables or not keys or not dimension:
        return jsonify(status=400, msg='请求数据不正确')

    if not timerange or len(timerange) != 2:
        return jsonify(status=400, msg='请求数据不正确')

    starttime, endtime = timerange
    starttime = int(starttime)
    endtime = int(endtime)

    last_hour_ts = get_current_hour_timestamp() - 3600 * 1000
    starttime = min(starttime, last_hour_ts)
    endtime = min(endtime, last_hour_ts)

    try:
        ret_stats = data_client.get_offline_merged_variable(keys, dimension, variables, starttime, endtime)
        if ret_stats and isinstance(ret_stats, dict):
            reduce_value_level(ret_stats)

        if ret_stats:
            return jsonify(status=200, values=ret_stats)
        else:
            return jsonify(status=200, values=ret_stats, msg=u"slot数据返回为空")
    except Exception as e:
        current_app.logger.error(traceback.format_exc())
        return jsonify(status=-1, error=e.message)
