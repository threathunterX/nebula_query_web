# -*- coding: utf-8 -*-
import logging, time
from datetime import datetime
import traceback

from flask import Blueprint, request, jsonify, current_app, make_response

from nebula_website import utils, settings

mod = Blueprint("logquery", __name__)

DEBUG_PREFIX = "==============="

logger = logging.getLogger("nebula.web.mock.logquery")

Mock_Dict = dict() 
"""
id:{
"id": 1,
"stauts": "success",
"progress":0.1,
"remark": "XXX",
"error": "",
"event_name":"",
"terms":"",
"fromtime":,
"endtime":,
"show_cols":,

},
id2:{
"id": 2,
"stauts": "process",
"remark": "XXX",
"error": "",
"event_name":"",
"terms":""
}
"""
import string, random

def random_str(size=None):
    if size is None:
        size = 20
    random_source = [ _ for s in (string.digits, string.ascii_letters) for _ in s]
    return ''.join(random.choice(random_source) for _ in xrange(size))

import uuid

def mock_random_result():
#    result = [(False, "Mock Error"), Exception, (True, None) ]
    result = [(True, None) ]
    def wrapper():
        r = result.pop(0)
        result.append(r)
        if r is Exception:
            raise Exception, "Mock Exception."
        return r
    return wrapper

Mock_Result_Dict = dict()

def get_mock_result(view_id):
    if not Mock_Result_Dict.has_key(view_id):
        Mock_Result_Dict[view_id] = mock_random_result()

    return Mock_Result_Dict[view_id]()

GET_LogQuery_ID = None
POST_LogQuery_ID = None
DEL_LogQuery_ID = None
GET_LogQueryProgress_ID = None
GET_LogQueryData_ID = None

@mod.route("/platform/persistent_query", methods=["GET"])
def GET_LogQuery():
    # 查询 本视图文件的cache
    try:
        global GET_LogQuery_ID
        if GET_LogQuery_ID is None:
            GET_LogQuery_ID = str(uuid.uuid1())
        success, msg = get_mock_result(GET_LogQuery_ID)
        if success:
            res = Mock_Dict.values()
            current_app.logger.debug("Mock_Dict items: %s", res)
            res.sort(key=lambda x:x.get("id",0))
            return jsonify({'status': 200, 'msg': "ok", 'values':res})
        else:
            return jsonify({'status': 500, 'msg': msg})
    except Exception:
        msg = traceback.format_exc()
        pmsg = "Error when fetch logquery configs to database.\n %s" % msg
        current_app.logger.error(pmsg)
        return jsonify({'status': 500, 'msg': pmsg})
    
@mod.route("/platform/persistent_query", methods=["POST"])
def POST_LogQuery():
    """
    新增日志查询任务
    
    @API
    summary: 新增日志查询任务
    notes: 新增日志查询任务
    tags:
      - platform
    method: post
    parameters:
    - name: fromtime
      in: body    
      required: true
      type: timestamp
      description: 起始时间戳
    - name: endtime
      in: body
      required: true
      type: timestamp
      description: 结束时间戳
    - name: terms
      in: body
      required: true
      type: list
      description: 查询条件
    - name: show_cols
      in: body
      required: true
      type: list
      description: 显示字段
    - name: event_name
      in: body
      type: string
      required: true
      description: 基础事件名
    - name: remark
      in: body
      type: string
      required: false
      description: 备注    
    produces:
      - application/json
    """
    try:
        body = request.get_json()
        fromtime = int(body.get("fromtime", 0))
        endtime = int(body.get("endtime", 0))
        terms = body.get("terms", None)
        show_cols = body.get("show_cols", None)
        event_name = body.get("event_name", None)
        remark = body.get("remark", None)
    except Exception:
        current_app.logger.error("Error when parse request args. %s", traceback.format_exc())
        return make_response(("fromtime or endtime args is invalid.",
                              400, dict()))
    
    if not (endtime and fromtime and terms and show_cols and event_name):
        return make_response(("fromtime, endtime, terms, show_cols, event_name \
                              args is required.",
                              400, dict()))
    default_status = "wait"
    # do db store
    try:
        # 连续的请求，失败、成功的需求
        global POST_LogQuery_ID
        if POST_LogQuery_ID is None:
            POST_LogQuery_ID = str(uuid.uuid1())
        success, msg = get_mock_result(POST_LogQuery_ID)
        if success:
            i = max(Mock_Dict.keys() or [0]) +1 
            Mock_Dict[i] = dict(
                id=i,
                status= default_status,
                remark= remark,
                error= None,
                event_name=event_name,
                terms=terms,
                fromtime=fromtime,
                endtime=endtime,
                show_cols=show_cols
            )
        else:
            return jsonify({'status': 500, 'msg': msg})
    except Exception:
        msg = traceback.format_exc()
        pmsg = "Error when store logquery config to database.\n %s" % msg
        current_app.logger.error(pmsg)
        return jsonify({'status': 500, 'msg': pmsg})
        
    # request babel util timeout 
    try:
        Mock_Dict[i]["status"] = "process"
        return jsonify({'status': 200, 'msg': "ok"})
    except Exception:
        msg = traceback.format_exc()
        pmsg = "Error when send query babel to Online module.\n %s" % msg
        current_app.logger.error(pmsg)
        return jsonify({'status': 500, 'msg': pmsg})

@mod.route("/platform/persistent_query/<int:config_id>", methods=["DELETE"])
def DEL_LogQuery(config_id):
    # delete from databases
    try:
        global DEL_LogQuery_ID
        if DEL_LogQuery_ID is None:
            DEL_LogQuery_ID = str(uuid.uuid1())
        
        success, msg = get_mock_result(DEL_LogQuery_ID)
        if success:
            Mock_Dict.pop(config_id)
            return jsonify({'status': 200, 'msg': "ok"})
        else:
            return jsonify({'status': 500, 'msg': msg})
    except Exception:
        msg = traceback.format_exc()
        pmsg = "Error when delete logquery config from database.\n %s" % msg
        current_app.logger.error(pmsg)
        return jsonify({'status': 500, 'msg': pmsg})

    # delete query job from online
    try:
        pass
    except Exception:
        msg = traceback.format_exc()
        pmsg = "Error when delete logquery job from Online module.\n %s" % msg
        current_app.logger.error(pmsg)
        return jsonify({'status': 500, 'msg': pmsg})

@mod.route("/platform/persistent_query/data", methods=["GET"])
def GET_LogQueryData():
    req = request.args
    try:
        lq_id = int(req.get('id', 0))
        page = int(req.get('page', 1))
        page_count = int(req.get('page_count'), 20)
    except Exception:
        return make_response(("id, page, page_count args is invalid.",
                              400, dict()))

    if not lq_id:
        return make_response(("id args is required.",
                              400, dict()))
    
    # babel fetch data.
    try:
        global GET_LogQueryData_ID
        if GET_LogQueryData_ID is None:
            GET_LogQueryData_ID = str(uuid.uuid1())
        # success? if query(id) in Query_Progress and progress is success.
        success, msg = get_mock_result(GET_LogQueryData_ID)
        if success:
            total = Mock_Dict[lq_id]["total"] = random.randrange(30,50)
            res = []
            for _ in xrange(total % page_count):
                res.append(dict( (c, random_str()) for c in Mock_Dict[lq_id]["show_cols"]))
            return jsonify({'status': 200, 'msg': "ok", 'values':res, "total": total,
                            "download_path":random_str(), "id":lq_id,
                            "filesize":random.randrange(100,200),
                            })
        else:
            return jsonify({'status': 500, 'msg': msg})
    except Exception:
        msg = traceback.format_exc()
        pmsg = "Error when fetch logquery job status from database.\n %s" % msg
        current_app.logger.error(pmsg)
        return jsonify({'status': 500, 'msg': pmsg})
        
