# -*- coding: utf-8 -*-

import json

import unittest

import pytest
import gevent

from nebula_website.managers import logquery

from nebula_website.managers.logquery import LogQueryDao
from nebula_website.models import LQ_Process_Status, LQ_Success_Status, LQ_Fail_Status,LQ_Wait_Status

from db_stat_web import app
from .utils import Storage

app.config["TESTING"] = True
test_app = app.test_client()
    
def test_get_progress(monkeypatch):
    logquery.LogQuery_Status = {1:{"id":1, "status":"process",
                   "progress":0.32, "error":None},# 正在查询的id以及进度
                2:{"id":2, "status":"wait"},# 正在等待的id
                3:{"id":3, "status":"failed", "progress":None,
                   "error":"miss"}, # 出错的id以及信息
                4:{"id":4, "status":"success", "download_path":"",
                   "filesize":1029012, "total":238}
    }
    
    rv = test_app.get("/platform/persistent_query/progress")
    assert rv.status_code == 200
    j = json.loads(rv.data)
    assert j["status"] == 200
    assert j["values"] == [
        dict(id=1, status="process", progress=0.32, error=None),
        dict(id=2, status="wait", progress=None, error=None),
        dict(id=3, status="failed", progress=None, error="miss"),
        dict(id=4, status="success", progress=None, error=None),
    ]
    
def test_get_data(monkeypatch):
    values = [
      {
        "did": "f4d39d57bafdb3b058a7d3f1af22c3c36259f5b58e760c5e9a61b10e",
        "timestamp": "1500278473443",
        "c_ip": "220.249.64.23",
        "uid": ""
      },
      {
        "did": "f4d39d57bafdb3b058a7d3f1af22c3c36259f5b58e760c5e9a61b10e",
        "timestamp": "1500278477228",
        "c_ip": "220.249.64.23",
        "uid": ""
      }
    ]
    lq_id = 1
    LogQuery_Status = {1:dict(total=5, download_path="a", filesize=10)}
    lq = LogQuery_Status[lq_id]
    
    def mock_fetch_logquery_data(*args):
        return True, dict(data=values)
    monkeypatch.setattr(logquery, "fetch_logquery_data", mock_fetch_logquery_data)
    
    logquery.LogQuery_Status = LogQuery_Status
    
    rv = test_app.get("/platform/persistent_query/data?id=%s&page=%s&page_count=%s" % (lq_id,1,1))
    assert rv.status_code == 200
    j = json.loads(rv.data)
    assert j == {'status': 200, 'msg': 'ok', 'values':values,
                 'total': lq["total"], "id": lq_id,
                 'download_path':lq["download_path"],
                 'filesize':lq["filesize"]}

