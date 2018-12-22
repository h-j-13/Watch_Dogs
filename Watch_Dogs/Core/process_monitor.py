#!/usr/bin/env python
# encoding:utf-8

"""
进程检测核心功能实现 - 进程检测

主要包括
- 获取所有进程号
- 获取进程基本信息
- 获取进程CPU占用率
- 获取路径文件夹总大小
- 获取路径可用大小
- 获取进程内存
- 获取进程磁盘占用(需要root权限)
- 获取进程网络监控?

reference   :   https://www.jianshu.com/p/deb0ed35c1c2
reference   :   https://www.kernel.org/doc/Documentation/filesystems/proc.txt
"""

import os
from copy import deepcopy
from time import time, sleep, localtime, strftime

from prcess_exception import wrap_process_exceptions, AccessDenied, NoSuchProcess, ZombieProcess
from sys_monitor import get_total_cpu_time

calc_func_interval = 2
# 用于存放所有进程信息的数据结构

all_process_info_dict = {}
all_process_info_dict["pid"] = set()  # 关注的进程pid
all_process_info_dict["process_info"] = {}  # 关注进程的相关信息
all_process_info_dict["prev_cpu_total_time"] = 0  # 上次记录的总CPU时间片

# 标准进程相关信息数据结构
process_info_dict = {}
process_info_dict["pre_time"] = 0  # 时间片(用于计算各种占用率 - 注意,这里是整个进程公用的)
process_info_dict["prev_cpu_time"] = None
process_info_dict["prev_io"] = None

# 系统内核数据
MEM_PAGE_SIZE = 4  # KB


@wrap_process_exceptions
def get_all_pid():
    """获取所有进程号"""

    def isDigit(x):
        """判断一个字符串是否为正整数"""
        try:
            x = int(x)
            return isinstance(x, int)
        except ValueError:
            return False

    return filter(isDigit, os.listdir("/proc"))


@wrap_process_exceptions
def get_process_info(pid):
    """获取进程信息 - /proc/[pid]/stat"""
    with open("/proc/{}/stat".format(pid), "r") as p_stat:
        p_data = p_stat.readline()

    p_data = p_data.split(' ')
    return {
        "pid": int(p_data[0]),
        "comm": p_data[1].strip(')').strip('('),
        "state": p_data[2],
        "ppid": int(p_data[3]),
        "pgrp": int(p_data[4])
    }


