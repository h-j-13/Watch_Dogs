#!/usr/bin/env python
# encoding:utf-8

import os

print "pid = ", os.getpid()

raw_input("wait to start...")

f = open("test.txt", "w")
s = "".join(['s' for i in xrange(100)])

for i in xrange(10000000):
    f.write(s + '\n')

raw_input('finish...clear')

# os.remove("test.txt")


# 确定了 rcahr wchar 的单位是字节,在文件系统中 1Kb=1024b 在磁盘中 1Kb = 1000b