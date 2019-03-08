# -*- coding: utf-8 -*-
import traceback, smtplib, logging, time
from os import path as opath
from email.mime.text import MIMEText
from collections import defaultdict
from datetime import datetime
from functools import partial

from sqlalchemy import text
import gevent
from gevent import Greenlet

from nebula_website.cache import get_strategy_weigh, get_config
from nebula_website.utils import render
from nebula_website.models import db

logger = logging.getLogger("nebula.services.notice_mail")

def get_alarm_hour_str(timestamp, f="%m.%d %H时"):
    ts = timestamp/1000.0
    d = datetime.fromtimestamp(ts)
    return datetime.strftime(d, f)
    
get_alarm_interval_str = partial(get_alarm_hour_str, f="%Y.%m.%d %H:%M")

Notice_Query = text("SELECT scene_name, uri_stem, check_type, strategy_name, timestamp, `key`, test FROM notice WHERE timestamp >= :fromtime AND timestamp < :endtime")

def get_scene_translate(scene_en):
    t = dict(VISITOR=u"访客风险",
             ACCOUNT=u"账户风险",
             ORDER=u"订单风险",
             TRANSACTION=u"支付场景",
             MARKETING=u"营销场景",
             OTHERS=u"其他场景",
    )
    return t.get(scene_en, scene_en)
    
def send_mail(body):
    sender = get_config("alerting.send_email", '')
    receiver = get_config("alerting.to_emails", '')
    subject = get_config("alerting.email_topic", 'nebula alarms')
    smtpserver = get_config("alerting.smtp_server", '')
    username = get_config("alerting.smtp_account", '')
    password = get_config("alerting.smtp_password", '')
    ssl = get_config("alerting.smtp_ssl", '0')
    port = get_config("alerting.smtp_port", "0")
    port = int(port)
    msg = MIMEText(body, 'html', 'utf-8')
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = receiver
    receiver = receiver.split(",")
#    logger.debug(u"""!!! sending notice mail, \n stmpserver: %s\n port: %s\n username: %s\n \
#password: %s\n sender: %s\n receiver: %s\n ssl: %s\n body: %s"""
#                 , smtpserver, port, username, password, sender, receiver, ssl, body.decode("utf8"))
    
    try:
        if ssl.lower() in {"yes", "y", "1", "true"}:
            smtp = smtplib.SMTP_SSL(host=smtpserver, port=port)
        else:
            smtp = smtplib.SMTP(host=smtpserver, port=port)
        if username and password:
            smtp.login(username, password)
        smtp.sendmail(sender, receiver, msg.as_string())
        smtp.quit()
    except Exception:
        logger.error("Sent Notice mail smtp error !!!")
        logger.error(traceback.format_exc())

    logger.debug("!!! sent notice mail for {} bytes".format(len(body)))

