#!/bin/sh
#usage dbip

source /etc/profile
source /tmp/checkDB/func.sh

DBIP=$1
TYPE=$2
BACKUP_DIR=/mnt/dbbackup

echo "---------------------------------------"
echo "开始检查数据库服务器[$DBIP]，模式为[$TYPE]"

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

FOUND_STR=`grep "backup.sh" $APP_ROOT/sgrdb/enableback.sh`
if [ -z "$FOUND_STR" ]
then
    echo "enableback.sh脚本中没有启动备份的命令，联系管控组处理"
    exit 1
fi

FOUND_STR=`grep "setmaster.sh" $APP_ROOT/sgrdb/enableback.sh`
if [ -z "$FOUND_STR" ]
then
    echo "enableback.sh脚本中没有启动I6000计数的命令，联系管控组处理"
    exit 1
fi

isLocalHost $VIRIP
#1-主, 0-备
ISBACKHOST=$?

##备机不能有定时备份任务和
if [ $ISBACKHOST -eq 0 ]; then
   STR=`sed -n '/sgrdb\/backup.sh/p' /etc/crontab`
   [ ! -z "$STR" ] && echo "备机不需要执行备份任务，执行/etc/init.d/keepalived restart,再次检测" && exit 1
   
   STR=`sed -n '/sgrdb\/setmaster.sh/p' /etc/crontab`
   [ ! -z "$STR" ] && echo "备机不需要执行I6000定时任务，执行/etc/init.d/keepalived restart,再次检测" && exit 1

   if [ -d $BACKUP_DIR ]
   then
	STR=`mount | grep $BACKUP_DIR`
	[ ! -z "$STR" ] &&  echo "备机不应该挂载$BACKUP_DIR，执行/etc/init.d/keepalived restart,再次检测" && exit 1
   fi
else
    if [ $TYPE = "slave" ];then
        echo "两台数据库服务都进入主模式 执行/etc/init.d/keepalived restart 确认能否切换主从 "
        exit 1
    fi
   STR=`sed -n '/sgrdb\/backup.sh/p' /etc/crontab`
   [ -z "$STR" ] && echo "主机需要执行备份任务！执行/etc/init.d/keepalived restart,再次检测" && exit 1
   
   STR=`sed -n '/sgrdb\/setmaster.sh/p' /etc/crontab`
   [ -z "$STR" ] && echo "主机需要执行I6000定时任务！，执行/etc/init.d/keepalived restart,再次检测" && exit 1

   if [ -d $BACKUP_DIR ]
   then
	STR=`mount | grep $BACKUP_DIR`
	[ -z "$STR" ] &&  echo "主服务器必须挂载$BACKUP_DIR，执行/etc/init.d/keepalived restart,再次检测" && exit 1
   fi
fi

##检查备份脚本
BACKUP_SCRIPT=$APP_ROOT/sgrdb/backup.sh
if [ ! -f $BACKUP_SCRIPT ]
then
	echo "备份脚本不存在"
	exit 1
fi

BACKUP_CONFIG_DIR=`grep "^DESTDIR=" $BACKUP_SCRIPT | awk -F= '{print $2}'`
if [ -d $BACKUP_DIR ]
then
	[ "$BACKUP_CONFIG_DIR" != "$BACKUP_DIR" ] && echo "配置的数据库备份路径不是$BACKUP_DIR，手动修改$BACKUP_SCRIPT文件中的DESTDIR=为$BACKUP_DIR" && exit 1
else
	[ ! -d $BACKUP_CONFIG_DIR ] && echo "$BACKUP_SCRIPT中配置的数据库备份路径[$BACKUP_CONFIG_DIR]不存在" && exit 1
fi

echo "数据库配置检查完成...ok...success"