@wrap_process_exceptions
def get_process_cpu_time(pid):
    """获取进程cpu时间片 - /proc/[pid]/stat"""

    """
    /proc/[pid]/stat
    Status information about the process.  This is used by ps(1).  
    It is defined in the kernel source file fs/proc/array.c.

    The   fields,   in   order,   with  their  proper  scanf(3)  format  specifiers,  are  listed  below.  
    Whether  or  not  certain  of  these  fields  display  valid  information  is  governed  by  a  ptrace  access  mode
    PTRACE_MODE_READ_FSCREDS | PTRACE_MODE_NOAUDIT check (refer to ptrace(2)).  
    If the check denies access, then the field value is displayed as 0.  
    The affected fields are indicated with the marking [PT].

    (1) pid  %d
        The process ID.

    (2) comm  %s
        The filename of the executable, in parentheses.  This is visible whether or not the executable is swapped out.

    (3) state  %c
        One of the following characters, indicating process state:

        R  Running
        S  Sleeping in an interruptible wait
        D  Waiting in uninterruptible disk sleep
        Z  Zombie
        T  Stopped (on a signal) or (before Linux 2.6.33) trace stopped
        t  Tracing stop (Linux 2.6.33 onward)
        W  Paging (only before Linux 2.6.0)
        X  Dead (from Linux 2.6.0 onward)
        x  Dead (Linux 2.6.33 to 3.13 only)
        K  Wakekill (Linux 2.6.33 to 3.13 only)
        W  Waking (Linux 2.6.33 to 3.13 only)
        P  Parked (Linux 3.9 to 3.13 only)

    (4) ppid  %d
        The PID of the parent of this process.

    (5) pgrp  %d
        The process group ID of the process.

    (6) session  %d
        The session ID of the process.

    (7) tty_nr  %d
        The controlling terminal of the process.  
        (The minor device number is contained in the combination of bits 31 to 20 and 7 to 0; 
        the major device number is in bits 15 to 8.)

    (8) tpgid  %d
        The ID of the foreground process group of the controlling terminal of the process.

    (9) flags  %u
        The kernel flags word of the process.  
        For bit meanings, see the PF_* defines in the Linux kernel source file include/linux/sched.h.  
        Details depend on the kernel version.
        The format for this field was %lu before Linux 2.6.

    (10) minflt  %lu
        The number of minor faults the process has made which have not required loading a memory page from disk.

    (11) cminflt  %lu
        The number of minor faults that the process's waited-for children have made.

    (12) majflt  %lu
        The number of major faults the process has made which have required loading a memory page from disk.

    (13) cmajflt  %lu
        The number of major faults that the process's waited-for children have made.

    (14) utime  %lu
        Amount of time that this process has been scheduled in user mode, measured in clock ticks 
        (divide by sysconf(_SC_CLK_TCK)).  This includes guest time, guest_time (time spent running a virtual CPU,  see  below),
        so that applications that are not aware of the guest time field do not lose that time from their calculations.

    (15) stime  %lu
        Amount of time that this process has been scheduled in kernel mode, 
        measured in clock ticks (divide by sysconf(_SC_CLK_TCK)).

    (16) cutime  %ld
        Amount  of  time  that this process's waited-for children have been scheduled in user mode,
         measured in clock ticks (divide by sysconf(_SC_CLK_TCK)).  (See also times(2).)  This includes guest time, cguest_time
        (time spent running a virtual CPU, see below).

    (17) cstime  %ld
        Amount of time that this process's waited-for children have been scheduled in kernel mode, 
        measured in clock ticks (divide by sysconf(_SC_CLK_TCK)).

    (18) priority  %ld
        (Explanation for Linux 2.6) For processes running a real-time scheduling policy (policy below; 
        see sched_setscheduler(2)), this is the negated scheduling priority, minus one; 
        that is, a number in the  range  -2
        to  -100,  corresponding  to  real-time  priorities 1 to 99.  
        For processes running under a non-real-time scheduling policy, 
        this is the raw nice value (setpriority(2)) as represented in the kernel.  The kernel
        stores nice values as numbers in the range 0 (high) to 39 (low), 
        corresponding to the user-visible nice range of -20 to 19.

        Before Linux 2.6, this was a scaled value based on the scheduler weighting given to this process.

    (19) nice  %ld
        The nice value (see setpriority(2)), a value in the range 19 (low priority) to -20 (high priority).

    (20) num_threads  %ld
        Number of threads in this process (since Linux 2.6).  Before kernel 2.6, this field was hard coded to 0 as a placeholder for an earlier removed field.

    (21) itrealvalue  %ld
        The time in jiffies before the next SIGALRM is sent to the process due to an interval timer.  Since kernel 2.6.17, this field is no longer maintained, and is hard coded as 0.

    (22) starttime  %llu
        The time the process started after system boot.  In kernels before Linux 2.6, this value was expressed in jiffies.  Since Linux 2.6, the value is expressed in clock ticks (divide by sysconf(_SC_CLK_TCK)).

        The format for this field was %lu before Linux 2.6.

    (23) vsize  %lu
        Virtual memory size in bytes.

    (24) rss  %ld
        Resident Set Size: number of pages the process has in real memory.  This is just the pages which count toward text, data, or stack space.  This does not include pages which have not been  demand-loaded  in,  or
        which are swapped out.

    (25) rsslim  %lu
        Current soft limit in bytes on the rss of the process; see the description of RLIMIT_RSS in getrlimit(2).

    (26) startcode  %lu  [PT]
        The address above which program text can run.

    (27) endcode  %lu  [PT]
        The address below which program text can run.

    (28) startstack  %lu  [PT]
        The address of the start (i.e., bottom) of the stack.

    (29) kstkesp  %lu  [PT]
        The current value of ESP (stack pointer), as found in the kernel stack page for the process.

    (30) kstkeip  %lu  [PT]
        The current EIP (instruction pointer).

    (31) signal  %lu
        The bitmap of pending signals, displayed as a decimal number.  Obsolete, because it does not provide information on real-time signals; use /proc/[pid]/status instead.

    (32) blocked  %lu
        The bitmap of blocked signals, displayed as a decimal number.  Obsolete, because it does not provide information on real-time signals; use /proc/[pid]/status instead.

    (33) sigignore  %lu
        The bitmap of ignored signals, displayed as a decimal number.  Obsolete, because it does not provide information on real-time signals; use /proc/[pid]/status instead.

    (34) sigcatch  %lu
        The bitmap of caught signals, displayed as a decimal number.  Obsolete, because it does not provide information on real-time signals; use /proc/[pid]/status instead.

    (35) wchan  %lu  [PT]
        This is the "channel" in which the process is waiting.  It is the address of a location in the kernel where the process is sleeping.  The corresponding symbolic name can be found in /proc/[pid]/wchan.

    (36) nswap  %lu
        Number of pages swapped (not maintained).

    (37) cnswap  %lu
        Cumulative nswap for child processes (not maintained).

    (38) exit_signal  %d  (since Linux 2.1.22)
        Signal to be sent to parent when we die.

    (39) processor  %d  (since Linux 2.2.8)
        CPU number last executed on.

    (40) rt_priority  %u  (since Linux 2.5.19)
        Real-time scheduling priority, a number in the range 1 to 99 for processes scheduled under a real-time policy, or 0, for non-real-time processes (see sched_setscheduler(2)).

    (41) policy  %u  (since Linux 2.5.19)
        Scheduling policy (see sched_setscheduler(2)).  Decode using the SCHED_* constants in linux/sched.h.

        The format for this field was %lu before Linux 2.6.22.

    (42) delayacct_blkio_ticks  %llu  (since Linux 2.6.18)
        Aggregated block I/O delays, measured in clock ticks (centiseconds).

    (43) guest_time  %lu  (since Linux 2.6.24)
        Guest time of the process (time spent running a virtual CPU for a guest operating system), measured in clock ticks (divide by sysconf(_SC_CLK_TCK)).

    (44) cguest_time  %ld  (since Linux 2.6.24)
        Guest time of the process's children, measured in clock ticks (divide by sysconf(_SC_CLK_TCK)).

    (45) start_data  %lu  (since Linux 3.3)  [PT]
        Address above which program initialized and uninitialized (BSS) data are placed.

    (46) end_data  %lu  (since Linux 3.3)  [PT]
        Address below which program initialized and uninitialized (BSS) data are placed.

    (47) start_brk  %lu  (since Linux 3.3)  [PT]
        Address above which program heap can be expanded with brk(2).

    (48) arg_start  %lu  (since Linux 3.5)  [PT]
        Address above which program command-line arguments (argv) are placed.

    (49) arg_end  %lu  (since Linux 3.5)  [PT]
        Address below program command-line arguments (argv) are placed.

    (50) env_start  %lu  (since Linux 3.5)  [PT]
        Address above which program environment is placed.

    (51) env_end  %lu  (since Linux 3.5)  [PT]
        Address below which program environment is placed.

    (52) exit_code  %d  (since Linux 3.5)  [PT]
        The thread's exit status in the form reported by waitpid(2).
    """

    with open("/proc/{}/stat".format(pid), "r") as p_stat:
        p_data = p_stat.readline()

    return sum(map(int, p_data.split(' ')[13:17]))  # 进程cpu时间片 = utime+stime+cutime+cstime