Query_Progress = dict()

@mod.route("/platform/persistent_query/progress", methods=["GET"])
def GET_LogQueryProgress():
    # async job to fetch wait, progress job progress to Query_Progress like Mock_Dict
    
    # query query job status from local cache
    try:
        
        global GET_LogQueryProgress_ID
        if GET_LogQueryProgress_ID is None:
            GET_LogQueryProgress_ID = str(uuid.uuid1())
        
        success, msg = get_mock_result(GET_LogQueryProgress_ID)
        if success:
            res = []
            for _ in Mock_Dict.values():
                if _.get("progress", 0) >= 1.0:
                    _["progress"] = 1
                    _["status"] = "success"
                else:
                    _["progress"] = _.get("progress", 0) + 0.075
                res.append(dict(id=_['id'],
                                status=_["status"],
                                progress=_["progress"],
                                error=_["error"]))
            return jsonify({'status': 200, 'msg': "ok", 'values':res})
        else:
            return jsonify({'status': 500, 'msg': msg})
        
    except Exception:
        msg = traceback.format_exc()
        current_app.logger.error("Error when fetch logquery job progress.")
        current_app.logger.error(msg)
        return jsonify({'status': 500, 'msg': msg})

@mod.route("/nebula/events")
def events_dep():
    return jsonify({"status": 0, "msg": "ok", "values": [{"fields": [{"remark": "", "type": "string", "name": "id"}, {"remark": "", "type": "string", "name": "pid"}, {"remark": "\u5ba2\u6237\u7aefip", "type": "string", "name": "c_ip"}, {"remark": "", "type": "string", "name": "sid"}, {"remark": "", "type": "string", "name": "uid"}, {"remark": "", "type": "string", "name": "did"}, {"remark": "", "type": "string", "name": "platform"}, {"remark": "", "type": "string", "name": "page"}, {"remark": "", "type": "string", "name": "notices"}, {"remark": "\u5ba2\u6237\u7aef\u7aef\u53e3", "type": "long", "name": "c_port"}, {"remark": "\u8bf7\u6c42\u5927\u5c0f", "type": "long", "name": "c_bytes"}, {"remark": "\u8bf7\u6c42\u5185\u5bb9", "type": "string", "name": "c_body"}, {"remark": "", "type": "string", "name": "c_type"}, {"remark": "\u670d\u52a1\u7aefip", "type": "string", "name": "s_ip"}, {"remark": "\u670d\u52a1\u7aef\u7aef\u53e3", "type": "long", "name": "s_port"}, {"remark": "\u54cd\u5e94\u5927\u5c0f", "type": "long", "name": "s_bytes"}, {"remark": "\u54cd\u5e94\u5185\u5bb9", "type": "string", "name": "s_body"}, {"remark": "", "type": "string", "name": "s_type"}, {"remark": "\u4e3b\u673a\u5730\u5740", "type": "string", "name": "host"}, {"remark": "url\u95ee\u53f7\u524d\u90e8\u5206", "type": "string", "name": "uri_stem"}, {"remark": "url\u95ee\u53f7\u540e\u90e8\u5206", "type": "string", "name": "uri_query"}, {"remark": "", "type": "string", "name": "referer"}, {"remark": "\u8bf7\u6c42\u65b9\u6cd5", "type": "string", "name": "method"}, {"remark": "\u8bf7\u6c42\u72b6\u6001", "type": "long", "name": "status"}, {"remark": "", "type": "string", "name": "cookie"}, {"remark": "", "type": "string", "name": "useragent"}, {"remark": "", "type": "string", "name": "xforward"}, {"remark": "", "type": "long", "name": "request_time"}, {"remark": "", "type": "string", "name": "request_type"}, {"remark": "", "type": "string", "name": "referer_hit"}, {"remark": "", "type": "string", "name": "geo_city"}, {"remark": "", "type": "string", "name": "user_name"}, {"remark": "", "type": "string", "name": "transaction_id"}, {"remark": "", "type": "string", "name": "deposit_amount"}, {"remark": "", "type": "string", "name": "card_number"}, {"remark": "", "type": "string", "name": "counterpart_user"}, {"remark": "", "type": "string", "name": "account_balance_before"}, {"remark": "\u64cd\u4f5c\u7ed3\u679c", "type": "string", "name": "result"}], "remark": "\u8d44\u91d1\u5b58\u5165", "name": "TRANSACTION_DEPOSIT"}, {"fields": [{"remark": "", "type": "string", "name": "id"}, {"remark": "", "type": "string", "name": "pid"}, {"remark": "\u5ba2\u6237\u7aefip", "type": "string", "name": "c_ip"}, {"remark": "", "type": "string", "name": "sid"}, {"remark": "", "type": "string", "name": "uid"}, {"remark": "", "type": "string", "name": "did"}, {"remark": "", "type": "string", "name": "platform"}, {"remark": "", "type": "string", "name": "page"}, {"remark": "", "type": "string", "name": "notices"}, {"remark": "\u5ba2\u6237\u7aef\u7aef\u53e3", "type": "long", "name": "c_port"}, {"remark": "\u8bf7\u6c42\u5927\u5c0f", "type": "long", "name": "c_bytes"}, {"remark": "\u8bf7\u6c42\u5185\u5bb9", "type": "string", "name": "c_body"}, {"remark": "", "type": "string", "name": "c_type"}, {"remark": "\u670d\u52a1\u7aefip", "type": "string", "name": "s_ip"}, {"remark": "\u670d\u52a1\u7aef\u7aef\u53e3", "type": "long", "name": "s_port"}, {"remark": "\u54cd\u5e94\u5927\u5c0f", "type": "long", "name": "s_bytes"}, {"remark": "\u54cd\u5e94\u5185\u5bb9", "type": "string", "name": "s_body"}, {"remark": "", "type": "string", "name": "s_type"}, {"remark": "\u4e3b\u673a\u5730\u5740", "type": "string", "name": "host"}, {"remark": "url\u95ee\u53f7\u524d\u90e8\u5206", "type": "string", "name": "uri_stem"}, {"remark": "url\u95ee\u53f7\u540e\u90e8\u5206", "type": "string", "name": "uri_query"}, {"remark": "", "type": "string", "name": "referer"}, {"remark": "\u8bf7\u6c42\u65b9\u6cd5", "type": "string", "name": "method"}, {"remark": "\u8bf7\u6c42\u72b6\u6001", "type": "long", "name": "status"}, {"remark": "", "type": "string", "name": "cookie"}, {"remark": "", "type": "string", "name": "useragent"}, {"remark": "", "type": "string", "name": "xforward"}, {"remark": "", "type": "long", "name": "request_time"}, {"remark": "", "type": "string", "name": "request_type"}, {"remark": "", "type": "string", "name": "referer_hit"}, {"remark": "", "type": "string", "name": "user_name"}, {"remark": "", "type": "string", "name": "person_id"}, {"remark": "", "type": "string", "name": "real_name"}, {"remark": "\u64cd\u4f5c\u7ed3\u679c", "type": "string", "name": "result"}, {"remark": "", "type": "string", "name": "geo_city"}], "remark": "\u8d26\u6237\u5b9e\u540d\u8ba4\u8bc1", "name": "ACCOUNT_CERTIFICATION"}, {"fields": [{"remark": "", "type": "string", "name": "id"}, {"remark": "", "type": "string", "name": "pid"}, {"remark": "\u5ba2\u6237\u7aefip", "type": "string", "name": "c_ip"}, {"remark": "", "type": "string", "name": "sid"}, {"remark": "", "type": "string", "name": "uid"}, {"remark": "", "type": "string", "name": "did"}, {"remark": "", "type": "string", "name": "platform"}, {"remark": "", "type": "string", "name": "page"}, {"remark": "", "type": "string", "name": "notices"}, {"remark": "\u5ba2\u6237\u7aef\u7aef\u53e3", "type": "long", "name": "c_port"}, {"remark": "\u8bf7\u6c42\u5927\u5c0f", "type": "long", "name": "c_bytes"}, {"remark": "\u8bf7\u6c42\u5185\u5bb9", "type": "string", "name": "c_body"}, {"remark": "", "type": "string", "name": "c_type"}, {"remark": "\u670d\u52a1\u7aefip", "type": "string", "name": "s_ip"}, {"remark": "\u670d\u52a1\u7aef\u7aef\u53e3", "type": "long", "name": "s_port"}, {"remark": "\u54cd\u5e94\u5927\u5c0f", "type": "long", "name": "s_bytes"}, {"remark": "\u54cd\u5e94\u5185\u5bb9", "type": "string", "name": "s_body"}, {"remark": "", "type": "string", "name": "s_type"}, {"remark": "\u4e3b\u673a\u5730\u5740", "type": "string", "name": "host"}, {"remark": "url\u95ee\u53f7\u524d\u90e8\u5206", "type": "string", "name": "uri_stem"}, {"remark": "url\u95ee\u53f7\u540e\u90e8\u5206", "type": "string", "name": "uri_query"}, {"remark": "", "type": "string", "name": "referer"}, {"remark": "\u8bf7\u6c42\u65b9\u6cd5", "type": "string", "name": "method"}, {"remark": "\u8bf7\u6c42\u72b6\u6001", "type": "long", "name": "status"}, {"remark": "", "type": "string", "name": "cookie"}, {"remark": "", "type": "string", "name": "useragent"}, {"remark": "", "type": "string", "name": "xforward"}, {"remark": "", "type": "long", "name": "request_time"}, {"remark": "", "type": "string", "name": "request_type"}, {"remark": "", "type": "string", "name": "referer_hit"}, {"remark": "", "type": "string", "name": "user_name"}, {"remark": "", "type": "string", "name": "login_verification_type"}, {"remark": "\u5bc6\u7801md5", "type": "string", "name": "password"}, {"remark": "\u9a8c\u8bc1\u7801", "type": "string", "name": "captcha"}, {"remark": "\u64cd\u4f5c\u7ed3\u679c", "type": "string", "name": "result"}, {"remark": "", "type": "string", "name": "remember_me"}, {"remark": "", "type": "string", "name": "login_channel"}, {"remark": "", "type": "string", "name": "geo_city"}], "remark": "\u8d26\u6237\u767b\u5f55", "name": "ACCOUNT_LOGIN"}, {"fields": [{"remark": "", "type": "string", "name": "id"}, {"remark": "", "type": "string", "name": "pid"}, {"remark": "\u5ba2\u6237\u7aefip", "type": "string", "name": "c_ip"}, {"remark": "", "type": "string", "name": "sid"}, {"remark": "", "type": "string", "name": "uid"}, {"remark": "", "type": "string", "name": "did"}, {"remark": "", "type": "string", "name": "platform"}, {"remark": "", "type": "string", "name": "page"}, {"remark": "", "type": "string", "name": "notices"}, {"remark": "\u5ba2\u6237\u7aef\u7aef\u53e3", "type": "long", "name": "c_port"}, {"remark": "\u8bf7\u6c42\u5927\u5c0f", "type": "long", "name": "c_bytes"}, {"remark": "\u8bf7\u6c42\u5185\u5bb9", "type": "string", "name": "c_body"}, {"remark": "", "type": "string", "name": "c_type"}, {"remark": "\u670d\u52a1\u7aefip", "type": "string", "name": "s_ip"}, {"remark": "\u670d\u52a1\u7aef\u7aef\u53e3", "type": "long", "name": "s_port"}, {"remark": "\u54cd\u5e94\u5927\u5c0f", "type": "long", "name": "s_bytes"}, {"remark": "\u54cd\u5e94\u5185\u5bb9", "type": "string", "name": "s_body"}, {"remark": "", "type": "string", "name": "s_type"}, {"remark": "\u4e3b\u673a\u5730\u5740", "type": "string", "name": "host"}, {"remark": "url\u95ee\u53f7\u524d\u90e8\u5206", "type": "string", "name": "uri_stem"}, {"remark": "url\u95ee\u53f7\u540e\u90e8\u5206", "type": "string", "name": "uri_query"}, {"remark": "", "type": "string", "name": "referer"}, {"remark": "\u8bf7\u6c42\u65b9\u6cd5", "type": "string", "name": "method"}, {"remark": "\u8bf7\u6c42\u72b6\u6001", "type": "long", "name": "status"}, {"remark": "", "type": "string", "name": "cookie"}, {"remark": "", "type": "string", "name": "useragent"}, {"remark": "", "type": "string", "name": "xforward"}, {"remark": "", "type": "long", "name": "request_time"}, {"remark": "", "type": "string", "name": "request_type"}, {"remark": "", "type": "string", "name": "referer_hit"}, {"remark": "", "type": "string", "name": "geo_city"}, {"remark": "", "type": "string", "name": "user_name"}, {"remark": "", "type": "string", "name": "referralcode"}, {"remark": "", "type": "string", "name": "code_type"}], "remark": "http\u52a8\u6001\u8d44\u6e90\u8bbf\u95ee", "name": "ACCOUNT_REFERRALCODE_CREATE"}, {"fields": [{"remark": "", "type": "string", "name": "id"}, {"remark": "", "type": "string", "name": "pid"}, {"remark": "\u5ba2\u6237\u7aefip", "type": "string", "name": "c_ip"}, {"remark": "", "type": "string", "name": "sid"}, {"remark": "", "type": "string", "name": "uid"}, {"remark": "", "type": "string", "name": "did"}, {"remark": "", "type": "string", "name": "platform"}, {"remark": "", "type": "string", "name": "page"}, {"remark": "", "type": "string", "name": "notices"}, {"remark": "\u5ba2\u6237\u7aef\u7aef\u53e3", "type": "long", "name": "c_port"}, {"remark": "\u8bf7\u6c42\u5927\u5c0f", "type": "long", "name": "c_bytes"}, {"remark": "\u8bf7\u6c42\u5185\u5bb9", "type": "string", "name": "c_body"}, {"remark": "", "type": "string", "name": "c_type"}, {"remark": "\u670d\u52a1\u7aefip", "type": "string", "name": "s_ip"}, {"remark": "\u670d\u52a1\u7aef\u7aef\u53e3", "type": "long", "name": "s_port"}, {"remark": "\u54cd\u5e94\u5927\u5c0f", "type": "long", "name": "s_bytes"}, {"remark": "\u54cd\u5e94\u5185\u5bb9", "type": "string", "name": "s_body"}, {"remark": "", "type": "string", "name": "s_type"}, {"remark": "\u4e3b\u673a\u5730\u5740", "type": "string", "name": "host"}, {"remark": "url\u95ee\u53f7\u524d\u90e8\u5206", "type": "string", "name": "uri_stem"}, {"remark": "url\u95ee\u53f7\u540e\u90e8\u5206", "type": "string", "name": "uri_query"}, {"remark": "", "type": "string", "name": "referer"}, {"remark": "\u8bf7\u6c42\u65b9\u6cd5", "type": "string", "name": "method"}, {"remark": "\u8bf7\u6c42\u72b6\u6001", "type": "long", "name": "status"}, {"remark": "", "type": "string", "name": "cookie"}, {"remark": "", "type": "string", "name": "useragent"}, {"remark": "", "type": "string", "name": "xforward"}, {"remark": "", "type": "long", "name": "request_time"}, {"remark": "", "type": "string", "name": "request_type"}, {"remark": "", "type": "string", "name": "referer_hit"}, {"remark": "", "type": "string", "name": "geo_city"}], "remark": "http\u9759\u6001\u8d44\u6e90\u8bbf\u95ee", "name": "HTTP_STATIC"}, {"fields": [{"remark": "", "type": "string", "name": "id"}, {"remark": "", "type": "string", "name": "pid"}, {"remark": "\u5ba2\u6237\u7aefip", "type": "string", "name": "c_ip"}, {"remark": "", "type": "string", "name": "sid"}, {"remark": "", "type": "string", "name": "uid"}, {"remark": "", "type": "string", "name": "did"}, {"remark": "", "type": "string", "name": "platform"}, {"remark": "", "type": "string", "name": "page"}, {"remark": "", "type": "string", "name": "notices"}, {"remark": "\u5ba2\u6237\u7aef\u7aef\u53e3", "type": "long", "name": "c_port"}, {"remark": "\u8bf7\u6c42\u5927\u5c0f", "type": "long", "name": "c_bytes"}, {"remark": "\u8bf7\u6c42\u5185\u5bb9", "type": "string", "name": "c_body"}, {"remark": "", "type": "string", "name": "c_type"}, {"remark": "\u670d\u52a1\u7aefip", "type": "string", "name": "s_ip"}, {"remark": "\u670d\u52a1\u7aef\u7aef\u53e3", "type": "long", "name": "s_port"}, {"remark": "\u54cd\u5e94\u5927\u5c0f", "type": "long", "name": "s_bytes"}, {"remark": "\u54cd\u5e94\u5185\u5bb9", "type": "string", "name": "s_body"}, {"remark": "", "type": "string", "name": "s_type"}, {"remark": "\u4e3b\u673a\u5730\u5740", "type": "string", "name": "host"}, {"remark": "url\u95ee\u53f7\u524d\u90e8\u5206", "type": "string", "name": "uri_stem"}, {"remark": "url\u95ee\u53f7\u540e\u90e8\u5206", "type": "string", "name": "uri_query"}, {"remark": "", "type": "string", "name": "referer"}, {"remark": "\u8bf7\u6c42\u65b9\u6cd5", "type": "string", "name": "method"}, {"remark": "\u8bf7\u6c42\u72b6\u6001", "type": "long", "name": "status"}, {"remark": "", "type": "string", "name": "cookie"}, {"remark": "", "type": "string", "name": "useragent"}, {"remark": "", "type": "string", "name": "xforward"}, {"remark": "", "type": "long", "name": "request_time"}, {"remark": "", "type": "string", "name": "request_type"}, {"remark": "", "type": "string", "name": "referer_hit"}, {"remark": "", "type": "string", "name": "geo_city"}], "remark": "http\u52a8\u6001\u8d44\u6e90\u8bbf\u95ee", "name": "HTTP_DYNAMIC"}, {"fields": [{"remark": "", "type": "string", "name": "id"}, {"remark": "", "type": "string", "name": "pid"}, {"remark": "\u5ba2\u6237\u7aefip", "type": "string", "name": "c_ip"}, {"remark": "", "type": "string", "name": "sid"}, {"remark": "", "type": "string", "name": "uid"}, {"remark": "", "type": "string", "name": "did"}, {"remark": "", "type": "string", "name": "platform"}, {"remark": "", "type": "string", "name": "page"}, {"remark": "", "type": "string", "name": "notices"}, {"remark": "\u5ba2\u6237\u7aef\u7aef\u53e3", "type": "long", "name": "c_port"}, {"remark": "\u8bf7\u6c42\u5927\u5c0f", "type": "long", "name": "c_bytes"}, {"remark": "\u8bf7\u6c42\u5185\u5bb9", "type": "string", "name": "c_body"}, {"remark": "", "type": "string", "name": "c_type"}, {"remark": "\u670d\u52a1\u7aefip", "type": "string", "name": "s_ip"}, {"remark": "\u670d\u52a1\u7aef\u7aef\u53e3", "type": "long", "name": "s_port"}, {"remark": "\u54cd\u5e94\u5927\u5c0f", "type": "long", "name": "s_bytes"}, {"remark": "\u54cd\u5e94\u5185\u5bb9", "type": "string", "name": "s_body"}, {"remark": "", "type": "string", "name": "s_type"}, {"remark": "\u4e3b\u673a\u5730\u5740", "type": "string", "name": "host"}, {"remark": "url\u95ee\u53f7\u524d\u90e8\u5206", "type": "string", "name": "uri_stem"}, {"remark": "url\u95ee\u53f7\u540e\u90e8\u5206", "type": "string", "name": "uri_query"}, {"remark": "", "type": "string", "name": "referer"}, {"remark": "\u8bf7\u6c42\u65b9\u6cd5", "type": "string", "name": "method"}, {"remark": "\u8bf7\u6c42\u72b6\u6001", "type": "long", "name": "status"}, {"remark": "", "type": "string", "name": "cookie"}, {"remark": "", "type": "string", "name": "useragent"}, {"remark": "", "type": "string", "name": "xforward"}, {"remark": "", "type": "long", "name": "request_time"}, {"remark": "", "type": "string", "name": "request_type"}, {"remark": "", "type": "string", "name": "referer_hit"}, {"remark": "", "type": "string", "name": "user_name"}, {"remark": "", "type": "string", "name": "old_token"}, {"remark": "", "type": "string", "name": "new_token"}, {"remark": "", "type": "string", "name": "token_type"}, {"remark": "\u9a8c\u8bc1\u7801", "type": "string", "name": "captcha"}, {"remark": "\u64cd\u4f5c\u7ed3\u679c", "type": "string", "name": "result"}, {"remark": "", "type": "string", "name": "geo_city"}], "remark": "\u8d26\u6237\u51ed\u8bc1\u4fee\u6539", "name": "ACCOUNT_TOKEN_CHANGE"}, {"fields": [{"remark": "", "type": "string", "name": "id"}, {"remark": "", "type": "string", "name": "pid"}, {"remark": "\u5ba2\u6237\u7aefip", "type": "string", "name": "c_ip"}, {"remark": "", "type": "string", "name": "sid"}, {"remark": "", "type": "string", "name": "uid"}, {"remark": "", "type": "string", "name": "did"}, {"remark": "", "type": "string", "name": "platform"}, {"remark": "", "type": "string", "name": "page"}, {"remark": "", "type": "string", "name": "notices"}, {"remark": "\u5ba2\u6237\u7aef\u7aef\u53e3", "type": "long", "name": "c_port"}, {"remark": "\u8bf7\u6c42\u5927\u5c0f", "type": "long", "name": "c_bytes"}, {"remark": "\u8bf7\u6c42\u5185\u5bb9", "type": "string", "name": "c_body"}, {"remark": "", "type": "string", "name": "c_type"}, {"remark": "\u670d\u52a1\u7aefip", "type": "string", "name": "s_ip"}, {"remark": "\u670d\u52a1\u7aef\u7aef\u53e3", "type": "long", "name": "s_port"}, {"remark": "\u54cd\u5e94\u5927\u5c0f", "type": "long", "name": "s_bytes"}, {"remark": "\u54cd\u5e94\u5185\u5bb9", "type": "string", "name": "s_body"}, {"remark": "", "type": "string", "name": "s_type"}, {"remark": "\u4e3b\u673a\u5730\u5740", "type": "string", "name": "host"}, {"remark": "url\u95ee\u53f7\u524d\u90e8\u5206", "type": "string", "name": "uri_stem"}, {"remark": "url\u95ee\u53f7\u540e\u90e8\u5206", "type": "string", "name": "uri_query"}, {"remark": "", "type": "string", "name": "referer"}, {"remark": "\u8bf7\u6c42\u65b9\u6cd5", "type": "string", "name": "method"}, {"remark": "\u8bf7\u6c42\u72b6\u6001", "type": "long", "name": "status"}, {"remark": "", "type": "string", "name": "cookie"}, {"remark": "", "type": "string", "name": "useragent"}, {"remark": "", "type": "string", "name": "xforward"}, {"remark": "", "type": "long", "name": "request_time"}, {"remark": "", "type": "string", "name": "request_type"}, {"remark": "", "type": "string", "name": "referer_hit"}, {"remark": "", "type": "string", "name": "user_name"}, {"remark": "", "type": "string", "name": "transaction_id"}, {"remark": "", "type": "string", "name": "escrow_type"}, {"remark": "", "type": "string", "name": "escrow_account"}, {"remark": "", "type": "double", "name": "pay_amount"}, {"remark": "\u64cd\u4f5c\u7ed3\u679c", "type": "string", "name": "result"}, {"remark": "", "type": "string", "name": "geo_city"}], "remark": "\u7b2c\u4e09\u65b9\u652f\u4ed8", "name": "TRANSACTION_ESCROW"}, {"fields": [{"remark": "", "type": "string", "name": "id"}, {"remark": "", "type": "string", "name": "pid"}, {"remark": "\u5ba2\u6237\u7aefip", "type": "string", "name": "c_ip"}, {"remark": "", "type": "string", "name": "sid"}, {"remark": "", "type": "string", "name": "uid"}, {"remark": "", "type": "string", "name": "did"}, {"remark": "", "type": "string", "name": "platform"}, {"remark": "", "type": "string", "name": "page"}, {"remark": "", "type": "string", "name": "notices"}, {"remark": "\u5ba2\u6237\u7aef\u7aef\u53e3", "type": "long", "name": "c_port"}, {"remark": "\u8bf7\u6c42\u5927\u5c0f", "type": "long", "name": "c_bytes"}, {"remark": "\u8bf7\u6c42\u5185\u5bb9", "type": "string", "name": "c_body"}, {"remark": "", "type": "string", "name": "c_type"}, {"remark": "\u670d\u52a1\u7aefip", "type": "string", "name": "s_ip"}, {"remark": "\u670d\u52a1\u7aef\u7aef\u53e3", "type": "long", "name": "s_port"}, {"remark": "\u54cd\u5e94\u5927\u5c0f", "type": "long", "name": "s_bytes"}, {"remark": "\u54cd\u5e94\u5185\u5bb9", "type": "string", "name": "s_body"}, {"remark": "", "type": "string", "name": "s_type"}, {"remark": "\u4e3b\u673a\u5730\u5740", "type": "string", "name": "host"}, {"remark": "url\u95ee\u53f7\u524d\u90e8\u5206", "type": "string", "name": "uri_stem"}, {"remark": "url\u95ee\u53f7\u540e\u90e8\u5206", "type": "string", "name": "uri_query"}, {"remark": "", "type": "string", "name": "referer"}, {"remark": "\u8bf7\u6c42\u65b9\u6cd5", "type": "string", "name": "method"}, {"remark": "\u8bf7\u6c42\u72b6\u6001", "type": "long", "name": "status"}, {"remark": "", "type": "string", "name": "cookie"}, {"remark": "", "type": "string", "name": "useragent"}, {"remark": "", "type": "string", "name": "xforward"}, {"remark": "", "type": "long", "name": "request_time"}, {"remark": "", "type": "string", "name": "request_type"}, {"remark": "", "type": "string", "name": "referer_hit"}, {"remark": "", "type": "string", "name": "order_id"}, {"remark": "", "type": "string", "name": "user_name"}, {"remark": "", "type": "string", "name": "product_id"}, {"remark": "", "type": "string", "name": "product_type"}, {"remark": "", "type": "string", "name": "product_attribute"}, {"remark": "", "type": "long", "name": "product_count"}, {"remark": "", "type": "long", "name": "product_total_count"}, {"remark": "\u5546\u5bb6", "type": "string", "name": "merchant"}, {"remark": "", "type": "double", "name": "order_money_amount"}, {"remark": "", "type": "double", "name": "order_coupon_amount"}, {"remark": "", "type": "double", "name": "order_point_amount"}, {"remark": "", "type": "string", "name": "transaction_id"}, {"remark": "", "type": "string", "name": "receiver_mobile"}, {"remark": "", "type": "string", "name": "receiver_address_country"}, {"remark": "", "type": "string", "name": "receiver_address_province"}, {"remark": "", "type": "string", "name": "receiver_address_city"}, {"remark": "", "type": "string", "name": "receiver_address_detail"}, {"remark": "", "type": "string", "name": "receiver_realname"}, {"remark": "\u64cd\u4f5c\u7ed3\u679c", "type": "string", "name": "result"}, {"remark": "", "type": "string", "name": "geo_city"}], "remark": "\u63d0\u4ea4\u8ba2\u5355", "name": "ORDER_SUBMIT"}, {"fields": [{"remark": "", "type": "string", "name": "id"}, {"remark": "", "type": "string", "name": "pid"}, {"remark": "\u5ba2\u6237\u7aefip", "type": "string", "name": "c_ip"}, {"remark": "", "type": "string", "name": "sid"}, {"remark": "", "type": "string", "name": "uid"}, {"remark": "", "type": "string", "name": "did"}, {"remark": "", "type": "string", "name": "platform"}, {"remark": "", "type": "string", "name": "page"}, {"remark": "\u5ba2\u6237\u7aef\u7aef\u53e3", "type": "long", "name": "c_port"}, {"remark": "\u8bf7\u6c42\u5927\u5c0f", "type": "long", "name": "c_bytes"}, {"remark": "\u8bf7\u6c42\u5185\u5bb9", "type": "string", "name": "c_body"}, {"remark": "", "type": "string", "name": "c_type"}, {"remark": "\u670d\u52a1\u7aefip", "type": "string", "name": "s_ip"}, {"remark": "\u670d\u52a1\u7aef\u7aef\u53e3", "type": "long", "name": "s_port"}, {"remark": "\u54cd\u5e94\u5927\u5c0f", "type": "long", "name": "s_bytes"}, {"remark": "\u54cd\u5e94\u5185\u5bb9", "type": "string", "name": "s_body"}, {"remark": "", "type": "string", "name": "s_type"}, {"remark": "\u4e3b\u673a\u5730\u5740", "type": "string", "name": "host"}, {"remark": "url\u95ee\u53f7\u524d\u90e8\u5206", "type": "string", "name": "uri_stem"}, {"remark": "url\u95ee\u53f7\u540e\u90e8\u5206", "type": "string", "name": "uri_query"}, {"remark": "", "type": "string", "name": "referer"}, {"remark": "\u8bf7\u6c42\u65b9\u6cd5", "type": "string", "name": "method"}, {"remark": "\u8bf7\u6c42\u72b6\u6001", "type": "long", "name": "status"}, {"remark": "", "type": "string", "name": "cookie"}, {"remark": "", "type": "string", "name": "useragent"}, {"remark": "", "type": "string", "name": "xforward"}, {"remark": "", "type": "long", "name": "request_time"}, {"remark": "", "type": "string", "name": "request_type"}, {"remark": "", "type": "string", "name": "referer_hit"}, {"remark": "", "type": "string", "name": "username"}, {"remark": "", "type": "string", "name": "activity_name"}, {"remark": "", "type": "string", "name": "activity_type"}, {"remark": "", "type": "long", "name": "activity_gain_count"}, {"remark": "", "type": "long", "name": "activity_gain_amount"}, {"remark": "", "type": "long", "name": "activity_pay_amount"}, {"remark": "", "type": "string", "name": "acticity_counterpart_user"}, {"remark": "\u64cd\u4f5c\u7ed3\u679c", "type": "string", "name": "result"}, {"remark": "", "type": "string", "name": "geo_city"}], "remark": "\u8425\u9500\u6d3b\u52a8", "name": "ACTIVITY_DO"}, {"fields": [{"remark": "", "type": "string", "name": "id"}, {"remark": "", "type": "string", "name": "pid"}, {"remark": "\u5ba2\u6237\u7aefip", "type": "string", "name": "c_ip"}, {"remark": "", "type": "string", "name": "sid"}, {"remark": "", "type": "string", "name": "uid"}, {"remark": "", "type": "string", "name": "did"}, {"remark": "", "type": "string", "name": "platform"}, {"remark": "", "type": "string", "name": "page"}, {"remark": "", "type": "string", "name": "notices"}, {"remark": "\u5ba2\u6237\u7aef\u7aef\u53e3", "type": "long", "name": "c_port"}, {"remark": "\u8bf7\u6c42\u5927\u5c0f", "type": "long", "name": "c_bytes"}, {"remark": "\u8bf7\u6c42\u5185\u5bb9", "type": "string", "name": "c_body"}, {"remark": "", "type": "string", "name": "c_type"}, {"remark": "\u670d\u52a1\u7aefip", "type": "string", "name": "s_ip"}, {"remark": "\u670d\u52a1\u7aef\u7aef\u53e3", "type": "long", "name": "s_port"}, {"remark": "\u54cd\u5e94\u5927\u5c0f", "type": "long", "name": "s_bytes"}, {"remark": "\u54cd\u5e94\u5185\u5bb9", "type": "string", "name": "s_body"}, {"remark": "", "type": "string", "name": "s_type"}, {"remark": "\u4e3b\u673a\u5730\u5740", "type": "string", "name": "host"}, {"remark": "url\u95ee\u53f7\u524d\u90e8\u5206", "type": "string", "name": "uri_stem"}, {"remark": "url\u95ee\u53f7\u540e\u90e8\u5206", "type": "string", "name": "uri_query"}, {"remark": "", "type": "string", "name": "referer"}, {"remark": "\u8bf7\u6c42\u65b9\u6cd5", "type": "string", "name": "method"}, {"remark": "\u8bf7\u6c42\u72b6\u6001", "type": "long", "name": "status"}, {"remark": "", "type": "string", "name": "cookie"}, {"remark": "", "type": "string", "name": "useragent"}, {"remark": "", "type": "string", "name": "xforward"}, {"remark": "", "type": "long", "name": "request_time"}, {"remark": "", "type": "string", "name": "request_type"}, {"remark": "", "type": "string", "name": "referer_hit"}, {"remark": "", "type": "string", "name": "geo_city"}, {"remark": "", "type": "string", "name": "delay_strategy"}], "remark": "http\u52a8\u6001\u8d44\u6e90\u8bbf\u95eeDelay event", "name": "HTTP_DYNAMIC_DELAY"}, {"fields": [{"remark": "", "type": "string", "name": "id"}, {"remark": "", "type": "string", "name": "pid"}, {"remark": "\u5ba2\u6237\u7aefip", "type": "string", "name": "c_ip"}, {"remark": "", "type": "string", "name": "sid"}, {"remark": "", "type": "string", "name": "uid"}, {"remark": "", "type": "string", "name": "did"}, {"remark": "", "type": "string", "name": "platform"}, {"remark": "", "type": "string", "name": "page"}, {"remark": "", "type": "string", "name": "notices"}, {"remark": "\u5ba2\u6237\u7aef\u7aef\u53e3", "type": "long", "name": "c_port"}, {"remark": "\u8bf7\u6c42\u5927\u5c0f", "type": "long", "name": "c_bytes"}, {"remark": "\u8bf7\u6c42\u5185\u5bb9", "type": "string", "name": "c_body"}, {"remark": "", "type": "string", "name": "c_type"}, {"remark": "\u670d\u52a1\u7aefip", "type": "string", "name": "s_ip"}, {"remark": "\u670d\u52a1\u7aef\u7aef\u53e3", "type": "long", "name": "s_port"}, {"remark": "\u54cd\u5e94\u5927\u5c0f", "type": "long", "name": "s_bytes"}, {"remark": "\u54cd\u5e94\u5185\u5bb9", "type": "string", "name": "s_body"}, {"remark": "", "type": "string", "name": "s_type"}, {"remark": "\u4e3b\u673a\u5730\u5740", "type": "string", "name": "host"}, {"remark": "url\u95ee\u53f7\u524d\u90e8\u5206", "type": "string", "name": "uri_stem"}, {"remark": "url\u95ee\u53f7\u540e\u90e8\u5206", "type": "string", "name": "uri_query"}, {"remark": "", "type": "string", "name": "referer"}, {"remark": "\u8bf7\u6c42\u65b9\u6cd5", "type": "string", "name": "method"}, {"remark": "\u8bf7\u6c42\u72b6\u6001", "type": "long", "name": "status"}, {"remark": "", "type": "string", "name": "cookie"}, {"remark": "", "type": "string", "name": "useragent"}, {"remark": "", "type": "string", "name": "xforward"}, {"remark": "", "type": "long", "name": "request_time"}, {"remark": "", "type": "string", "name": "request_type"}, {"remark": "", "type": "string", "name": "referer_hit"}, {"remark": "", "type": "string", "name": "order_id"}, {"remark": "", "type": "string", "name": "user_name"}, {"remark": "\u5546\u5bb6", "type": "string", "name": "merchant"}, {"remark": "", "type": "string", "name": "cancel_reason"}, {"remark": "", "type": "string", "name": "transaction_id"}, {"remark": "\u64cd\u4f5c\u7ed3\u679c", "type": "string", "name": "result"}, {"remark": "", "type": "string", "name": "geo_city"}], "remark": "\u53d6\u6d88\u8ba2\u5355", "name": "ORDER_CANCEL"}, {"fields": [{"remark": "", "type": "string", "name": "id"}, {"remark": "", "type": "string", "name": "pid"}, {"remark": "\u5ba2\u6237\u7aefip", "type": "string", "name": "c_ip"}, {"remark": "", "type": "string", "name": "sid"}, {"remark": "", "type": "string", "name": "uid"}, {"remark": "", "type": "string", "name": "did"}, {"remark": "", "type": "string", "name": "platform"}, {"remark": "", "type": "string", "name": "page"}, {"remark": "", "type": "string", "name": "notices"}, {"remark": "\u5ba2\u6237\u7aef\u7aef\u53e3", "type": "long", "name": "c_port"}, {"remark": "\u8bf7\u6c42\u5927\u5c0f", "type": "long", "name": "c_bytes"}, {"remark": "\u8bf7\u6c42\u5185\u5bb9", "type": "string", "name": "c_body"}, {"remark": "", "type": "string", "name": "c_type"}, {"remark": "\u670d\u52a1\u7aefip", "type": "string", "name": "s_ip"}, {"remark": "\u670d\u52a1\u7aef\u7aef\u53e3", "type": "long", "name": "s_port"}, {"remark": "\u54cd\u5e94\u5927\u5c0f", "type": "long", "name": "s_bytes"}, {"remark": "\u54cd\u5e94\u5185\u5bb9", "type": "string", "name": "s_body"}, {"remark": "", "type": "string", "name": "s_type"}, {"remark": "\u4e3b\u673a\u5730\u5740", "type": "string", "name": "host"}, {"remark": "url\u95ee\u53f7\u524d\u90e8\u5206", "type": "string", "name": "uri_stem"}, {"remark": "url\u95ee\u53f7\u540e\u90e8\u5206", "type": "string", "name": "uri_query"}, {"remark": "", "type": "string", "name": "referer"}, {"remark": "\u8bf7\u6c42\u65b9\u6cd5", "type": "string", "name": "method"}, {"remark": "\u8bf7\u6c42\u72b6\u6001", "type": "long", "name": "status"}, {"remark": "", "type": "string", "name": "cookie"}, {"remark": "", "type": "string", "name": "useragent"}, {"remark": "", "type": "string", "name": "xforward"}, {"remark": "", "type": "long", "name": "request_time"}, {"remark": "", "type": "string", "name": "request_type"}, {"remark": "", "type": "string", "name": "referer_hit"}, {"remark": "", "type": "string", "name": "user_name"}, {"remark": "\u65e7\u5bc6\u7801", "type": "string", "name": "old_password"}, {"remark": "\u65b0\u5bc6\u7801", "type": "string", "name": "new_password"}, {"remark": "", "type": "string", "name": "verification_token"}, {"remark": "", "type": "string", "name": "verification_token_type"}, {"remark": "\u9a8c\u8bc1\u7801", "type": "string", "name": "captcha"}, {"remark": "\u64cd\u4f5c\u7ed3\u679c", "type": "string", "name": "result"}, {"remark": "", "type": "string", "name": "geo_city"}], "remark": "\u8d26\u6237\u5bc6\u7801\u4fee\u6539", "name": "ACCOUNT_PW_CHANGE"}, {"fields": [{"remark": "", "type": "string", "name": "id"}, {"remark": "", "type": "string", "name": "pid"}, {"remark": "\u5ba2\u6237\u7aefip", "type": "string", "name": "c_ip"}, {"remark": "", "type": "string", "name": "sid"}, {"remark": "", "type": "string", "name": "uid"}, {"remark": "", "type": "string", "name": "did"}, {"remark": "", "type": "string", "name": "platform"}, {"remark": "", "type": "string", "name": "page"}, {"remark": "", "type": "string", "name": "notices"}, {"remark": "\u5ba2\u6237\u7aef\u7aef\u53e3", "type": "long", "name": "c_port"}, {"remark": "\u8bf7\u6c42\u5927\u5c0f", "type": "long", "name": "c_bytes"}, {"remark": "\u8bf7\u6c42\u5185\u5bb9", "type": "string", "name": "c_body"}, {"remark": "", "type": "string", "name": "c_type"}, {"remark": "\u670d\u52a1\u7aefip", "type": "string", "name": "s_ip"}, {"remark": "\u670d\u52a1\u7aef\u7aef\u53e3", "type": "long", "name": "s_port"}, {"remark": "\u54cd\u5e94\u5927\u5c0f", "type": "long", "name": "s_bytes"}, {"remark": "\u54cd\u5e94\u5185\u5bb9", "type": "string", "name": "s_body"}, {"remark": "", "type": "string", "name": "s_type"}, {"remark": "\u4e3b\u673a\u5730\u5740", "type": "string", "name": "host"}, {"remark": "url\u95ee\u53f7\u524d\u90e8\u5206", "type": "string", "name": "uri_stem"}, {"remark": "url\u95ee\u53f7\u540e\u90e8\u5206", "type": "string", "name": "uri_query"}, {"remark": "", "type": "string", "name": "referer"}, {"remark": "\u8bf7\u6c42\u65b9\u6cd5", "type": "string", "name": "method"}, {"remark": "\u8bf7\u6c42\u72b6\u6001", "type": "long", "name": "status"}, {"remark": "", "type": "string", "name": "cookie"}, {"remark": "", "type": "string", "name": "useragent"}, {"remark": "", "type": "string", "name": "xforward"}, {"remark": "", "type": "long", "name": "request_time"}, {"remark": "", "type": "string", "name": "request_type"}, {"remark": "", "type": "string", "name": "referer_hit"}, {"remark": "", "type": "string", "name": "user_name"}, {"remark": "\u5bc6\u7801md5", "type": "string", "name": "password"}, {"remark": "", "type": "string", "name": "register_verification_token"}, {"remark": "", "type": "string", "name": "register_verification_token_type"}, {"remark": "\u9a8c\u8bc1\u7801", "type": "string", "name": "captcha"}, {"remark": "\u64cd\u4f5c\u7ed3\u679c", "type": "string", "name": "result"}, {"remark": "", "type": "string", "name": "register_realname"}, {"remark": "", "type": "string", "name": "register_channel"}, {"remark": "", "type": "string", "name": "invite_code"}, {"remark": "", "type": "string", "name": "geo_city"}], "remark": "\u8d26\u6237\u6ce8\u518c", "name": "ACCOUNT_REGISTRATION"}, {"fields": [{"remark": "", "type": "string", "name": "id"}, {"remark": "", "type": "string", "name": "pid"}, {"remark": "\u5ba2\u6237\u7aefip", "type": "string", "name": "c_ip"}, {"remark": "", "type": "string", "name": "sid"}, {"remark": "", "type": "string", "name": "uid"}, {"remark": "", "type": "string", "name": "did"}, {"remark": "", "type": "string", "name": "platform"}, {"remark": "", "type": "string", "name": "page"}, {"remark": "", "type": "string", "name": "notices"}, {"remark": "\u5ba2\u6237\u7aef\u7aef\u53e3", "type": "long", "name": "c_port"}, {"remark": "\u8bf7\u6c42\u5927\u5c0f", "type": "long", "name": "c_bytes"}, {"remark": "\u8bf7\u6c42\u5185\u5bb9", "type": "string", "name": "c_body"}, {"remark": "", "type": "string", "name": "c_type"}, {"remark": "\u670d\u52a1\u7aefip", "type": "string", "name": "s_ip"}, {"remark": "\u670d\u52a1\u7aef\u7aef\u53e3", "type": "long", "name": "s_port"}, {"remark": "\u54cd\u5e94\u5927\u5c0f", "type": "long", "name": "s_bytes"}, {"remark": "\u54cd\u5e94\u5185\u5bb9", "type": "string", "name": "s_body"}, {"remark": "", "type": "string", "name": "s_type"}, {"remark": "\u4e3b\u673a\u5730\u5740", "type": "string", "name": "host"}, {"remark": "url\u95ee\u53f7\u524d\u90e8\u5206", "type": "string", "name": "uri_stem"}, {"remark": "url\u95ee\u53f7\u540e\u90e8\u5206", "type": "string", "name": "uri_query"}, {"remark": "", "type": "string", "name": "referer"}, {"remark": "\u8bf7\u6c42\u65b9\u6cd5", "type": "string", "name": "method"}, {"remark": "\u8bf7\u6c42\u72b6\u6001", "type": "long", "name": "status"}, {"remark": "", "type": "string", "name": "cookie"}, {"remark": "", "type": "string", "name": "useragent"}, {"remark": "", "type": "string", "name": "xforward"}, {"remark": "", "type": "long", "name": "request_time"}, {"remark": "", "type": "string", "name": "request_type"}, {"remark": "", "type": "string", "name": "referer_hit"}, {"remark": "", "type": "string", "name": "geo_city"}, {"remark": "", "type": "string", "name": "user_name"}, {"remark": "", "type": "string", "name": "transaction_id"}, {"remark": "", "type": "string", "name": "withdraw_amount"}, {"remark": "", "type": "string", "name": "withdraw_type"}, {"remark": "", "type": "string", "name": "card_number"}, {"remark": "", "type": "string", "name": "counterpart_user"}, {"remark": "", "type": "string", "name": "account_balance_before"}, {"remark": "\u64cd\u4f5c\u7ed3\u679c", "type": "string", "name": "result"}], "remark": "\u8d44\u91d1\u53d6\u73b0", "name": "TRANSACTION_WITHDRAW"}, {"fields": [{"remark": "", "type": "string", "name": "id"}, {"remark": "", "type": "string", "name": "pid"}, {"remark": "\u5ba2\u6237\u7aefip", "type": "string", "name": "c_ip"}, {"remark": "", "type": "string", "name": "sid"}, {"remark": "", "type": "string", "name": "uid"}, {"remark": "", "type": "string", "name": "did"}, {"remark": "", "type": "string", "name": "platform"}, {"remark": "", "type": "string", "name": "page"}, {"remark": "", "type": "string", "name": "notices"}, {"remark": "\u5ba2\u6237\u7aef\u7aef\u53e3", "type": "long", "name": "c_port"}, {"remark": "\u8bf7\u6c42\u5927\u5c0f", "type": "long", "name": "c_bytes"}, {"remark": "\u8bf7\u6c42\u5185\u5bb9", "type": "string", "name": "c_body"}, {"remark": "", "type": "string", "name": "c_type"}, {"remark": "\u670d\u52a1\u7aefip", "type": "string", "name": "s_ip"}, {"remark": "\u670d\u52a1\u7aef\u7aef\u53e3", "type": "long", "name": "s_port"}, {"remark": "\u54cd\u5e94\u5927\u5c0f", "type": "long", "name": "s_bytes"}, {"remark": "\u54cd\u5e94\u5185\u5bb9", "type": "string", "name": "s_body"}, {"remark": "", "type": "string", "name": "s_type"}, {"remark": "\u4e3b\u673a\u5730\u5740", "type": "string", "name": "host"}, {"remark": "url\u95ee\u53f7\u524d\u90e8\u5206", "type": "string", "name": "uri_stem"}, {"remark": "url\u95ee\u53f7\u540e\u90e8\u5206", "type": "string", "name": "uri_query"}, {"remark": "", "type": "string", "name": "referer"}, {"remark": "\u8bf7\u6c42\u65b9\u6cd5", "type": "string", "name": "method"}, {"remark": "\u8bf7\u6c42\u72b6\u6001", "type": "long", "name": "status"}, {"remark": "", "type": "string", "name": "cookie"}, {"remark": "", "type": "string", "name": "useragent"}, {"remark": "", "type": "string", "name": "xforward"}, {"remark": "", "type": "long", "name": "request_time"}, {"remark": "", "type": "string", "name": "request_type"}, {"remark": "", "type": "string", "name": "referer_hit"}, {"remark": "", "type": "string", "name": "geo_city"}], "remark": "http click \u4e8b\u4ef6", "name": "HTTP_CLICK"}, {"fields": [{"remark": "\u5ba2\u6237\u7aefip", "type": "string", "name": "c_ip"}, {"remark": "", "type": "string", "name": "page"}, {"remark": "", "type": "string", "name": "uid"}, {"remark": "", "type": "string", "name": "did"}, {"remark": "", "type": "long", "name": "timestamp"}, {"remark": "", "type": "string", "name": "notices"}, {"remark": "", "type": "string", "name": "tags"}, {"remark": "", "type": "double", "name": "scores"}, {"remark": "", "type": "string", "name": "strategies"}], "remark": "\u98ce\u9669\u4e8b\u4ef6", "name": "HTTP_INCIDENT"}]})