def get_body_data(notices):
    """
    input:
    [{"scene_name":, "uri_stem":, "check_type":, "strategy_name":, "timestamp":, "key":}]
    output:
    [{
    scene: ""
    pages: [{
        page: ""
        dimensions:[{
          dimension: ""
          strategies:[{
            strategy: ""
            remark: ""
            tags:[]
            hours:[{
              hour: ""
              keys:[]
            }]
          }]
        }]
      }]
    }]
    """

    if not notices:
        return None
    
    strategy_weigh = get_strategy_weigh()
    inner_result = defaultdict(set)
    for n in notices:
        inner_key = (n["scene_name"], n["uri_stem"], n["check_type"],
                     n["strategy_name"], get_alarm_hour_str(n["timestamp"]).decode('utf8'))
        inner_result[inner_key].add(n["key"])
    # scene_name, uri_stem, check_type, strategy_name, hour : set(keys)
    
    tmp_hour_result = defaultdict(list)
    for k,v in inner_result.iteritems():
        tmp_key = k[:-1]
        tmp_hour_result[tmp_key].append(dict(hour=k[-1],keys=v))
    # scene_name, uri_stem, check_type, strategy_name: [{hour:"",keys=set(keys)}]    
        
    tmp_strategy_result = defaultdict(list)
    for k,v in tmp_hour_result.iteritems():
        tmp_key = k[:-1]
        sw = strategy_weigh.get(k[-1])
        remark = sw.get("remark")
        if not isinstance(remark, unicode):
            remark = remark.decode('utf8')
        tags = []
        for _ in sw.get("tags"):
            if isinstance(_, unicode):
                tags.append(_)
            else:
                tags.append(_.decode("utf8"))
        tmp_strategy_result[tmp_key].append(dict(strategy=k[-1], remark=remark,
                                                 tags=tags, hours=v))
    # scene_name, uri_stem, check_type: [{strategy:"", remark:"", tags:[],hours:[{hour:"",keys=set(keys)}]}, {}]
        
    tmp_dimension_result = defaultdict(list)
    for k,v in tmp_strategy_result.iteritems():
        tmp_key = k[:-1]
        tmp_dimension_result[tmp_key].append(dict(dimension=k[-1],strategies=v))
    # scene_name, uri_stem: [{dimension:"", strategies:[{strategy:"", remark:"", tags:[],hours:[{hour:"",keys=set(keys)}]}, {}]}, {} ]
        
    tmp_page_result = defaultdict(list)
    for k,v in tmp_dimension_result.iteritems():
        tmp_key = k[:-1]
        tmp_page_result[tmp_key].append(dict(page=k[-1],dimensions=v))
    # scene_name: [ {page:"", dimensions:[{dimension:"", strategies:[{strategy:"", remark:"", tags:[],hours:[{hour:"",keys=set(keys)}]}, {}]}, {} ]},{} ]
    
    result = list()
    for k,v in tmp_page_result.iteritems():
        result.append(dict(scene=k[-1],pages=v))
    for s in result:
        s['scene'] = get_scene_translate(s['scene'])
    return result
    
def query_job(DB_Engine, sql, result_list=None, **kwargs):
        if result_list is None:
            result_list = dict()
    
        q = DB_Engine.execute(sql, **kwargs)
        for scene_name, uri_stem, check_type, strategy_name, timestamp, key, test in q.fetchall():
            result_list.append(dict(scene_name=scene_name, uri_stem=uri_stem,
                                    check_type=check_type, strategy_name=strategy_name,
                                    timestamp=timestamp, key=key, test=test))
        return result_list

Service_Name = "[Service] Notice Warning Mail"

# todo service costs
def send_alarm_task(template_path):
    template_fn = opath.join(template_path, "mail.html")
    try:
        with db.app.app_context():
            # default 3600s
            interval = int(get_config("alerting.delivery_interval", '60')) * 60
            logger.debug("fetch interval: %s", interval)

            n = time.time()
            endtime = int(n *1000)
            fromtime = endtime - interval * 1000
            
            # 如果拉不到config也会默认不开启配置
            enable = get_config("alerting.status", "0")
            if enable.lower() not in {"true", "yes", "y", "1"}:
                return
            # fetch notices
            notices = list()
            
            DB_Engine = db.get_engine()
            try:
                notices = query_job(DB_Engine, Notice_Query, notices,
                                    fromtime=fromtime, endtime=endtime)
            except Exception:
                logger.error("===== %s ===== Error When query notices!!" % Service_Name)
                logger.error(traceback.format_exc())
                return
            # filter test notices
            is_test_needed = get_config("alerting.need_test", '1')
            if is_test_needed.lower() not in {"true", "yes", "y", "1"}:
                notices = filter(lambda n: not n["test"], notices)
            
            # notices to send
            logger.debug("===== %s ===== sending notices %s from %s to %s",
                         Service_Name, notices, fromtime, endtime)
            
            # render notice mail and send
            if notices:
                scene_data = get_body_data(notices)
                context = dict(scenes=scene_data,
                               fromtime=get_alarm_interval_str(fromtime),
                               endtime=get_alarm_interval_str(endtime))
                result = render(template_fn, context)
                send_mail(result)
                return
            logger.info("===== %s ===== There is No notices to send warning mail from %s to %s", Service_Name, fromtime, endtime)
    except Exception:
        logger.error("===== %s ===== Unknown Exception !!", Service_Name)
        logger.error(traceback.format_exc())
