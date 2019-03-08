
# # -*- coding: utf-8 -*-
#
# import traceback
# from flask import Blueprint, request, jsonify, current_app, make_response
#
# from nebula_website.managers import logquery
# from nebula_website.managers.logquery import LogQueryDao, LQ_Wait_Status
#
# mod = Blueprint("logquery", __name__)
'''

note:注释本接口， 此接口已经由java-web实现并且运行
time：2018-10-24

'''


#
# @mod.route("/platform/persistent_query", methods=["GET"])
# def GET_LogQuery():
#     """
#     查询 日志查询任务配置
#     #@done
#     """
#
#     # 查询 LogQuery_Status
#     try:
#         LogQuery_Status = logquery.LogQueryDao.get_logquery_status()
#         response = LogQuery_Status.values()
#         response.sort(key=lambda x: x.get("id", 0))
#         return jsonify({'status': 200, 'msg': "ok", 'values': response})
#     except Exception:
#         msg = traceback.format_exc()
#         pmsg = "Error when fetch logquery configs to database.\n %s" % msg
#         current_app.logger.error(pmsg)
#         return jsonify({'status': 500, 'msg': pmsg})
#
#
# @mod.route("/platform/persistent_query", methods=["POST"])
# def POST_LogQuery():
#     """
#     新增日志查询任务
#     #@done
#     @API
#     summary: 新增日志查询任务
#     notes: 新增日志查询任务
#     tags:
#       - platform
#     method: post
#     parameters:
#     - name: fromtime
#       in: body
#       required: true
#       type: timestamp
#       description: 起始时间戳
#     - name: endtime
#       in: body
#       required: true
#       type: timestamp
#       description: 结束时间戳
#     - name: terms
#       in: body
#       required: true
#       type: list
#       description: 查询条件
#     - name: show_cols
#       in: body
#       required: true
#       type: list
#       description: 显示字段
#     - name: event_name
#       in: body
#       type: string
#       required: true
#       description: 基础事件名
#     - name: remark
#       in: body
#       type: string
#       required: false
#       description: 备注
#     produces:
#       - application/json
#     """
#     if logquery.LogQueryDao.reach_logquery_job_limit():
#         return jsonify({'status': 500, 'msg': '只能同时进行2条查询，请等待完成后再添加新的查询'})
#     try:
#         body = request.get_json()
#         fromtime = int(body.get("fromtime", 0))
#         endtime = int(body.get("endtime", 0))
#         terms = body.get("terms", None)
#         show_cols = body.get("show_cols", None)
#         event_name = body.get("event_name", None)
#         remark = body.get("remark", None)
#     except Exception:
#         current_app.logger.error("Error when parse request args. %s", traceback.format_exc())
#         return make_response(("fromtime or endtime args is invalid.",
#                               400, dict()))
#
#     if not (endtime and fromtime and terms and show_cols and event_name):
#         return make_response(("fromtime, endtime, terms, show_cols, event_name \
#                               args is required.",
#                               400, dict()))
#     # do db store
#     try:
#         success, d = logquery.LogQueryDao.add(fromtime, endtime, terms, \
#                                                 show_cols, event_name, remark)
#         if not success:
#             return make_response((d, 503, dict()))
#     except Exception:
#         msg = traceback.format_exc()
#         pmsg = "Error when store logquery config to database.\n %s" % msg
#         m = "存储日志查询任务配置失败"
#         current_app.logger.error(pmsg)
#         return jsonify({'status': 500, 'msg': m})
#
#     lq_id = d["id"]
#     default_status = LQ_Wait_Status
#
#     # request babel util timeout
#     try:
#         success, d = logquery.add_logquery_job(lq_id, fromtime, endtime, terms, \
#                                                show_cols, event_name, remark)
#         if not success:
#             return make_response((d, 503, dict()))
#     except Exception:
#         msg = traceback.format_exc()
#         m = "创建日志查询任务失败."
#         pmsg = "Error when send query babel to Online module.\n %s" % msg
#         current_app.logger.error(pmsg)
#         return jsonify({'status': 500, 'msg': m})
#
#     # update LogQuery_Status
#     LogQueryDao.set_logquery_status(dict(
#         id = lq_id,
#         status= default_status,
#         remark= remark,
#         error= None,
#         event_name=event_name,
#         terms=terms,
#         fromtime=fromtime,
#         endtime=endtime,
#         show_cols=show_cols))
#     return jsonify({'status': 200, 'msg': 'ok'})
#
#
# @mod.route("/platform/persistent_query/<int:config_id>", methods=["DELETE"])
# def DEL_LogQuery(config_id):
#     """
#     删除日志查询任务
#
#     #@done
#     """
#
#     # delete from databases
#     try:
#         success = logquery.LogQueryDao.delete(config_id)
#         if not success:
#             return jsonify({'status': 500,
#                             'msg': "无法从数据库中删除id为%s的日志查询配置" % config_id})
#     except Exception:
#         msg = traceback.format_exc()
#         current_app.logger.error("Error when delete logquery config from database.")
#         current_app.logger.error(msg)
#         return jsonify({'status': 500, 'msg': msg})
#
#     # delete query job from online
#     try:
#         success, d = logquery.delete_logquery_job(config_id)
#         if not success:
#             return make_response((d, 503, dict()))
#     except Exception:
#         msg = traceback.format_exc()
#         current_app.logger.error("Error when delete logquery job from Online module.")
#         current_app.logger.error(msg)
#         return jsonify({'status': 500, 'msg': msg})
#
#     # delete view cache
#     logquery.LogQueryDao.delete_logquery_status(config_id)
#     current_app.logger.debug("logquery_status after del:%s", logquery.LogQueryDao.get_logquery_status())
#     return jsonify({'status': 200, 'msg': "ok"})
#
#
# @mod.route("/platform/persistent_query/data", methods=["GET"])
# def GET_LogQueryData():
#     """
#     获取日志查询任务 结果
#     Output format
#     {
#     "status": 200,
#     "msg": "ok",
#     "total": 30,
#     "id": "12",
#     "download_path": "",
#     "filesize":120, #单位 字节数
#     "values": [
#       {
#         "did": "f4d39d57bafdb3b058a7d3f1af22c3c36259f5b58e760c5e9a61b10e",
#         "timestamp": "1500278473443",
#         "c_ip": "220.249.64.23",
#         "uid": ""
#       },
#       {
#         "did": "f4d39d57bafdb3b058a7d3f1af22c3c36259f5b58e760c5e9a61b10e",
#         "timestamp": "1500278477228",
#         "c_ip": "220.249.64.23",
#         "uid": ""
#       }
#     ]
#     }
#     #@done
#     """
#     req = request.args
#     try:
#         lq_id = int(req.get('id', 0))
#         page = int(req.get('page', 1))
#         page_count = int(req.get('page_count', 20))
#     except Exception:
#         return make_response(("id, page, page_count args is invalid.",
#                               400, dict()))
#
#     if not lq_id:
#         return make_response(("id args is required.",
#                               400, dict()))
#
#     current_app.logger.debug("Input args: lq_id: %s, page:%s, page_count:%s", lq_id, page, page_count)
#     # babel fetch data.
#     try:
#         LogQuery_Status = LogQueryDao.get_logquery_status()
#         success, d = logquery.fetch_logquery_data(lq_id, page, page_count)
#         if success:
#             lqs = LogQuery_Status.get(lq_id,dict())
#             return jsonify({'status': 200, 'msg': 'ok', 'values':d['data'],
#                             'total':lqs.get("total", 0), "id": lq_id,
#                             'download_path':lqs.get("download_path",""),
#                             'filesize':lqs.get("filesize", 0)})
#         else:
#             return make_response((d, 503, dict()))
#     except Exception:
#         msg = traceback.format_exc()
#         pmsg = "Error when fetch logquery job status from database.\n %s" % msg
#         current_app.logger.error(pmsg)
#         return jsonify({'status': 500, 'msg': pmsg})
#
#
# @mod.route("/platform/persistent_query/progress", methods=["GET"])
# def GET_LogQueryProgress():
#     """
#     获取日志查询任务的查询进度、状态
#     #@done
#     """
#     # async job to fetch wait|progress jobs' status, progress job progress to LogQuery_Status
#
#     # query query job status from LogQuery_Status
#     try:
#         res = []
#         LogQuery_Status = logquery.LogQueryDao.get_logquery_status()
#         if LogQuery_Status:
#             for _ in LogQuery_Status.values():
#                 res.append(dict(
#                     id=_['id'],
#                     status=_["status"],
#                     progress=_.get("progress"),
#                     error=_.get("error")))
#             res.sort(key=lambda x:x.get("id",0))
#         return jsonify({'status': 200, 'msg': "ok", 'values':res})
#     except Exception:
#         msg = traceback.format_exc()
#         current_app.logger.error("Error when fetch logquery job progress.")
#         current_app.logger.error(msg)
#         return jsonify({'status': 500, 'msg': msg})