def calc_process_cpu_percent(pid, interval=calc_func_interval):
    """计算进程CPU使用率 (计算的cpu总体占用率)"""
    global all_process_info_dict, process_info_dict
    # 初始化 - 添加进程信息
    if int(pid) not in all_process_info_dict["pid"]:
        all_process_info_dict["pid"].add(int(pid))
        all_process_info_dict["process_info"][str(pid)] = deepcopy(process_info_dict)  # 添加一个全新的进程数据结构副本

    if all_process_info_dict["process_info"][str(pid)]["prev_cpu_time"] is None:
        all_process_info_dict["prev_cpu_total_time"] = get_total_cpu_time()[0]
        all_process_info_dict["process_info"][str(pid)]["prev_cpu_time"] = get_process_cpu_time(pid)
        sleep(interval)

    current_cpu_total_time = get_total_cpu_time()[0]
    current_process_cpu_time = get_process_cpu_time(pid)
    process_cpu_percent = (current_process_cpu_time - all_process_info_dict["process_info"][str(pid)]["prev_cpu_time"]) \
                          * 100.0 / (current_cpu_total_time - all_process_info_dict["prev_cpu_total_time"])

    all_process_info_dict["process_info"][str(pid)]["prev_cpu_time"] = current_process_cpu_time
    all_process_info_dict["prev_cpu_total_time"] = current_cpu_total_time

    return process_cpu_percent


