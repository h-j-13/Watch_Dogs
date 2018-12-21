#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <signal.h>
#include <linux/wait.h>

/**
 * 在linux下创建一个僵尸进程
 *
 * author       : echoSuccess
 * reference    : https://blog.csdn.net/u011123091/article/details/81220827
 */

int main(int argc,char **argv)

{
        int i=0;
        pid_t pid=fork();
        if(pid==-1) return 0;
        else if(pid==0)
        {
                printf("son pid is %d\n",getpid());
                while(1)
                {
                        printf("son---i=%d\n",i);
                        i++;
                        sleep(1);
                        if(i==5)
                        break;
                }
                printf("son is over!\n");
        }else if(pid>0)
        {
                printf("parent pid is %d\n",getpid());
                while(1) sleep(100);
        }
        return 0;

}