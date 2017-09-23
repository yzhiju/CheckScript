#!/bin/sh
#usage dbip

source /etc/profile

DBIP=$1

VIRIP=`sed -n '/virtual_ipaddress/{n;p}' /etc/keepalived/keepalived.conf | awk -F'/' '{print $1}'`
if [ -z "$VIRIP" ]; then
   echo "get virtual ip failed"
fi
echo "数据库服务器虚拟IP地址: $VIRIP"

STR=`echo $VIRIP | grep $DBIP`
if [ -z "$STR" ]; then
    echo "/opt/HMS/database.conf必须填写数据库的虚拟IP地址"
    exit 1
fi

isLocalHost $DBIP
#1-主, 0-备
ISBACKHOST=$?

##备机不能有定时备份任务和
if [ $ISBACKHOST -eq 0 ]; then
   STR=`sed -n '/sgrdb\/backup.sh/p' /etc/crontab`
   [ ! -z "$STR" ] && echo "备机不需要执行备份任务" && exit 1
   
   STR=`sed -n '/sgrdb\/setmaster.sh/p' /etc/crontab`
   [ ! -z "$STR" ] && echo "备机不需要执行I6000定时任务" && exit 1
else
   STR=`sed -n '/sgrdb\/backup.sh/p' /etc/crontab`
   [ -z "$STR" ] && echo "主机需要执行备份任务！" && exit 1
   
   STR=`sed -n '/sgrdb\/setmaster.sh/p' /etc/crontab`
   [ ! -z "$STR" ] && echo "主机需要执行I6000定时任务！" && exit 1
fi

##检查备份脚本
