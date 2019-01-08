#!/usr/bin/env python
# encoding:utf-8

"""
进程监测核心功能实现 - 进程管理

主要包括
- 获取所有进程名
- 按进程名称搜索进程
- 关闭进程
- 关闭进程(连同相关进程)
- 获取同组进程
- 获取所有子进程
- 获取进程执行文件地址
- 后台创建一个新的进程(不随主进程退出,返回创建的进程号)
- 重启进程

"""

from process_monitor import get_all_pid, get_process_info
from prcess_exception import wrap_process_exceptions, NoSuchProcess, ZombieProcess, AccessDenied

import os
import signal
import subprocess


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


def kill_process(pid):
    """关闭进程"""
    try:
        if get_process_info(pid)['state'] == 'Z':  # zombie process
            raise ZombieProcess(pid)
        os.kill(int(pid), signal.SIGKILL)
    except OSError as e:
        if e.args[0] == 1:  # Operation not permitted
            raise AccessDenied(pid)
        if e.args[0] == 3:  # No such process
            raise NoSuchProcess(pid)


def kill_all_process(pid, kill_child=True, kill_process_gourp=True):
    """关闭进程 (pid所指进程, 该进程的子进程, 该进程的同组进程)"""
    # 获取需要关闭的进程
    self_pid = os.getpid()
    need_killed_process = [pid]
    if kill_child:
        need_killed_process.extend(get_all_child_process(pid))
    if kill_process_gourp and get_process_group_id(pid) != get_process_group_id(self_pid):
        need_killed_process.extend(get_same_group_process(get_process_group_id(pid)))
    need_killed_process = sorted(list(set(need_killed_process)), reverse=True)
    # 去掉监控进程本身 (因为启动进程会将启动的进程变成监控进程的子进程,这地方逻辑不是很清晰 todo:更好的进程关闭方式? )
    if self_pid in need_killed_process:
        need_killed_process.remove(self_pid)
    # 逐一关闭
    try:
        for p in need_killed_process:
            kill_process(p)
    except NoSuchProcess as e:
        pass

    return True


def get_process_parent_pid(pid):
    """获取进程父进程id - ppid"""
    return get_process_info(pid)['ppid']


def get_process_group_id(pid):
    """获取进程组id - pgrp"""
    return get_process_info(pid)['pgrp']


def get_same_group_process(pid):
    """获取同组进程"""
    result = []
    pgrp = get_process_group_id(pid)

    for p in get_all_pid():
        if pgrp == get_process_group_id(p):
            result.append(p)
    # 一般最小的pid为组id和整个进程的父pid
    return sorted(result, reverse=False)


def get_all_child_process(pid):
    """获取所有子进程"""
    result = []

    for p in get_all_pid():
        if pid == get_process_parent_pid(p):
            result.append(p)

    return sorted(result, reverse=False)


@wrap_process_exceptions
def get_process_execute_path(pid):
    """获取进程执行文件地址 - /proc/[pid]/cwd"""

    """
    /proc/[pid]/cwd
        
        This is a symbolic link to the current working directory of the process.  
        To find out the current working directory of process 20, for instance, you can do this:
            
            $ cd /proc/20/cwd; /bin/pwd

        Note that the pwd command is often a shell built-in, and might not work properly.  
        In bash(1), you may use pwd -P.
        In a multithreaded process, the contents of this symbolic link are not available if the main thread
         has already terminated (typically by calling pthread_exit(3)).

        Permission to dereference or read (readlink(2)) this symbolic link is governed by a 
        ptrace access mode PTRACE_MODE_READ_FSCREDS check; see ptrace(2).
    """

    cwd_path = "/proc/{}/cwd".format(pid)
    return os.readlink(cwd_path)


def start_process(execute_file_full_path):
    """后台创建一个新的进程(不随主进程退出,返回创建的进程号)"""
    # reference : https://stackoverflow.com/questions/1605520/how-to-launch-and-run-external-script-in-background
    # reference : https://www.cnblogs.com/zhoug2020/p/5079407.html
    # reference : https://stackoverflow.com/questions/89228/calling-an-external-command-in-python/92395#92395
    # reference : https://stackoverflow.com/questions/1196074/how-to-start-a-background-process-in-python

    # 获取执行文件相关地址
    cwd = execute_file_full_path[:execute_file_full_path.rindex("/")]
    execute_file = execute_file_full_path[execute_file_full_path.rindex("/") + 1:]
    # 启动进程
    if execute_file.endswith('.py'):  # python
        p = subprocess.Popen(["nohup", "python", execute_file_full_path],
                             cwd=cwd,
                             close_fds=True,
                             stderr=subprocess.STDOUT)
        return p.pid
    # todo : support more execute file
    else:
        return False


def restart_process(pid, execute_file_full_path):
    """重启进程"""
    # 关闭
    kill_all_process(pid)
    # 启动
    return start_process(execute_file_full_path)
