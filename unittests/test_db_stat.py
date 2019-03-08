# -*- coding: utf-8 -*-

import pytest

def test_DPS_account_query(monkeypatch):
    """
    测试用例：
    - uid值为None、空字符串时合并
    - 是否测试的原则是所有为测试才显示测试
    - 是否白名单的原则是所有为白名单才显示白名单
    """

    from nebula_website.views.db_stat import db, DPS_account_query
    class Q(object):
        def fetchall(self):
            # uid None, "" 合并
            # test, decision 合并规则
            return [dict(uid=None, count=1, min_ts=10, max_ts=20, test=1,
                         decision='accept', strategy_name="account_x", ip="127.0.0.1",
                         geo_city="本地", tag="撞库"),
                    dict(uid="", count=2, min_ts=3, max_ts=40, test=1, decision="reject",
                         strategy_name="account_x", ip="127.0.0.2", geo_city="本地",
                         tag="撞库"),
                    dict(uid="1", count=1, min_ts=1, max_ts=2, test=1, decision="accept",
                         strategy_name="account_x", ip="1", geo_city="本地", tag="撞库"),
                    dict(uid="1", count=1, min_ts=1, max_ts=2, test=1, decision="accept",
                         strategy_name="account_x", ip="2", geo_city="本地", tag="撞库"),
                    dict(uid="1", count=1, min_ts=1, max_ts=2, test=0, decision="accept",
                         strategy_name="account_x", ip="2", geo_city="本地", tag="撞库"),
            ]
    class DB_Engine(object):
        def execute(self, *args, **kwargs):
            return Q()

    def get_engine():
        return DB_Engine()
    monkeypatch.setattr(db, "get_engine", get_engine)
    result =  DPS_account_query(None, None, None, None, None)
    expect_result = {
        "":{
            "origin":{ "127.0.0.1":{"tags":{ "撞库":1 },
                                    "source_ip":"127.0.0.1",
                                    "geo_city":"本地"},
                       "127.0.0.2":{"tags":{ "撞库":2 },
                                    "source_ip":"127.0.0.2",
                                    "geo_city":"本地"},
                   },
            "first_time":3,
            "last_time":40,
            "is_test":1,
            "is_white":0,
            "strategys":{ "account_x": 3},},
        "1":{
            "origin":{ "1":{"tags":{ "撞库":1 },
                            "source_ip":"1",
                            "geo_city":"本地"},
                       "2":{"tags":{ "撞库":2 },
                            "source_ip":"2",
                            "geo_city":"本地"},
                   },
            "first_time":1,
            "last_time":2,
            "is_test":0,
            "is_white":1,
            "strategys":{ "account_x": 3},
        },
    }
    assert expect_result == result
    
def test_DPS_get_risk_score(monkeypatch):
    from nebula_website.views.db_stat import DPS_get_risk_score
    from nebula_website.views import db_stat
    """
    Premise: input strategy count are same category, so just take the mean
    """

    def mock_strategy_weigh():
        return dict(a=dict(score=200), b=dict(score=300), c=dict(score=500))
    monkeypatch.setattr(db_stat, "get_strategy_weigh", mock_strategy_weigh )
    input_strategy_dict = dict(a=1, b=1, c=1)
    
    output_score = DPS_get_risk_score(input_strategy_dict)
    assert int(output_score*1000) == 33333 # 33.33

def test_DPS_write_fn(tmpdir):
    """
    1. max line 65536
    """
    from nebula_website.views.db_stat import DPS_write_fn
    def count_line(fn):
        c = 0
        with open(fn, 'r') as f:
            for _ in f:
                c += 1
        return c
    # 写入65534 + 1 行
    # 实际也有 65535行
    valid_count = 65535
    show_cols = ["a",]
    tmpdir = str(tmpdir.join("tmp.txt"))
    query_result = ( dict(a=1) for _ in xrange(valid_count-1) )
    DPS_write_fn(tmpdir, show_cols, query_result)
    assert count_line(tmpdir) == valid_count
    
    # 写入数据量65546 + 1 cols
    # 实际只有65536最大行
    max_count = 65536
    query_result = ( dict(a=1) for _ in xrange(max_count+10) )
    DPS_write_fn(tmpdir, show_cols, query_result)
    assert count_line(tmpdir) == max_count
    
def test_DPS_read_fn(monkeypatch, tmpdir):
    """
    1. cols isn't expect ones AttributeError
    2. read lines between start_offset and end_offset, boundary issue
    3. maybe more, specified cols's type
    
    Dependency: DPS_write_fn
    """
    from nebula_website.views.db_stat import DPS_read_fn, DPS_write_fn
    
    from nebula_website.views import db_stat
    from db_stat_web import app
    app.config["TESTING"] = True
    monkeypatch.setattr(db_stat, "current_app", app.test_client())    

    # 1. cols isn't expect ones AttributeError
    write_cols = ["a", "b"]
    expect_cols = ["a", "c"]
    tmpdir = str(tmpdir.join("tmp.txt"))
    DPS_write_fn(tmpdir, write_cols, [])
    with pytest.raises(AttributeError):
        DPS_read_fn(tmpdir, 1, 2, expect_cols)

    # regular procedure and check the cols return type
    cols = ["is_test", "tags", "geo_city"]
    input_result = [
        dict(is_test=1, tags={"a":10}, geo_city=u'\u722c\u866b'),
        dict(is_test=0, tags={"b":1}, geo_city=u'\u722c\u866b'),
        dict(is_test=1, tags={"c":5}, geo_city=u'\u722c\u866b'),
    ]
    DPS_write_fn(tmpdir, cols, input_result)
    
    result = DPS_read_fn(tmpdir, 2, 3, cols)
    print result
    assert result[0] == input_result[2]
    
    assert isinstance(result[0].get("is_test"), int)
    assert isinstance(result[0].get("tags"), dict)
    assert isinstance(result[0].get("geo_city"), unicode)
    assert result[0].get("geo_city") == u'\u722c\u866b'

def test_DashboardPageSearch():
    """
    1. 400
    2. 503
    3. 405
    4. check first query file created, return total and file total match?
    5. no file , post
    """
    from db_stat_web import app
    app.config["TESTING"] = True
    test_app = app.test_client()
    # invalid http method
    rv = test_app.put("/platform/stats/dashboard_page_search?uri_stem=%s" % "http://abc.a.com")
    assert rv.status_code == 405
    
    # no uri_stem or fromtime or endtime args
    rv = test_app.get("/platform/stats/dashboard_page_search?uri_stem=%s" % "http://abc.a.com")
    assert rv.status_code == 400
    assert rv.data == "uri_stem, fromtime, endtime query args are required."
    
    # invalid dashboard type
    invalid_dashboard_type = "mad"
    rv = test_app.get("/platform/stats/dashboard_page_search?uri_stem=1&fromtime=1&endtime=1&dashboard=%s" % invalid_dashboard_type)
    assert rv.status_code == 400
    assert rv.data == "Invalid dashboard %s" % invalid_dashboard_type
