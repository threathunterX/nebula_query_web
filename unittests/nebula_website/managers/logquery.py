# -*- coding: utf-8 -*-
import traceback
import logging

import gevent

from threathunter_common.event import Event
from threathunter_common.util import millis_now

from nebula_website import babel, settings
from nebula_website.models import db, LQ_Process_Status, LQ_Success_Status, LQ_Fail_Status
from nebula_website.models import LQ_Wait_Status
from nebula_website.models import LogQuery as Model

logger = logging.getLogger("nebula.manager.logquery")

LogQueryClient = babel.getLogQueryClient()
LogQueryProgressClient = babel.getLogQueryProgressClient()

# 日志查询 job 的配置、状态 缓存
LogQuery_Status = None
# LogQuery_Status's format
"""
id:{ "id": 1,
     "status": "success",
     "progress":0.1,
     "remark": "XXX",
     "error": "",
     "event_name":"",
     "terms":"",
     "fromtime":,
     "endtime":,
     "show_cols":,
     "total":,
     "filesize":,
     "download_path":,
    },
"""


class LogQueryDao(object):
    @staticmethod
    def clear():
        db.session.query(Model).delete()
        db.session.commit()

    @staticmethod
    def get_logquery_config_count():
        return db.session.query(Model).count()

    @staticmethod
    def get_logquery_config(lq_id):
        return db.session.query(Model).filter(Model.id==lq_id).first()

    @staticmethod
    def get_logquery_configs():
        return db.session.query(Model).all()
        
    @staticmethod
    def reach_logquery_job_limit():
        global LogQuery_Status
        if not LogQuery_Status:
            LogQuery_Status = dict()
            for _ in LogQueryDao.get_logquery_configs():
                LogQuery_Status[_.id] = _.to_dict()
        process_count = 0
        for _ in LogQuery_Status.values():
            if _["status"] == LQ_Process_Status:
                process_count += 1
        if process_count >= settings.LogQuery_Jobs_Limit:
            return True
        return False

    @staticmethod
    def get_logquery_status():
        global LogQuery_Status
        if not LogQuery_Status:
            LogQuery_Status = dict()
            for _ in LogQueryDao.get_logquery_configs():
                LogQuery_Status[_.id] = _.to_dict()
        return LogQuery_Status
        
    @staticmethod
    def set_logquery_status(lq_status):
        global LogQuery_Status
        if not LogQuery_Status:
            LogQuery_Status = dict()
            for _ in LogQueryDao.get_logquery_configs():
                LogQuery_Status[_.id] = _.to_dict()
        LogQuery_Status[lq_status["id"]] = lq_status
        
    @staticmethod
    def delete_logquery_status(lq_id):
        global LogQuery_Status
        if not LogQuery_Status:
            LogQuery_Status = dict()
            for _ in LogQueryDao.get_logquery_configs():
                LogQuery_Status[_.id] = _.to_dict()
        try:
            LogQuery_Status.pop(lq_id)
        except Exception:
            logger.error("Exception when delete memory: %s", traceback.format_exc() )

    @staticmethod
    def delete(lq_id):
        lq = LogQueryDao.get_logquery_config(lq_id)
        if lq:
            db.session.delete(lq)
            db.session.commit()
            return True, None
        return False, "No such logquery config id is: %s" % lq_id

    @staticmethod
    def add(fromtime, endtime, terms, show_cols, event_name, remark):
        try:
            lq = Model.from_dict(dict(fromtime=fromtime, endtime=endtime, terms=terms,
                                      show_cols=show_cols, remark=remark,
                                      event_name=event_name, status=LQ_Wait_Status))
        except Exception:
            return False, "invalid args to init LogQuery config instance.: %s" % traceback.format_exc()
        try:
            db.session.add(lq)
            db.session.commit()
            return True, lq.to_dict()
        except Exception:
            return False, "LogQuery config instance (%s)can't store: %s" % (lq.to_dict(),
            traceback.format_exc())
        
    @staticmethod
    def update_logquery_config(lq=None, lq_id=None, status=None, download_path=None, error=None):
        if not lq and not lq_id:
            return False, "Not specify logquery config."
        if not lq:
            lq = LogQueryDao.get_logquery_config(lq_id)
        if lq:
            if status and lq.status != status:
                lq.status = status
            if download_path and lq.download_path != download_path:
                lq.download_path = download_path
            if error:
                lq.error = error
            db.session.add(lq)
            db.session.commit()
            return True, ""
        return False, "No such logquery config id is: %s" % lq_id
        

def send_event(event, client, bn):
    logger.debug("%s Input event: %s", bn, event)
    try:
        success, res = client.send(event, '', True, 5)
    except Exception:
        msg = "Exception During %s Babel Request: %s", bn, traceback.format_exc()
        logger.error(msg)
        return False, msg

    # babel request fail
    if not success:
        msg = u"%s Babel request fail, event: %s" % (bn, event)
        logger.error(msg)
        return False, msg

    # bad request
    _ = res.property_values if res else None
    if _:
        if _.get("success"):
            return True, _
        else:
            msg = u"Bad %s response event: %s, msg:%s " % (\
                     bn, event, _.get("errmsg"))
            logger.error(msg)
            return False,msg
    return False, "%s Babel event's property_values is blank." % bn
    
