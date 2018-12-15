#!/usr/bin/env python
# encoding:utf-8

"""
进程检测异常

异常类型
- 无此进程
- Zombie进程
- 无读取权限
- 读取超时

灵感及思路参考 psutil
reference   :   https://github.com/giampaolo/psutil/blob/master/psutil/_exceptions.py
"""


class ProcessException(Exception):
    """
    进程监测异常类
    """

    def __init__(self, msg=""):
        Exception.__init__(self, msg)
        self.msg = msg


class NoSuchProcess(ProcessException):
    """
    进程号不存在
    """

    def __init__(self, pid, process_name=None, msg=None):
        ProcessException.__init__(self, msg)
        self.pid = pid
        self.process_name = process_name
        self.msg = msg
        if not msg:
            if process_name:
                details = " (pid={}, process_name={})".format(self.pid, self.process_name)
            else:
                details = " (pid={})".format(self.pid)
            self.msg = "process no longer exists " + details


class ZombieProcess(ProcessException):
    """
    僵尸进程

    Exception raised when querying a zombie process. This is
    raised on macOS, BSD and Solaris only, and not always: depending
    on the query the OS may be able to succeed anyway.
    On Linux all zombie processes are querable (hence this is never
    raised). Windows doesn't have zombie processes.
    """

    def __init__(self, pid, process_name=None, ppid=None, msg=None):
        ProcessException.__init__(self, msg)
        self.pid = pid
        self.ppid = ppid
        self.process_name = process_name
        self.msg = msg
        if not msg:
            details = " (pid={}".format(self.pid)
            if process_name:
                details += ", process_name=%s".format(self.process_name)
            if ppid:
                details += ", ppid=%s".format(self.ppid)
            details += ")"
            self.msg = "process still exists but it's a zombie " + details


class AccessDenied(ProcessException):
    """拒绝访问"""

    def __init__(self, pid=None, process_name=None, msg=None):
        ProcessException.__init__(self, msg)
        self.pid = pid
        self.process_name = process_name
        self.msg = msg
        details = ""
        if self.pid:
            details += " pid={}".format(self.pid)
        if self.process_name:
            details += " name={}".format(self.process_name)
        elif self.msg:
            details += self.msg
        self.msg = "Access Denied - " + self.msg
