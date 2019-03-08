# -*- coding: utf-8 -*-
import unittest

from query_web import app

from unittests import utils

# @todo 本地如何测？ babel配置?

class IncidentTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
    def test_api_start_time(self):
        # 测试用例:
        # 1. 没有Persist_Path目录 返回制定数据
        # 2. 创建两个包涵data目录的 数据目录，确认返回是最早的数据文件夹
        # mock 一个临时文件夹
        rv = self.app.get('/platform/behavior/start_time')
        print rv.data
        print type(rv)

    def test_api_related_stat(self):
        # 测试用例：
        # 1. 当前小时
        # 2. 历史小时
        # 4. 参数检查
        # 3. 各个页面的使用场景 page 维度 | 其他
        # 检查返回格式
        # 需要mock
        url_prefix = '/platform/behavior/related_statistics'
        
        # 当前小时 user 维度 关联did数,ip 
        key_type = "user"
        from_time, end_time = utils.get_current_hour_interval()
        related_key_types = "did,ip"
        url = "%s?key_type=%s&fromtime=%s&endtime=%s&related_key_types=%s" % (url_prefix, key_type, from_time, end_time, related_key_types)
        rv = self.app.get(url)
        print rv.data
        
    def test_api_continuous_top_related(self):
        url_prefix = '/platform/behavior/continuous_top_related_statistic'
        # 只是输入、返回格式、mock metrics
        # 还要提出来格式化的函数
        
    def test_api_page_stat(self):
        # 只是输入、返回格式、mock babel
        # 还要提出来格式化的函数
        url_prefix = "/platform/behavior/page_statistics"
        
    def test_api_visit_stream(self):
        url_prefix = "/platform/behavior/visit_stream"
        # 只是输入、返回格式、mock babel

    def test_api_clicks_period(self):
        # 只是输入、返回格式、mock babel
        url_prefix = "/platform/behavior/clicks_period"
        
    def test_api_clicks(self):
        # 集成测试保证条数、往下没有异常?
        # 只是输入、返回格式、mock babel
        url_prefix = "/platform/behavior/clicks"
    def test_api_online_slot(self):
        url_prefix = "/platform/stats/slot"

        key_type="total"
        from_time, end_time= utils.get_current_hour_interval()
        var_list="total__visit__incident_count__1h__slot&var_list=total__visit__dynamic_distinct_ip__1h__slot&var_list=total__visit__dynamic_count__1h__slot"
        url = "%s?key_type=%s&fromtime=%s&endtime=%s&var_list=%s" % (url_prefix, key_type, from_time, end_time, var_list)
        rv = self.app.get(url)
        print rv.data

    def test_api_online_realtime(self):
        url_prefix = "/platform/stats/online"
        
        # 首页总览
        key_type = "total"
        from_time, end_time = 1488463200000,1496413177281
        var_list='total__visit__dynamic_count__1h__slot'
        url = "%s?key_type=%s&fromtime=%s&endtime=%s&var_list=%s" % (url_prefix, key_type, from_time, end_time, var_list)
        rv = self.app.get(url)
        print rv.data

    def tearDown(self):
        pass

if __name__ == '__main__':
    unittest.main()
        