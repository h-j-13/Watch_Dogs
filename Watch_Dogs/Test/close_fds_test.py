import os, time, sys, subprocess
print sys.argv
if len(sys.argv) == 2:
    time.sleep(100)
    print 'track end'
    if sys.platform == 'linux2':
        subprocess.Popen(['say', 'hello'])
else:
    print sys.platform
    print 'main begin'
    subprocess.Popen(['python', os.path.realpath(__file__), '0'], close_fds=True)
    print 'main end'