@wrap_process_exceptions
def get_path_total_size(path, style='M'):
    """获取文件夹总大小(默认MB)"""
    total_size = 0
    # 通过 os.walk() 获取所有文件并计算总大小
    for dir_path, dir_names, file_names in os.walk(path):
        for fn in file_names:
            try:
                total_size += os.path.getsize(os.path.join(dir_path, fn))
            except (OSError, IOError):
                continue
    # 调整返回单位大小
    if style == 'M':
        return round(total_size / 1024. ** 2, 2)
    elif style == 'G':
        return round(total_size / 1024. ** 3, 2)
    else:  # 'KB'
        return round(total_size / 1024., 2)


@wrap_process_exceptions
def get_path_avail_size(path, style='G'):
    """获取文件夹所在路径剩余可用大小"""
    path_stat = os.statvfs(path)
    avail_size = path_stat.f_bavail * path_stat.f_frsize

    # 调整返回单位大小
    if style == 'M':
        return round(avail_size / 1024. ** 2, 2)
    elif style == 'G':
        return round(avail_size / 1024. ** 3, 2)
    else:  # 'KB'
        return round(avail_size / 1024., 2)


@wrap_process_exceptions
def get_process_mem(pid, style='M'):
    """获取进程占用内存 /proc/pid/stat"""

    """
    /proc/[pid]/stat
                  
    (23) vsize  %lu
        Virtual memory size in bytes.
    
    (24) rss  %ld
        Resident Set Size: number of pages the process has in real memory.  
        This is just the pages which count toward text, data, or stack space.  
        This does not include pages which have not been  demand-loaded  in,  or which are swapped out.
    """

    with open("/proc/{}/stat".format(pid), "r") as p_stat:
        p_data = p_stat.readline()

    global MEM_PAGE_SIZE
    # 进程实际占用内存 = rss * page size
    if style == 'M':
        return round(int(p_data.split()[23]) * MEM_PAGE_SIZE / 1024., 2)
    elif style == 'G':
        return round(int(p_data.split()[23]) * MEM_PAGE_SIZE / 1024. ** 2, 2)
    else:  # K
        return int(p_data.split()[23]) * MEM_PAGE_SIZE


