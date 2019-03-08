# -*- coding: utf-8 -*-

import pytest
import gevent

from nebula_website.services import notice_mail

def mock_strategy_weigh():
    return {"visit_H_loginurl_5m_ip":dict(name="visit_H_loginurl_5m_ip",
                                          tags=[u"爬虫", u"撞库"],
                                          remark="IP5分钟内多次访问登录页面",),
            "visit_H_authurl_5m_ip":dict(name="visit_H_authurl_5m_ip",
                                         tags=[u"爬虫"],
                                         remark="IP5分钟内多次访问认证页面"),
            "visit_H_loginurl_5m_user":dict(name="visit_H_loginurl_5m_user",
                                            tags=[u"爬虫", u"撞库"],
                                            remark="USER5分钟内多次访问登录页面"),
            "visit_H_authurl_5m_user":dict(name="visit_H_authurl_5m_user",
                                           tags=[u"爬虫", u"撞库"],
                                           remark="USER5分钟内多次访问认证页面"),
        }

Mock_Configs = {
        "alerting.status":"true",
        "alerting.delivery_interval":5,
        "alerting.send_email":"",
        "alerting.to_emails":"",
        "alerting.smtp_server":"",
        "alerting.smtp_account":"",
        "alerting.smtp_password":"",
        "alerting.smtp_ssl":"",
        "alerting.smtp_port":"",
    }

def mock_configs(key, default=None):
    global Mock_Configs
    return Mock_Configs.get(key, default)

def test_get_body_data(monkeypatch):
    monkeypatch.setattr(notice_mail, "get_strategy_weigh", mock_strategy_weigh)
    
    input_notices = [
        {"scene_name":"OTHERS",
         "uri_stem":"/test",
         "check_type":"IP",
         "strategy_name":"visit_H_authurl_5m_ip",
         "timestamp":1509102502730,
         "key":"0.0.0.0"}, 
        {"scene_name":"VISITOR",
         "uri_stem":"/test1",
         "check_type":"IP",
         "strategy_name":"visit_H_loginurl_5m_ip",
         "timestamp":1509102502730,
         "key":"0.0.0.0"}, 
        {"scene_name":"VISITOR",
         "uri_stem":"/test2",
         "check_type":"IP",
         "strategy_name":"visit_H_loginurl_5m_ip",
         "timestamp":1509102502730,
         "key":"0.0.0.0"}, 
        {"scene_name":"VISITOR",
         "uri_stem":"/test2",
         "check_type":"USER",
         "strategy_name":"visit_H_authurl_5m_user",
         "timestamp":1509102502730,
         "key":"0.0.0.0"}, 
        {"scene_name":"VISITOR",
         "uri_stem":"/test2",
         "check_type":"USER",
         "strategy_name":"visit_H_loginurl_5m_user",
         "timestamp":1509102502730,
         "key":"0.0.0.0"}, 
        {"scene_name":"VISITOR",
         "uri_stem":"/test2",
         "check_type":"USER",
         "strategy_name":"visit_H_loginurl_5m_user",
         "timestamp":1509098902730,
         "key":"0.0.0.0"}, 
        {"scene_name":"VISITOR",
         "uri_stem":"/test2",
         "check_type":"USER",
         "strategy_name":"visit_H_loginurl_5m_user",
         "timestamp":1509098902730,
         "key":"0.0.0.1"}, 
    ]
    assume_outputs = [
        {'pages': [
            {'dimensions': [
                {'strategies': [
                    {'hours': [
                        {'keys': set(['0.0.0.0']), 'hour': u'10.27 11\u65f6'}],
                     'remark': u'IP5\u5206\u949f\u5185\u591a\u6b21\u8bbf\u95ee\u8ba4\u8bc1\u9875\u9762',
                     'tags': [u'\u722c\u866b'],
                     'strategy': 'visit_H_authurl_5m_ip'}],
                 'dimension': 'IP'}],
             'page': '/test'}],
         'scene': u"其他场景"},
        {'pages': [
            {'dimensions': [
                {'strategies': [
                    {'hours': [
                        {'keys': set(['0.0.0.0']),
                         'hour': u'10.27 11\u65f6'}],
                     'remark': u'IP5\u5206\u949f\u5185\u591a\u6b21\u8bbf\u95ee\u767b\u5f55\u9875\u9762',
                     'tags': [u'\u722c\u866b', u'\u649e\u5e93'],
                     'strategy': 'visit_H_loginurl_5m_ip'}],
                 'dimension': 'IP'}],
             'page': '/test1'},
            {'dimensions': [
                {'strategies': [
                    {'hours': [
                        {'keys': set(['0.0.0.0']),
                         'hour': u'10.27 11\u65f6'}],
                     'remark': u'IP5\u5206\u949f\u5185\u591a\u6b21\u8bbf\u95ee\u767b\u5f55\u9875\u9762',
                     'tags': [u'\u722c\u866b', u'\u649e\u5e93'],
                     'strategy': 'visit_H_loginurl_5m_ip'}],
                 'dimension': 'IP'},
                {'strategies': [
                    {'hours': [
                        {'keys': set(['0.0.0.0']),
                         'hour': u'10.27 11\u65f6'},
                        {'keys': set(['0.0.0.1', '0.0.0.0']),
                         'hour': u'10.27 10\u65f6'}],
                     'remark': u'USER5\u5206\u949f\u5185\u591a\u6b21\u8bbf\u95ee\u767b\u5f55\u9875\u9762',
                     'tags': [u'\u722c\u866b', u'\u649e\u5e93'],
                     'strategy': 'visit_H_loginurl_5m_user'},
                    {'hours': [
                        {'keys': set(['0.0.0.0']),
                         'hour': u'10.27 11\u65f6'}],
                     'remark': u'USER5\u5206\u949f\u5185\u591a\u6b21\u8bbf\u95ee\u8ba4\u8bc1\u9875\u9762',
                     'tags': [u'\u722c\u866b', u'\u649e\u5e93'],
                     'strategy': 'visit_H_authurl_5m_user'}],
                 'dimension': 'USER'}],
             'page': '/test2'}],
         'scene': u"访客风险"}]
    assert notice_mail.get_body_data(input_notices) == assume_outputs
    
