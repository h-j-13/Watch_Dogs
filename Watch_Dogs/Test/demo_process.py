#!/usr/bin/env python
# encoding:utf-8

"""
用于测试的文件
"""

import time

count = 1
for i in xrange(10):
    time.sleep(0.5)
    count += 1
    if count > 10:
        print time.time()
        count = 1

with open('a.txt', 'a') as a:
    for i in xrange(100):
        a.write('a')
        time.sleep(1)
        a.write('\n')
