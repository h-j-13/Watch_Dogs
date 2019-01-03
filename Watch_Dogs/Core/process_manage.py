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
from prcess_exception import wrap_process_exceptions, NoSuchProcess, ZombieProcess, AccessDenied

import os
import signal


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
        os.kill(pid, signal.SIGKILL)
    except OSError as e:
        if e.args[0] == 1:  # Operation not permitted
            raise AccessDenied(pid)
        if e.args[0] == 3:  # No such process
            raise NoSuchProcess(pid)


def kill_process_group(pgid):
    """关闭进程组"""
    try:
        if get_process_info(pgid)['state'] == 'Z':  # zombie process
            raise ZombieProcess(pgid)
        os.killpg(pgid, signal.SIGKILL)
    except OSError as e:
        if e.args[0] == 1:  # Operation not permitted
            raise AccessDenied(pgid)
        if e.args[0] == 3:  # No such process
            raise NoSuchProcess(pgid)

# todo 获取同组进程

def statr_process(cmd):
    # todo 完成他
    """创建一个新的进程(不随主进程退出,返回创建的进程好)"""
    # reference : https://stackoverflow.com/questions/89228/calling-an-external-command-in-python/92395#92395
    # reference : https://stackoverflow.com/questions/1196074/how-to-start-a-background-process-in-python

    # from subprocess import call
    # call(["python", "/home/houjie/Watch_Dogs/Watch_Dogs/Test/test.py"])

    import subprocess
    pid = subprocess.Popen(['python', "/home/houjie/Watch_Dogs/Watch_Dogs/Test/test.py"],
                           close_fds=True)  # call subprocess
    return pid.pid
    # import os
    # return os.spawnl(os.P_NOWAITO, 'python /home/houjie/Watch_Dogs/Watch_Dogs/Test/test.py &')

    import subprocess
    # pid = os.fork()
    #
    # if pid == 0:
    #     os.execv("/usr/bin/ls", ['/home/houjie/Watch_Dogs/Watch_Dogs/Test/test.py'])
    # # os.system('python /home/houjie/Watch_Dogs/Watch_Dogs/Test/test.py &')
    # os.spawnl(os.P_DETACH, 'python /home/houjie/Watch_Dogs/Watch_Dogs/Test/test.py')
    # p = subprocess.Popen("python /home/houjie/Watch_Dogs/Watch_Dogs/Test/test.py",
    #                      stdin=subprocess.PIPE,
    #                      stdout=subprocess.PIPE,
    #                      stderr=subprocess.PIPE,)
    #                      # close_fds=True)
    # print p.pid
    raw_input(1)



if __name__ == '__main__':
    print statr_process(12637)
