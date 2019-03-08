# -*- coding: utf-8 -*-

from flask_sqlalchemy import SQLAlchemy
import simplejson as json

from threathunter_common.util import millis_now

__all__ = ["db", "Notice", "Notice_Stat", "Incident", "LogQuery"]

db = SQLAlchemy()
BaseModel = db.Model
Column = db.Column
Integer = db.Integer
BigInteger = db.BigInteger
CHAR = db.CHAR
VARCHAR = db.VARCHAR
String = db.String
BLOB = db.BLOB
Enum = db.Enum

LQ_Process_Status = "process"
LQ_Wait_Status = "wait"
LQ_Success_Status = "success"
LQ_Fail_Status = "failed"
# below is same as dbwriter/model.py

class LogQuery(BaseModel):
    __bind_key__ = "nebula"
    __tablename__ = 'logquery'

    id = Column(Integer, primary_key=True)
    fromtime = Column(Integer)
    endtime = Column(Integer)
    status = Column(Enum(LQ_Wait_Status,LQ_Process_Status, LQ_Success_Status, LQ_Fail_Status))
    remark = Column(VARCHAR(300))
    error = Column(VARCHAR(200))
    event_name = Column(VARCHAR(100))
    download_path = Column(CHAR(100))
    create_time = Column(Integer)
    terms = Column(VARCHAR(2000))
    show_cols = Column(VARCHAR(2000))

    @staticmethod
    def from_dict(obj):
        return LogQuery(
            fromtime=obj['fromtime'],
            endtime=obj['endtime'],
            status=obj["status"],
            event_name=obj["event_name"],
            remark=obj.get("remark"),
            error=obj.get("error"),
            terms=json.dumps(obj['terms']),
            show_cols=','.join(obj['show_cols']),
            download_path=obj.get('download_path', ''),
            create_time=millis_now()
        )

    def to_dict(self):
        return dict(
            id=self.id,
            fromtime=self.fromtime,
            endtime=self.endtime,
            terms=json.loads(self.terms),
            status=self.status,
            event_name=self.event_name,
            remark=self.remark,
            error=self.error,
            show_cols=self.show_cols.split(','),
            download_path=self.download_path
        )

class Notice(BaseModel):
    __tablename__ = 'notice'

    id = Column(Integer, primary_key=True)
    timestamp = Column(BigInteger, index=True)
    key = Column(VARCHAR(512), index=True)
    strategy_name = Column(CHAR(100))
    scene_name = Column(CHAR(100))
    checkpoints = Column(CHAR(100))
    check_type = Column(CHAR(100))
    decision = Column(CHAR(100))
    risk_score = Column(Integer)
    expire = Column(Integer)
    remark = Column(VARCHAR(1000))
    last_modified = Column(BigInteger)
    variable_values = Column(BLOB)
    geo_province = Column(CHAR(100))
    geo_city = Column(CHAR(100))
    test = Column(Integer)
    tip = Column(String(1024))
    uri_stem = Column(String(1024))

class Notice_Stat(BaseModel):
    __tablename__ = "notice_stat"
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(BigInteger, index=True)
    key = Column(VARCHAR(512), index=True)
    check_type = Column(CHAR(100))
    strategy_name = Column(CHAR(100))
    scene_name = Column(CHAR(100))
    decision = Column(CHAR(100))
    test = Column(Integer)
    tag = Column(CHAR(100))
    geo_city = Column(CHAR(100))
    uri_stem = Column(String(1024))
    ip = Column(CHAR(20))
    uid = Column(VARCHAR(512))
    did = Column(VARCHAR(512))
    count = Column(Integer)
    last_modified = Column(BigInteger)
    
class Incident(BaseModel):
    __tablename__ = "risk_incident"
    
    id = Column(Integer, primary_key=True)
    ip = Column(CHAR(20), nullable=False)
    start_time = Column(BigInteger, nullable=False)
    strategies = Column(VARCHAR(1000), nullable=False)
    hit_tags = Column(VARCHAR(1000), nullable=False)
    risk_score = Column(Integer, nullable=False)
    uri_stems = Column(VARCHAR(2000), nullable=False)
    hosts = Column(VARCHAR(1000), nullable=False)
    most_visited = Column(VARCHAR(1000))
    peak = Column(CHAR(20))
    dids = Column(BLOB, nullable=False)
    associated_users = Column(BLOB, nullable=False)
    associated_orders = Column(VARCHAR(1000))
    users_count = Column(Integer)
    status = Column(Integer, default=0)
    last_modified = Column(BigInteger)