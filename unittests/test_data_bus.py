# -*- coding: utf-8 -*-

import json

import pytest

from query_web import app
app.config["TESTING"] = True
test_app = app.test_client()

def test_add_logquery_babel():
    pass
    
def test_del_logquery_babel():
    pass

def test_fetch_logquery_progress():
    pass

def test_fetch_logquery_data():
    pass

def test_ProfileCrawlerPageStatHandler(monkeypatch):
    """
    """
    url_prefix = "/platform/stats/crawler_page_risk"
    from nebula_website import data_client
    url1_one_day_count = {
        '00':1, '01':2, '02':3, '03':4, '04':5, '05':6, '06':7, '07':8, '08':9,
        '09':10, '10':11, '11':12, '12':13, '13':14, '14':15, '15':16, '16':17,
        '17':18, '18':19, '19':20, '20':21, '21':22, '22':23, '23':24
    }
    def mock_get_profile_crawler_page_risk(current_day, pages):
        pages = set(pages)
        d = { "url1": {
            "page__crawler_request_amount__profile":url1_one_day_count,
            "page__crawler_crawler_risk_amount__profile": url1_one_day_count,
            "page__crawler_latency__profile":url1_one_day_count,
            "page__crawler_upstream_size__profile":url1_one_day_count,
            "page__crawler_status_2__profile":url1_one_day_count,
            "page__crawler_status_3__profile":url1_one_day_count,
            "page__crawler_status_4__profile":url1_one_day_count,
            "page__crawler_status_5__profile":url1_one_day_count,
        },
              "url2":None
        }
        return True, dict( (k,v) for k,v in d.iteritems() if k in pages)
    monkeypatch.setattr(data_client, "get_profile_crawler_page_risk", mock_get_profile_crawler_page_risk)
    
    rv = test_app.get("%s?current_day=%s&pages=%s" % (url_prefix, 199999999, "url1"))
    # dir rv????
    continuous_data = dict()
    for k in url1_one_day_count.keys():
        d = continuous_data[k] = dict()
        for kk in ("count","latency", "crawler_count", "upload_bytes", "2XX", "3XX", "4XX", "5XX"):
            d[kk] = url1_one_day_count.get(k)
#        d["latency"] = url1_one_day_count.get(k) / float(d["count"] or 1)

    expect_result = dict(
        status=200,
        msg='ok',
        values=[dict(url="url1",
                     count=300,
                     crawler_count=300,
                     latency=4900/float(300),
                     upload_bytes=300,
                     continuous_data=continuous_data)]
    )
    j = json.loads(rv.data)
    assert j == expect_result