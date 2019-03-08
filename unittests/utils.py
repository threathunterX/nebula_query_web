# -*- coding: utf-8 -*-
import time
    
class Storage(dict):
    """
    A Storage object is like a dictionary except `obj.foo` can be used
    in addition to `obj['foo']`.

        >>> o = storage(a=1)
        >>> o.a
        1
        >>> o['a']
        1
        >>> o.a = 2
        >>> o['a']
        2
        >>> del o.a
        >>> o.a
        Traceback (most recent call last):
            ...
        AttributeError: 'a'

    """
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError, k:
            raise AttributeError, k

    def __setattr__(self, key, value):
        self[key] = value

    def __delattr__(self, key):
        try:
            del self[key]
        except KeyError, k:
            raise AttributeError, k

    def __repr__(self):
        return '<Storage ' + dict.__repr__(self) + '>'

def get_hour_start(point=None):
    """
    获取point时间戳所在的小时的开始的时间戳, 默认获取当前时间所在小时的开始时的时间戳
    """
    if point is None:
        p = time.time()
    else:
        p = point
        
    return ((int(p) / 3600) * 3600) * 1.0

def get_current_hour_interval():
    fromtime = int(get_hour_start()) * 1000
    endtime = int(time.time() * 1000)
    return fromtime, endtime

def get_last_hour_interval():
    current_hour = int(get_hour_start()) * 1000
    fromtime = current_hour - (3600 * 1000)
    endtime = current_hour - 1
    return fromtime, endtime

def get_last_two_hour_interval():
    current_hour = int(get_hour_start()) * 1000
    fromtime = current_hour - (2*3600 * 1000)
    endtime = current_hour - 1
    return fromtime, endtime
