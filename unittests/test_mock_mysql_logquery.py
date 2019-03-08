# -*- coding: utf-8 -*-

import json

import pytest

from nebula_website.views import logquery as logquery_view

from nebula_website.managers import logquery

from nebula_website.managers.logquery import LogQueryDao

def test_crud(monkeypatch, app):
    req = {
        "fromtime":150,
        "endtime":200,
        "terms":[{"op":"!=", "right": "117.136.66.243","left": "c_ip"}],
        "event_name" : "HTTP_DYNAMIC",
        "show_cols": ["s_body","c_ip","uid","timestamp"],
        "remark":"a"
    }
    app.register_blueprint(logquery_view.mod)
    from nebula_website.models import db
    db.init_app(app)
    db.app = app
    db.create_all()
    test_app = app.test_client()
    
    # before add
    LogQueryDao.clear()
    assert LogQueryDao.get_logquery_config_count() == 0
    logquery.LogQuery_Status = None
    LogQuery_Status = LogQueryDao.get_logquery_status()
    assert not LogQuery_Status.keys()

    def mock_add_logquery_job(*args, **kwargs):
        return True, None
    monkeypatch.setattr(logquery, "add_logquery_job", mock_add_logquery_job)
    
    # add
    rv = test_app.post("/platform/persistent_query", data=json.dumps(req),
                       content_type = 'application/json')
    assert rv.status_code == 200
    j = json.loads(rv.data)
    assert j["status"] == 200
    
    # testify LogQuery_Status
    req["status"] = "wait"
    
    LogQuery_Status = LogQueryDao.get_logquery_status()
    assert len(LogQuery_Status.keys()) == 1
    lq_status = LogQuery_Status[LogQuery_Status.keys()[0]]
    assert lq_status["remark"] == req["remark"]
    assert lq_status["status"] == req["status"]
    assert LogQueryDao.get_logquery_config_count() == 1
    
    # get
    rv = test_app.get("/platform/persistent_query")
    assert rv.status_code == 200
    j = json.loads(rv.data)
    jj = j["values"][0]
    in_lq_id = jj.pop("id")
    jj.pop("error")
    assert jj == req
    
    # before delete
    def mock_delete_logquery_job(*args, **kwargs):
        return True, None
    monkeypatch.setattr(logquery, "delete_logquery_job", mock_delete_logquery_job)
    
    # delete
    rv = test_app.delete("/platform/persistent_query/%s" % in_lq_id)
    assert rv.status_code == 200
    j = json.loads(rv.data)
    assert j["status"] == 200