@wrap_process_exceptions
def get_process_io(pid):
    """获取进程读写数据 - /proc/pid/io"""

    """
    /proc/[pid]/io (since kernel 2.6.20)
              
    This file contains I/O statistics for the process, for example:

    # cat /proc/3828/io
    rchar: 323934931
    wchar: 323929600
    syscr: 632687
    syscw: 632675
    read_bytes: 0
    write_bytes: 323932160
    cancelled_write_bytes: 0

    The fields are as follows:

    rchar:  characters read
            The number of bytes which this task has caused to be read from storage.  This is simply the sum of bytes 
            which this process passed to read(2) and similar system calls.  It includes things such as terminal I/O  and
            is unaffected by whether or not actual physical disk I/O was required 
            (the read might have been satisfied from pagecache).

    wchar: characters written
            The number of bytes which this task has caused, or shall cause to be written to disk.  
            Similar caveats apply here as with rchar.

    syscr: read syscalls
            Attempt to count the number of read I/O operations—that is, system calls such as read(2) and pread(2).

    syscw: write syscalls
            Attempt to count the number of write I/O operations—that is, system calls such as write(2) and pwrite(2).

    read_bytes: bytes read
            Attempt to count the number of bytes which this process really did cause to be fetched from the storage layer.  This is accurate for block-backed filesystems.

    write_bytes: bytes written
            Attempt to count the number of bytes which this process caused to be sent to the storage layer.

    cancelled_write_bytes:
            The  big  inaccuracy  here  is truncate.  If a process writes 1MB to a file and then deletes the file, 
            it will in fact perform no writeout.  But it will have been accounted as having caused 1MB of write.  
            In other words: this field represents the number of bytes which this process caused to not happen, 
            by truncating pagecache.  A task can cause "negative" I/O too.  
            If this task truncates some dirty pagecache, some I/O which
            another task has been accounted for (in its write_bytes) will not be happening.

    Note:  In  the  current implementation, things are a bit racy on 32-bit systems: 
            if process A reads process B's /proc/[pid]/io while process B is updating one of these 64-bit counters, 
            process A could see an intermediate result.

    Permission to access this file is governed by a ptrace access mode PTRACE_MODE_READ_FSCREDS check; see ptrace(2).
    """

    # rchar vs read_bytes
    # https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/Documentation/filesystems/proc.txt?id=HEAD#l1305
    # https://stackoverflow.com/search?q=%2F+proc+%2F+%5Bpid%5D+%2F+io
    #
    # Note 有关部分/proc无法读取所触发的 Permission denied 问题
    # -----------------------------------------------------
    # 1. 改用root权限登录执行即可
    #
    # 2. SETUID, SETGIT - reference : https://blog.csdn.net/qq_38132048/article/details/78302582
    # 进程运行时能够访问哪些资源或文件，不取决于进程文件的属主属组，而是取决于运行该命令的用户身份的uid/gid，以该身份获取各种系统资源。
    # 对一个属主为root的可执行文件，如果设置了SUID位，则其他所有普通用户都将可以以root身份运行该文件，获取相应的系统资源。
    # 可以简单地理解为让普通用户拥有可以执行“只有root权限才能执行”的特殊权限。
    # setuid，setuid的作用是让执行该命令的用户以该命令拥有者的权限去执行，比如普通用户执行passwd时会拥有root的权限，
    # 这样就可以修改/etc/passwd这个文件了。它的标志为：s，会出现在x的地方，例：-rwsr-xr-x  。而setgid的意思和它是一样的，
    # 即让执行文件的用户以该文件所属组的权限去执行。
    # Code Example :
    # import os
    # os.seteuid(0)
    # >>> OSError: [Errno 1] Operation not permitted
    # 但是执行seteuid(0)的时候也需要root权限 - -!
    #
    # 3. SETCAP - reference : https://linux.die.net/man/8/setcap
    #             reference : https://www.jianshu.com/p/deb0ed35c1c2
    # **用setcap替换setuid的方式给予读取系统目录的权限**
    #
    # 上面讲解了深度系统监视器的核心模块的原理和代码参考实现，我们会发现大部分都要读取系统目录 /proc,
    # /proc这个目录的大部分内容只有root用户才有权限读取。
    # 很多初学者喜欢用setuid的方式直接赋予二进制root权限，但是这样非常危险，会造成图形前端获得过大的权限，从而产生安全漏洞。
    # Linux内核针对这种情况有更好的实现方式，用 setcap 给予二进制特定的权限，保证二进制的特殊权限在最小的范围中，
    # 比如在深度系统监视器中就用命令：
    # sudo setcap cap_kill,cap_net_raw,cap_dac_read_search,cap_sys_ptrace+ep ./deepin-system-monitor
    #
    # 来给予进程相应的能力，比如：
    # cap_net_raw 对应网络文件读取权限
    # cap_dac_read_search 对应文件读取检查权限
    # cap_sys_ptrace 对应进程内存信息读取权限
    # 这样，在保证二进制有对应读取权限的同时，又保证了二进制最小化的权限范围，最大化的保证了应用和系统的安全。
    #
    # 但是setcap只能用于授予可执行文件(c编译出来的文件)相应的权限,如果给python源代码文件(.py文件)授予权限后,依然正常使用
    # =====Eg=====
    #  houjie@houjie  ~/Watch_Dogs/Watch_Dogs/Core/dist  ./process_monitor
    # Traceback (most recent call last):
    #   File "Watch_Dogs/Core/process_monitor.py", line 450, in <module>
    #   File "Watch_Dogs/Core/prcess_exception.py", line 109, in wrapper
    # prcess_exception.AccessDenied: Access Denied (pid=875)
    # [9453] Failed to execute script process_monitor
    #  ✘ houjie@houjie  ~/Watch_Dogs/Watch_Dogs/Core/dist  sudo setcap cap_kill,cap_net_raw,
    #  cap_dac_read_search,cap_sys_ptrace+ep ./process_monitor
    #  houjie@houjie  ~/Watch_Dogs/Watch_Dogs/Core/dist  ./process_monitor
    # rchar: 18389336
    # wchar: 30947737
    # syscr: 1027
    # syscw: 6249
    # read_bytes: 65286144
    # write_bytes: 47058944
    # cancelled_write_bytes: 1523712
    # 在通过python调用可执行文件的方式获取结果?
    #
    # 目前最为'优雅'的解决办法:
    # 给python解释器提权 sudo setcap cap_kill,cap_net_raw,cap_dac_read_search,cap_sys_ptrace+ep ./python2.7
    # 取消权限 sudo setcap cap_sys_ptrace+ep ./python2.7
    # 这样python在读取文件时候就可以无障碍了,但是存在的问题就是这台机器上的python可以获取任意读取所有文件的权限. 甚至于/etc/passwd
    # 但是由于setcap的关系,只给了python解释器最小的权限. 并不存在进行删除或者其他危险操作的权限,相比于1,2 还是更为安全一点
    #
    # 4. PyInstaller - reference : http://www.cnblogs.com/mywolrd/p/4756005.html
    # 通过PyInstaller将核心内容打包成可执行文件后,用setcap提权(看起来是最优雅的,待完成所有功能后试一下,如何交互呢?)
    # ...待完善

    with open("/proc/{}/io".format(pid), "r") as p_io:
        rchar = p_io.readline().split(':')[1].strip()
        wchar = p_io.readline().split(':')[1].strip()

    return map(int, [rchar, wchar])


