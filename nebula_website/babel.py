# -*- coding: utf-8 -*-
import json

from babel_python.serviceclient_async import ServiceClient
from babel_python.servicemeta import ServiceMeta
from babel_python.serviceserver_async import ServiceServer
from threathunter_common.util import millis_now

import settings

# default mode
mode = settings.Babel_Mode
nebula_node_count = settings.Nebula_Node_Count
amqp_url = 'librabbitmq://%s:%s@%s:%s/' % (settings.Rmq_Username, settings.Rmq_Password, settings.Rmq_Host,
                                           settings.Rmq_Port)


def set_mode(m):
    if m != "redis" and m != "rabbitmq":
        raise RuntimeError("invalid babel mode")

    global mode
    mode = m


successing_timeout = 0
frozen_until = 0


# client 集中安全防护
def wrap_client(client):
    old_send = client.send

    def send(request, key, block=True, timeout=10, expire=None, least_ret=None):
        global successing_timeout, frozen_until

        now = millis_now()
        if now < frozen_until:
            print "frozen now"
            return False, None

        result = old_send(request, key, block, timeout, expire, least_ret)
        if result[0] or result[1]:
            # success
            successing_timeout = 0
            frozen_until = 0
        else:
            # timeout
            successing_timeout += 1
            if successing_timeout >= 9:
                frozen_until = now + 30 * 1000 # block 30 seconds
                successing_timeout = 0
        return result

    client.send = send
    return client


def get_client(redis_conf, rmq_conf):
    global mode

    conf = rmq_conf
    if mode == "redis":
        conf = redis_conf
    conf = json.loads(conf)

    # HACK 部分RPC service 需要改成polling
    if conf['name'] in ['keystatquery', 'clickstreamquery']:
        conf['options']['servercardinality'] = 1

    meta = ServiceMeta.from_dict(conf)

    client = ServiceClient(meta) if mode == "redis" else ServiceClient(meta, amqp_url=amqp_url, client_id="")
    client.start()
    return wrap_client(client)


def get_server(redis_conf, rmq_conf):
    conf = rmq_conf
    if mode == "redis":
        conf = redis_conf

    meta = ServiceMeta.from_json(conf)
    server = ServiceServer(meta) if mode == "redis" else ServiceServer(meta, amqp_url=amqp_url, server_id="")
    return server


def get_baseline_query_client():
    return get_client(settings.BaseLineQuery_redis,
                      settings.BaseLineQuery_rmq)


def get_incident_query_client():
    return get_client(settings.IncidentQuery_redis,
                      settings.IncidentQuery_rmq)


def get_risk_event_info_query_client():
    return get_client(settings.RiskEventInfoQuery_redis,
                      settings.RiskEventInfoQuery_rmq)


def get_key_value_client():
    return get_client(settings.KeyValueService_redis,
                      settings.KeyValueService_rmq)


def get_global_value_client():
    return get_client(settings.GlobalValueService_redis,
                      settings.GlobalValueService_rmq)


def get_top_value_client():
    return get_client(settings.TopValueService_redis,
                      settings.TopValueService_rmq)


def get_key_top_value_client():
    return get_client(settings.KeyTopValueService_redis,
                      settings.KeyTopValueService_rmq)


def get_eventquery_client():
    return get_client(settings.EventQuery_redis, settings.EventQuery_rmq)


def get_statquery_client():
    return get_client(settings.StatQuery_redis, settings.StatQuery_rmq)


def get_offline_stat_client():
    return get_client(settings.OfflineStatService_redis,
                      settings.OfflineStatService_rmq)


def get_online_detail_client():
    return get_client(settings.OnlineDetail_redis,
                      settings.OnlineDetail_rmq)


def get_realtime_query_client():
    return get_client(settings.RealtimeQueryService_redis,
                      settings.RealtimeQueryService_rmq)


def get_globalslot_query_client():
    return get_client(settings.GlobalSlotQueryService_redis,
                      settings.GlobalSlotQueryService_rmq)


def get_notice_notify_server():
    return get_server(settings.NoticeService_redis,
                      settings.NoticeService_rmq)


def get_noticelog_notify_server():
    return get_server(settings.NoticeLogService_redis,
                      settings.NoticeLogService_rmq)


def get_misclog_notify_server():
    return get_server(settings.MiscLogService_redis,
                      settings.MiscLogService_rmq)


def get_httplog_notify_server():
    return get_server(settings.HttpLogService_redis,
                      settings.HttpLogService_rmq)


def get_offline_keystat_query_client():
    return get_client(
        settings.Offline_KeyStatService_redis,
        settings.Offline_KeyStatService_rmq)


def get_offline_baseline_query_client():
    return get_client(
        settings.Offline_BaselineService_redis,
        settings.Offline_BaselineService_rmq)


def get_offline_continuous_query_client():
    return get_client(
        settings.Offline_ContinuousService_redis,
        settings.Offline_ContinuousService_rmq)


def get_licenseinfo_client():
    return get_client(settings.LicenseInfo_redis,
                      settings.LicenseInfo_rmq)


def getProfileQueryClient():
    return get_client(settings.ProfileQueryService_redis,
                      settings.ProfileQueryService_rmq)


def getProfileAccountRiskClient():
    return get_client(settings.ProfileAccountRiskService_redis,
                      settings.ProfileAccountRiskService_rmq)


def getProfileAccountPageRiskClient():
    return get_client(settings.ProfileAccountPageRiskService_redis,
                      settings.ProfileAccountPageRiskService_rmq)


def getProfileTopPagesClient():
    return get_client(settings.ProfileTopPagesService_redis,
                      settings.ProfileTopPagesService_rmq)


def getProfileCrawlerRiskClient():
    return get_client(settings.ProfileCrawlerRiskService_redis,
                      settings.ProfileCrawlerRiskService_rmq)


def getProfileCrawlerPageRiskClient():
    return get_client(settings.ProfileCrawlerPageRiskService_redis,
                      settings.ProfileCrawlerPageRiskService_rmq)


def getLogQueryClient():
    return get_client(settings.LogQueryService_redis,
                      settings.LogQueryService_rmq)


def getLogQueryProgressClient():
    return get_client(settings.LogQueryProgressService_redis,
                      settings.LogQueryProgressService_rmq)


def getLogQueryProgressServer():
    return get_server(settings.LogQueryProgressService_redis,
                      settings.LogQueryProgressService_rmq)


def get_online_slot_query_client():
    return get_client(
        settings.OnlineSlotVariableQuery_redis,
        settings.OnlineSlotVariableQuery_rmq)


def get_offline_merge_query_client():
    return get_client(
        settings.OfflineMergeVariableQuery_redis,
        settings.OfflineMergeVariableQuery_rmq
    )
