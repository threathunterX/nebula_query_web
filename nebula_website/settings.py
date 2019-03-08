# -*- coding: utf-8 -*-
from os import path as _opath

from complexconfig.config import Config as _Config
from complexconfig.config import EmptyConfig as _EmptyConfig
from complexconfig.parser.properties_parser import PropertiesParser as _PropertiesParser
from complexconfig.loader.file_loader import FileLoader as _FileLoader
from complexconfig.configcontainer import configcontainer as _cc

"""
for _ in dir(settings):
    if not _.startswith("_"):
         print _, " : ", getattr(settings, _)
"""

# =============== Fundamental Settings ===============
_global_config_fn = "/etc/nebula/nebula.conf"
_web_config_fn = "/etc/nebula/web"
_babel_config_fn = '/etc/nebula/babels'

_basedir = _opath.abspath(_opath.dirname(__file__))

config_scope = "local"
global_config = None

if _opath.exists(_global_config_fn):
    _loader = _FileLoader("loader", _global_config_fn)
    _parser = _PropertiesParser("parser")
    global_config = _Config(_loader, _parser)
    global_config.load_config(sync=True)
    config_scope = "global"
    
if config_scope == "local":
    global_config = _EmptyConfig()
    _web_config_fn = _opath.join(_basedir, "localconfig")
    

_cc.set_config("nebula", global_config)
_config = _cc.get_config("nebula")

# =================== Loadding Settings ===================
DEBUG = False
CACHE_TYPE = 'simple'

Auth_Code = "196ca0c6b74ad61597e3357261e80caf"

WebUI_Address = _config.get_string("webui_address", '0.0.0.0')
WebUI_Port = _config.get_int("webui_port", 9001)

Notice_RPC_Template_Path = _config.get_string(
    "notice_rpc_template_path", "conf")

Redis_Host = _config.get_string('redis_host', "127.0.0.1")
Redis_Port = _config.get_int('redis_port', 6379)

Influxdb_Url = _config.get_string('influxdb_url',"http://127.0.0.1:8086/")
Babel_Mode = _config.get_string('babel_server', "redis")
Persist_Path = _config.get_string('persist_path', "./")
LogQuery_Jobs_Limit = _config.get_int("persist_job_limit", 2)

Nebula_Node_Count = _config.get_int("nebula_node_count", 1)

Rmq_Username = _config.get_string('rmq_username', 'guest')
Rmq_Password = _config.get_string('rmq_password', 'guest')
Rmq_Host = _config.get_string('rmq_host', "127.0.0.1")
Rmq_Port = _config.get_int('rmq_port', 5672)

# 当前小时计算模块是否启用，不启用的话，就省去查询相关接口的开销
Enable_Online = _config.get_boolean("nebula.online.slot.enable", True)

MySQL_Host = _config.get_string("mysql_host", "127.0.0.1")
MySQL_Port = _config.get_int("mysql_port", 3306)
MySQL_User = _config.get_string("mysql_user", 'root')
MySQL_Passwd = _config.get_string("mysql_passwd", "passwd")
Nebula_Data_DB = _config.get_string("nebula_data_db", "nebula_data")
Nebula_DB = _config.get_string("nebula_db", "nebula")

SQLALCHEMY_DATABASE_URI = "mysql://%s:%s@%s:%s/%s" % (MySQL_User, MySQL_Passwd, MySQL_Host,
                                                      MySQL_Port, Nebula_Data_DB)
SQLALCHEMY_BINDS = {
    "nebula": "mysql://%s:%s@%s:%s/%s" % (MySQL_User, MySQL_Passwd, MySQL_Host,
                                                      MySQL_Port, Nebula_DB)
}
# Metrics configs
Metrics_Server = _config.get_string('metrics_server', "redis")
metrics_dict = {
    "app": "nebula_query_web",
    "redis": {
        "type": "redis",
        "host": Redis_Host,
        "port": Redis_Port
    },
    "influxdb": {
    "type": "influxdb",
    "url": Influxdb_Url,
    "username": "test",
    "password": "test"
    },
    "server": Metrics_Server
}


# =============== Babel settings ===============

_Babel_Setting_Fns = [
    "BaseLineQuery_redis.service", "BaseLineQuery_rmq.service",
    "IncidentQuery_redis.service", "IncidentQuery_rmq.service",
    "RiskEventInfoQuery_redis.service", "RiskEventInfoQuery_rmq.service",
    "LicenseInfo_redis.service", "LicenseInfo_rmq.service",
    "KeyValueService_redis.service", "KeyValueService_rmq.service",
    "StatQuery_redis.service", "StatQuery_rmq.service",
    "EventQuery_redis.service", "EventQuery_rmq.service",
    "GlobalValueService_redis.service", "GlobalValueService_rmq.service",
    "TopValueService_redis.service", "TopValueService_rmq.service",
    "KeyTopValueService_redis.service", "KeyTopValueService_rmq.service",
    "NoticeService_redis.service", "NoticeService_rmq.service",
    "NoticeLogService_redis.service", "NoticeLogService_rmq.service",
    "MiscLogService_redis.service", "MiscLogService_rmq.service",
    "HttpLogService_redis.service", "HttpLogService_rmq.service",
    "OfflineStatService_redis.service", "OfflineStatService_rmq.service",
    "OnlineDetail_redis.service", "OnlineDetail_rmq.service",
    "ProfileQueryService_redis.service", "ProfileQueryService_rmq.service",
    "RealtimeQueryService_redis.service", "RealtimeQueryService_rmq.service",
    "Offline_BaselineService_redis.service", "Offline_BaselineService_rmq.service",
    "Offline_KeyStatService_redis.service", "Offline_KeyStatService_rmq.service",
    "Offline_ContinuousService_redis.service", "Offline_ContinuousService_rmq.service",
    "GlobalSlotQueryService_redis.service", "GlobalSlotQueryService_rmq.service",
    "ProfileAccountRiskService_redis.service", "ProfileAccountRiskService_rmq.service",
    "ProfileAccountPageRiskService_redis.service",
    "ProfileAccountPageRiskService_rmq.service",
    "ProfileTopPagesService_redis.service","ProfileTopPagesService_rmq.service",
    "ProfileCrawlerRiskService_redis.service","ProfileCrawlerRiskService_rmq.service",
    "ProfileCrawlerPageRiskService_redis.service",
    "ProfileCrawlerPageRiskService_rmq.service",
    "LogQueryService_redis.service", "LogQueryService_rmq.service",
    "LogQueryProgressService_redis.service", "LogQueryProgressService_rmq.service",
    "OnlineSlotVariableQuery_redis.service", "OnlineSlotVariableQuery_rmq.service",
    "OfflineMergeVariableQuery_redis.service", "OfflineMergeVariableQuery_rmq.service",
]

try:
    fp = None
    for fn in _Babel_Setting_Fns:
        fp = _opath.join(_babel_config_fn, fn)
        if not _opath.exists(fp):
            fp = _opath.join(_web_config_fn, fn)
        with open(fp, 'r') as f:
            globals()[ fn.split(".")[0] ] = ''.join(f.readlines())
except IOError:
    print "pwd: %s" % _basedir
    print "!!!! Babel配置 %s 缺失，无法启动" % fp
    import sys
    sys.exit(-1)

