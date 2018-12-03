#!/usr/bin/env python
# encoding:utf-8

"""
进程检测核心功能实现

主要包括
- 总体CPU占用率


reference : https://www.jianshu.com/p/deb0ed35c1c2
"""

from time import sleep

prev_work_time = 0
prev_total_time = 0


def get_total_cpu_time():
    """获取总cpu时间 - /proc/stat"""

    """
    From man proc(5)
    ...
    
    /proc/stat 
        kernel/system statistics.  Varies with architecture.  Common entries include:

        cpu 10132153 290696 3084719 46828483 16683 0 25195 0 175628 0
        cpu0 1393280 32966 572056 13343292 6130 0 17875 0 23933 0
        
        The  amount  of  time,  measured in units of USER_HZ (1/100ths of a second on most architectures, 
        use sysconf(_SC_CLK_TCK) to obtain the right value), that the system ("cpu" line) or 
        the specific CPU ("cpuN" line) spent in various states:

            user   (1) Time spent in user mode.
            
            nice   (2) Time spent in user mode with low priority (nice).
            
            system (3) Time spent in system mode.
            
            idle   (4) Time spent in the idle task.  This value should be USER_HZ times the second entry in the /proc/uptime pseudo-file.
            
            iowait (since Linux 2.5.41) (5) Time waiting for I/O to complete.  
                This value is not reliable, for the following reasons:
                    1. The CPU will not wait for I/O to complete; iowait is the time that a task is waiting for I/O to complete.  
                    When a CPU goes into idle state for outstanding task I/O, another task will be scheduled on this CPU.
    
                    2. On a multi-core CPU, the task waiting for I/O to complete is not running on any CPU, so the iowait of each CPU is difficult to calculate.
    
                    3. The value in this field may decrease in certain conditions.
    
            irq (since Linux 2.6.0-test4) (6) Time servicing interrupts.
    
            softirq (since Linux 2.6.0-test4) (7) Time servicing softirqs.
    
            steal (since Linux 2.6.11) (8) Stolen time, which is the time spent in other operating systems when running in a virtualized environment
    
            guest (since Linux 2.6.24) (9) Time spent running a virtual CPU for guest operating systems under the control of the Linux kernel.
    
            guest_nice (since Linux 2.6.33) (10) Time spent running a niced guest (virtual CPU for guest operating systems under the control of the Linux kernel).

        page 5741 1808
        The number of pages the system paged in and the number that were paged out (from disk).

        swap 1 0
        The number of swap pages that have been brought in and out.

        intr 1462898
        This  line  shows  counts  of  interrupts  serviced since boot time, for each of the possible system interrupts.
        The first column is the total of all interrupts serviced including unnumbered architecture specific
        interrupts; each subsequent column is the total for that particular numbered interrupt.  
        Unnumbered interrupts are not shown, only summed into the total.

        disk_io: (2,0):(31,30,5764,1,2) (3,0):...
        (major,disk_idx):(noinfo, read_io_ops, blks_read, write_io_ops, blks_written)
        (Linux 2.4 only)

        ctxt 115315
        The number of context switches that the system underwent.

        btime 769041601
        boot time, in seconds since the Epoch, 1970-01-01 00:00:00 +0000 (UTC).

        processes 86031
        Number of forks since boot.

        procs_running 6
        Number of processes in runnable state.  (Linux 2.5.45 onward.)

        procs_blocked 2
        Number of processes blocked waiting for I/O to complete.  (Linux 2.5.45 onward.)

        softirq 229245889 94 60001584 13619 5175704 2471304 28 51212741 59130143 0 51240672
        This line shows the number of softirq for all CPUs.  The first column is the total of all softirqs and 
        each subsequent column is the total for particular softirq.  (Linux 2.6.31 onward.)
    """

    # CPU的占有率计算公式
    # workTime  =   user + nice + system;
    # totalTime =   return user + nice + system + idle + iowait + irq + softirq + steal;
    # cpuPercent = (currentWorkTime - prevWorkTime) / (currentTotalTime - prevTotalTime)

    #
    # sum everything up (except guest and guestnice since they are already included
    # in user and nice, see http://unix.stackexchange.com/q/178045/20626)

    with open("/proc/stat", "r") as cpu_stat:
        total_cpu_time = cpu_stat.readline().replace('cpu', '').strip()
        user, nice, system, idle, iowait, irq, softirq, steal, guest, guestnice = map(int, total_cpu_time.split(' '))
        return user + nice + system + idle + iowait + irq + softirq + steal, user + nice + system


def calc_cpu_percent(interval=2):
    """计算CPU总占用率 (返回的是百分比)"""
    # 两次调用之间的间隔最好不要小于2s,否则可能会为0
    global prev_work_time, prev_total_time
    if prev_work_time == 0:  # 未初始化
        prev_total_time, prev_work_time = get_total_cpu_time()
        sleep(interval)
    current_total_time, current_work_time = get_total_cpu_time()
    cpu_percent = (current_work_time - prev_work_time) * 100.0 / (current_total_time - prev_total_time)
    prev_total_time, prev_work_time = current_total_time, current_work_time
    return cpu_percent


if __name__ == '__main__':
    while 1:
        sleep(3)
        print calc_cpu_percent()