# test_send_mail pass
    
def test_notice_mail_server(monkeypatch, app):
    global Mock_Configs
    #check interval time?
    # 0 1 1min
    # 1 1 2min
    # 1 1 1min 2min
    # 0 0 2min 1min
    nm = notice_mail.NoticeMailServer(app, "temp")
    def mock_query_job(*args, **kwargs):
        return list()
    def mock(*args,**kwargs):
        return
    monkeypatch.setattr(nm, "query_job", mock_query_job)
    monkeypatch.setattr(notice_mail, "get_body_data", mock)
    monkeypatch.setattr(notice_mail, "render", mock)
    monkeypatch.setattr(notice_mail, "send_mail", mock)
    monkeypatch.setattr(notice_mail, "get_config", mock_configs)
    
    Mock_Configs["alerting.status"] = "0"
    Mock_Configs["alerting.delivery_interval"] = 1
    assert nm._run_times == 0
    nm.start()
    gevent.sleep(5)
    # first sleep
    assert nm._status == "sleep"
    assert nm._this_enable == False
    assert nm._last_sleeptime == None
    assert nm._run_times == 1
    
    # second sleep
    gevent.sleep(60)
    assert nm._run_times == 2
    assert nm._status == "sleep"
    assert nm._this_enable == False
    assert 60*1000 + 1000 > nm._this_runtime - nm._last_sleeptime > 60*1000 -1000
    Mock_Configs["alerting.delivery_interval"] = 2
    
    # third sleep
    gevent.sleep(60)
    # fourth sleep
    gevent.sleep(120)
    assert nm._run_times == 4
    assert nm._status == "sleep"
    assert nm._this_enable == False
    assert 120*1000 +1000 > nm._this_runtime - nm._last_sleeptime > 120*1000 -1000
    
# @todo 回头挂到app上，出个接口看backend service 状态
    