def test_logquery_notify_server_always_wait(monkeypatch):
    """
    0. online 挂了, before create
    1. 一直等待
    1.5 一直等待, online挂了
    2. wait -> process
    3. process -> process
    4. 一直process?
    5. process -> success
    6. wait -> failed
    7. 重启之后成功的任务需要补上filesize, total
    """
    from nebula_website import babel
    monkeypatch.setattr(babel, "getLogQueryProgressServer", lambda: None)
    
    def mock_update_logquery_config(*args):
        return

    monkeypatch.setattr(LogQueryDao, "update_logquery_config", mock_update_logquery_config)
    
    lq_server = logquery.LogQueryServer(app)
    
    # 1. 一直等待
    logquery.LogQuery_Status = {
        1:{"id":1, "status":LQ_Wait_Status},# 正在等待的id
    }
    
    monkeypatch.setattr(logquery, "fetch_logquery_progress", lambda: (False, "mock error"))
    lq_server.start()
    gevent.sleep(40)
    LogQueryDao.get_logquery_status()[1]["status"] == LQ_Fail_Status
    
    # 1.5 一直等待，online挂了之后重启丢失之前任务信息
    logquery.LogQuery_Status = {
        1:{"id":1, "status":LQ_Wait_Status},# 正在等待的id
    }
    monkeypatch.setattr(logquery, "fetch_logquery_progress", lambda: True, Storage(data=[]))
    lq_server.start()
    gevent.sleep(40)
    LogQueryDao.get_logquery_status()[1]["status"] == LQ_Fail_Status

    # 2. wait -> process
    logquery.LogQuery_Status = {
        1:{"id":1, "status":LQ_Wait_Status},# 正在等待的id
    }
    mock_data = Storage(data=[dict(id=1, status=LQ_Process_Status, progress=0.1)])
    monkeypatch.setattr(logquery, "fetch_logquery_progress", lambda: True, mock_data)
    lq_server.start()
    ls = LogQueryDao.get_logquery_status()
    assert ls[1]["status"] == LQ_Process_Status
    assert ls[1]["progress"] == 0.1
    
    # 3. process -> process
    logquery.LogQuery_Status = {
        1:{"id":1, "status":LQ_Process_Status, "progress":0.1},
    }
    mock_data = Storage(data=[dict(id=1, status=LQ_Process_Status, progress=0.2)])
    monkeypatch.setattr(logquery, "fetch_logquery_progress", lambda: True, mock_data)
    lq_server.start()
    ls = LogQueryDao.get_logquery_status()
    assert ls[1]["status"] == LQ_Process_Status
    assert ls[1]["progress"] == 0.2
    
    # 4. 一直process? > 1?
    
    # 5. wait, process -> success
    logquery.LogQuery_Status = {
        1:{"id":1, "status":LQ_Process_Status, "progress":0.1},
        2:{"id":2, "status":LQ_Wait_Status,},
    }
    mock_data = Storage(data=[dict(id=1, status=LQ_Success_Status, total=1, filesize=1, download_path='mock'), dict(id=2, status=LQ_Success_Status, total=2, filesize=2, download_path='mock2')])
    monkeypatch.setattr(logquery, "fetch_logquery_progress", lambda: True, mock_data)
    lq_server.start()
    ls = LogQueryDao.get_logquery_status()
    assert ls[1]["status"] == LQ_Success_Status
    assert ls[1]["filesize"] == 1
    assert ls[1]["download_path"] == "mock"
    assert ls[1]["total"] == 1

    assert ls[2]["status"] == LQ_Success_Status
    assert ls[2]["filesize"] == 2
    assert ls[2]["download_path"] == "mock2"
    assert ls[2]["total"] == 2
    
    # 6. wait, process -> failed 
    logquery.LogQuery_Status = {
        1:{"id":1, "status":LQ_Process_Status, "progress":0.1},
        2:{"id":2, "status":LQ_Wait_Status,},
    }
    mock_data = Storage(data=[dict(id=1, status=LQ_Fail_Status, error="mockerror"),
                          dict(id=2, status=LQ_Fail_Status, error="mockerror2"),])
    monkeypatch.setattr(logquery, "fetch_logquery_progress", lambda: True, mock_data)
    lq_server.start()
    ls = LogQueryDao.get_logquery_status()
    assert ls[1]["status"] == LQ_Fail_Status
    assert ls[1]["error"] == "mockerror"
    assert ls[2]["status"] == LQ_Fail_Status
    assert ls[2]["error"] == "mockerror2"
    
    # 7. 重启之后成功的任务需要补上filesize, total
    logquery.LogQuery_Status = {
        1:{"id":1, "status":LQ_Success_Status},
    }
    mock_data = Storage(data=[dict(id=1, status=LQ_Success_Status, total=1, download_path="mock_path", filesize=10)])
    monkeypatch.setattr(logquery, "fetch_logquery_progress", lambda: True, mock_data)
    lq_server.start()
    ls = LogQueryDao.get_logquery_status()
    assert ls[1]["status"] == LQ_Success_Status
    assert ls[1]["filesize"] == 10
    assert ls[1]["download_path"] == "mock_path"
    assert ls[1]["total"] == 1
    mock_data = Storage(data=[dict(id=1, status=LQ_Success_Status, total=2, download_path="mock_path1", filesize=11)])
    gevent.sleep(8)
    ls = LogQueryDao.get_logquery_status()
    assert ls[1]["status"] == LQ_Success_Status
    assert ls[1]["filesize"] == 10
    assert ls[1]["download_path"] == "mock_path"
    assert ls[1]["total"] == 1

class CheckLogQueryBabelMock(object):
    """
    Check LogQuery Babel MockServer's input and output
    """

    def __init__(self):
        self.lq = dict(
            id=1,
            fromtime=150,
            endtime=200,
            terms=[{"op":"!=", "right": "117.136.66.243","left": "c_ip"}],
            name= "HTTP_DYNAMIC",
            show_cols= ["s_body","c_ip","uid","timestamp"],
            remark="a")

    def run(self):
        self.babel_add_logquery_job()
        self.babel_fetch_logquery_status()
        self.babel_fetch_logquery_data()
        self.babel_delete_logquery_job()

    def babel_add_logquery_job(self):
        # 测试新增日志查询任务
        success, d = logquery.add_logquery_job(self.lq["id"], self.lq["fromtime"],
                                               self.lq["endtime"], self.lq["terms"],
                                               self.lq["show_cols"], self.lq["name"],
                                               self.lq["remark"])
        assert success, d

    def babel_delete_logquery_job(self):
        # 测试删除日志查询任务
        success, d = logquery.delete_logquery_job(self.lq["id"])
        assert success, d
    
    def babel_fetch_logquery_data(self):
        # 测试获取日志查询数据
        success, d = logquery.fetch_logquery_data(self.lq["id"], 1, 20)
        assert success, d
        
    def babel_fetch_logquery_status(self):
        # 测试获取日志查询任务状态
        # 那边没了
        success, d = logquery.fetch_logquery_progress()
        assert success, d

if __name__ == '__main__':
    m = CheckLogQueryBabelMock()
    m.run()