def add_logquery_job(lq_id, fromtime, endtime, terms, \
                 show_cols, event_name, remark):
    # add logquery job via babel
    bn = "Logquery Create"
    prop = dict(
        id = lq_id,
        action_type = "create",
        show_cols = show_cols,
        fromtime = fromtime,
        endtime = endtime,
        name = event_name,
        terms = terms,
    )
    event = Event("__all__", "logquery", "", millis_now(), prop)
    return send_event(event, LogQueryClient, bn)
    
def delete_logquery_job(lq_id):
    # del logquery job via babel
    bn = "Logquery Delete"
    prop = dict(
        id = lq_id,
        action_type = "delete"
    )
    event = Event("__all__", "logquery", "", millis_now(), prop)
    return send_event(event, LogQueryClient, bn)
    
def fetch_logquery_data(lq_id, page, page_count):
    # fetch success logquery job's data via babel
    bn = "Logquery fetch"
    prop = dict(
        id = lq_id,
        action_type = "fetch",
        page = page,
        page_count = page_count
    )
    event = Event("__all__", "logquery", "", millis_now(), prop)
    return send_event(event, LogQueryClient, bn)

class LogQueryServer(object):
    def __init__(self, app):
        self.app = app
        self.server = babel.getLogQueryProgressServer()
        self.bg_task = None
        self.wait_times = dict()
        self.wait_limit = 5
    def start(self):
        self.server.start(func=self.process_notify)
#        self.bg_task = gevent.spawn(self.check_logquery_progress)
    def check_logquery_wait_times(self, lq):
        times = self.wait_times.get(lq["id"], 0)
        if times >= self.wait_limit:
            lq["status"]= "failed"
            lq["error"] = "任务等待超过 %s 次, 任务失败." % (self.wait_limit)
            with self.app.app_context():
                LogQueryDao.update_logquery_config(lq_id=lq["id"], error=lq["error"],
                                                   status=LQ_Fail_Status)
        self.wait_times[lq["id"]] = times + 1
    def process_notify(self, event):
#        logger.debug("get logquery progress notify once: %s", event)
#        logger.debug("LogQuery_Status: %s", LogQuery_Status)
        if LogQuery_Status and any(_['status'] in (LQ_Process_Status, LQ_Wait_Status, LQ_Success_Status)
                                   for _ in LogQuery_Status.values()):
            d = event.property_values if event else None
            if (not d) or (not d["success"]):
                logger.error("Notify unsuccess or blank event property_values: %s", d)
                return
            logger.debug("event property_values is: %s", d)
            notified_ids = set()
            # not in d["data"]
            for new in d["data"]:
                notified_ids.add(new["id"])
                old = LogQuery_Status.get(new["id"])
                if not old:
                    continue
                if old["status"] == LQ_Wait_Status and \
                   new["status"] == LQ_Process_Status:
                    logger.debug("logquery notify wait -> process")
                    old["status"]= new["status"]
                    old["progress"] = new["progress"]
                    with self.app.app_context():
                        LogQueryDao.update_logquery_config(lq_id=new["id"],
                                                           status=new["status"])
                elif old["status"] == LQ_Process_Status and \
                     new["status"] == LQ_Process_Status:
                    logger.debug("logquery notify still process..")
                    old["progress"] = new["progress"]
                elif old["status"] == LQ_Wait_Status and \
                     new["status"] == LQ_Wait_Status:
                    logger.debug("logquery notify still wait...")
                    # check times to wait
                    self.check_logquery_wait_times(old)
                elif new["status"] == LQ_Success_Status and \
                     old["status"] != LQ_Success_Status:
                    logger.debug("logquery notify success")
                    old["status"]= new["status"]
                    old["download_path"]= new["download_path"]
                    old["filesize"]= new["filesize"]
                    old["total"]= new["total"]
                    with self.app.app_context():
                        LogQueryDao.update_logquery_config(lq_id=new["id"],
                                                           status=LQ_Success_Status,
                                                           download_path=new["download_path"])
                elif new["status"] == LQ_Success_Status and \
                     old["status"] == LQ_Success_Status and not old.get("filesize"):
                    logger.debug("logquery notify after reload fix infos.")
                    old["filesize"]= new["filesize"]
                    old["total"]= new["total"]
                elif new["status"] == LQ_Fail_Status and \
                     old["status"] != LQ_Fail_Status:
                    logger.debug("logquery notify failed")
                    old["status"]= new["status"]
                    old["error"]= new["error"]
                    with self.app.app_context():
                        LogQueryDao.update_logquery_config(lq_id=new["id"],
                                                           status=LQ_Fail_Status)
                else:
                    logger.warn("Unknown Logquery Status transfer from %s to %s" % (
                        old["status"], new["status"]
                    ))
            for k,v in LogQuery_Status.iteritems():
                if k not in notified_ids:
                    self.check_logquery_wait_times(v)
#            logger.debug("Logquery Status after progress notify: %s", LogQueryDao.get_logquery_status())

def fetch_logquery_progress():
    # cronjob to fetch logquery jobs' status
    bn = "Logquery progress"
    event = Event("__all__", "logquery", "", millis_now(), {})
    return send_event(event, LogQueryProgressClient, bn)