def calc_process_cpu_io(pid, interval=calc_func_interval):
    """计算进程的磁盘IO速度 (单位MB/s)"""
    global all_process_info_dict, process_info_dict
    # 初始化 - 添加进程信息
    if int(pid) not in all_process_info_dict["pid"]:
        all_process_info_dict["pid"].add(int(pid))
        all_process_info_dict["process_info"][str(pid)] = deepcopy(process_info_dict)  # 添加一个全新的进程数据结构副本

    # 添加数据结构信息
    if all_process_info_dict["process_info"][str(pid)]["prev_io"] is None:
        all_process_info_dict["process_info"][str(pid)]["prev_io"] = get_process_io(pid)
        all_process_info_dict["process_info"][str(pid)]["pre_time"] = time()
        sleep(interval)

    current_time = time()
    current_rchar, current_wchar = get_process_io(pid)

    # 注意,这里为了计算磁盘的IO,除以的数字是1000而不是1024
    read_MBs = (current_rchar - all_process_info_dict["process_info"][str(pid)]["prev_io"][0]) \
               / 1000. ** 2 / (current_time - all_process_info_dict["process_info"][str(pid)]["pre_time"])
    write_MBs = (current_wchar - all_process_info_dict["process_info"][str(pid)]["prev_io"][1]) \
                / 1000. ** 2 / (current_time - all_process_info_dict["process_info"][str(pid)]["pre_time"])

    all_process_info_dict["process_info"][str(pid)]["prev_io"] = [current_rchar, current_wchar]
    all_process_info_dict["process_info"][str(pid)]["pre_time"] = current_time

    return [round(read_MBs, 2), round(write_MBs, 2)]


def get_process_net_info():
    pass


def is_log_exist(path):
    """判断日志文件是否存在 (输入绝对路径)"""
    return os.path.exists(path) and os.path.isfile(path) and os.access(path, os.R_OK)


def get_log_tail(path, n=10):
    """获取日志文件最后几行"""

    # author    : Armin Ronacher
    # reference : https://stackoverflow.com/questions/136168/get-last-n-lines-of-a-file-with-python-similar-to-tail
    def tail(f, n, offset=0):
        """Reads a n lines from f with an offset of offset lines."""
        avg_line_length = 74
        to_read = n + offset
        while 1:
            try:
                f.seek(-(avg_line_length * to_read), 2)
            except IOError:
                # woops.  apparently file is smaller than what we want
                # to step back, go to the beginning instead
                f.seek(0)
            pos = f.tell()
            lines = f.read().splitlines()
            if len(lines) >= to_read or pos == 0:
                return lines[-to_read:offset and -offset or None]
            avg_line_length *= 1.3

    with open(path, 'r') as log_f:
        return tail(log_f, n)


def get_log_last_update_time(path):
    """获取文件最后更新时间"""
    return strftime('%Y-%m-%d %H:%M:%S', localtime(os.stat(path).st_atime))


def get_log_keyword_lines(path, keyword):
    """获取日志文件含有关键词的行"""
    result = []
    n = 1
    with open(path, 'r') as log_f:
        for line in log_f:
            if keyword in line:
                result.append((n, line.strip()))
            n += 1

    return result


if __name__ == '__main__':
    print get_log_keyword_lines('/home/houjie/Watch_Dogs/Watch_Dogs/Core/log.txt','[')
