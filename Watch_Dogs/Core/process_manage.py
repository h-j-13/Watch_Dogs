#!/usr/bin/env python
# encoding:utf-8

"""
进程监测核心功能实现 - 进程管理

主要包括
- 获取所有进程名
- 按进程名称搜索进程
-


"""

from process_monitor import get_all_pid, get_process_info
from prcess_exception import wrap_process_exceptions


def get_all_pid_name(name_type="cmdline"):
    """获取所有进程名"""
    res = {}
    # 按照命令ps -ef的逻辑,以 cmdline 作为进程名称,当然也可以选择 comm 作为备选
    for pid in get_all_pid():
        process_info = get_process_info(pid)
        process_name = process_info[name_type] if get_process_info(pid)[name_type].strip() else process_info['comm']
        res[pid] = process_name

    return res


def search_pid_by_keyword(keyword, search_type='contain'):
    """按进程名搜索进程号 (搜索类型 contain-包含关键词,match-完全匹配)"""
    res = []
    for pid, process_name in get_all_pid_name().items():
        if search_type == 'contain':
            if keyword in process_name:
                res.append((pid, process_name))
        elif search_type == 'match':
            if keyword == process_name:
                res.append((pid, process_name))

    return res



# todo
# 1. 获取同组进程
# 2. 关闭进程
# 3. 启动进程
# 4. 重启进程