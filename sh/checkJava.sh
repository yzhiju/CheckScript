#!/bin/sh
#usage tmpdir orgCode VirtualIP DBVIRIP
source /etc/profile

TMPDIR=$1
ORGCODE=$2
VIRIP=$3
DBVIRIP=$4
TYPE=$5
source $TMPDIR/func.sh

SSH_PORT=16001
SFTP_PORT=16002
#mysftp
SFTPUSER=mysftp
#~Mysftp2017hdms!
SFTPPWD=~Mysftp2017hdms!
LIST_FILE=/opt/HMS/mount.info

TOTALSPACE=50

#kafka:10.68.28.95:9092
KAFKAADDR=10.68.28.95:9092
mkdir -p $TMPDIR

echo "---------------------------------------"
echo "开始检查接口服务器，模式为[$TYPE]"

FOUND_SFTP_PORT=`netstat -anop | grep $SFTP_PORT | grep LISTEN`
if test -z "$FOUND_SFTP_PORT"
then
    SFTP_PORT=10022
fi

FOUND_SFTP_PORT=`netstat -anop | grep $SFTP_PORT | grep LISTEN`
if test -z "$FOUND_SFTP_PORT"
then
    echo "没有找到sftp监听端口16002或者10022"
    exit 1
fi

##检查是否备机, 1-主, 0-备
isLocalHost $VIRIP
if [ $? -eq 0 ]; then
#1-正在运行，0-停止
   isRunning cbs
   [ $? -ne 0 ] && echo "备服务器不需要启动cbs服务，执行/etc/init.d/hms stop停止掉" && exit 1

   isRunning angel
   [ $? -ne 0 ] && echo "备服务器不需要启动angel服务，执行/etc/init.d/hms stop停止掉" && exit 1

	if [ -f $LIST_FILE ]
	then
		while read line
		do
			if test "$line"
			then
				UUID=`echo "$line" | awk '{print $1}'`
				DISK=`echo "$line" | awk '{print $2}'`
				MOUNT=`mount | grep "$DISK"`
				if test "$MOUNT"
				then
					echo "备机上不应该挂载$DISK，手动将$DISK的挂载umount，确保卸载完毕，通过mount | grep $DISK查看不到记录，ps -ef | grep umount_san.sh确保无umount_san.sh进程存在"
					exit 1
				fi
			fi
		done < $LIST_FILE
	else
		#检查文件夹同步
		if [ -f /etc/init.d/run_rsync_sftp.sh -a -f /etc/init.d/run_rsync_wave.sh -a -f /etc/init.d/run_rsync_slave.sh -a -f /usr/bin/rsync ]
		then
			if test -z `ps -ef | grep /usr/bin/rsync | grep -v grep`
			then
				echo "/usr/bin/rsync进程未启动，查看/opt/HMS/update_master_status.sh中有没有/etc/init.d/run_rsync_slave.sh，并且是否/etc/init.d/run_rsync_slave.sh进程一直在运行"
				exit 1
			fi
			if test `ps -ef | grep /etc/init.d/run_rsync_sftp.sh | grep -v grep`
			then
				echo "/etc/init.d/run_rsync_sftp.sh进程不应该启动，重启机器再重新检查"
				exit 1
			fi
			if test `ps -ef | grep /etc/init.d/run_rsync_wave.sh | grep -v grep`
			then
				echo "/etc/init.d/run_rsync_wave.sh进程不应该启动，重启机器再重新检查"
				exit 1
			fi
		else
			echo "rsync没有安装"
			exit 1
		fi
	fi
else
    if [ $TYPE = "slave" ];then
        echo "两台接口服务都进入主模式 执行/etc/init.d/keepalived restart 确认能否切换主从 "
        exit 1
    fi
   isRunning cbs
   [ $? -ne 1 ] && echo "主服务器需要启动cbs服务，执行/etc/init.d/hms start启动" && exit 1

   isRunning angel
   [ $? -ne 1 ] && echo "主服务器需要启动angel服务，执行/etc/init.d/hms start启动" && exit 1

	if [ -f $LIST_FILE ]
	then
		while read line
		do
			if test "$line"
			then
				UUID=`echo "$line" | awk '{print $1}'`
				DISK=`echo "$line" | awk '{print $2}'`
				MOUNT=`mount | grep "$DISK"`
				if [ -z "$MOUNT" ]
				then
					echo "主服务器上必须挂载$DISK，手动执行mount $UUID $DISK，确保挂载成功，ps -ef | grep mount_san.sh确保无mount_san.sh进程存在"
					exit 1
				fi
			fi
		done < $LIST_FILE
	else
		#检查文件夹同步
		if [ -f /etc/init.d/run_rsync_sftp.sh -a -f /etc/init.d/run_rsync_wave.sh -a -f /etc/init.d/run_rsync_slave.sh -a -f /usr/bin/rsync ]
		then
			if test -z `ps -ef | grep /etc/init.d/run_rsync_sftp.sh | grep -v grep`
			then
				echo "/etc/init.d/run_rsync_sftp.sh进程未启动，查看/opt/HMS/update_master_status.sh中有没有sh /usr/local/rsync/start_rsync_master.sh，并且/usr/local/rsync/start_rsync_master.sh中有/etc/init.d/run_rsync_sftp.sh"
				exit 1
			fi
			if test -z `ps -ef | grep /etc/init.d/run_rsync_wave.sh | grep -v grep`
			then
				echo "/etc/init.d/run_rsync_wave.sh进程未启动，查看/opt/HMS/update_master_status.sh中有没有sh /usr/local/rsync/start_rsync_master.sh，并且/usr/local/rsync/start_rsync_master.sh中有/etc/init.d/run_rsync_wave.sh"
				exit 1
			fi
			if test `ps -ef | grep /usr/bin/rsync | grep -v grep`
			then
				echo "/usr/bin/rsync进程不应该启动，重启机器再重新检查"
				exit 1
			fi
		else
			echo "rsync没有安装"
			exit 1
		fi
	fi   
fi

#检查database.conf文件是否填写虚拟IP数据库地址
STR=`sed -n '/host/p' /opt/HMS/database.conf  | awk -F'host="' '{print $2}' | awk -F'" ' '{print $1}'`
if [ -z "$STR" -o "$STR" != "$DBVIRIP" ]; then
   echo "数据库文件[/opt/HMS/database.conf] 数据库地址必须填写数据库虚拟IP地址[$DBVIRIP]"
   exit 1
fi

STR=`sed -n '/port/p' /opt/HMS/database.conf  | awk -F'port="' '{print $2}' | awk -F'" ' '{print $1}'`
if [ -z "$STR" -o "$STR" != "8336" ]; then
   echo "数据库文件[/opt/HMS/database.conf] 数据库端口必须填写8336"
   exit 1
fi

cp $APP_ROOT/sgaps/standalone/deployments/hdms.war  $TMPDIR

unzip -o $TMPDIR/hdms.war WEB-INF/classes/config/project-cfg.xml -d $TMPDIR
PROJECT_FILE=$TMPDIR/WEB-INF/classes/config/project-cfg.xml

unzip -o $TMPDIR/hdms.war WEB-INF/classes/log4j.properties -d $TMPDIR
LOG_FILE=$TMPDIR/WEB-INF/classes/log4j.properties

unzip -o $TMPDIR/hdms.war WEB-INF/classes/config/db/druid-mysql.properties -d $TMPDIR
DB_FILE=$TMPDIR/WEB-INF/classes/config/db/druid-mysql.properties

STR=`sed -n '/<PHYSICAL_ID>/p' $PROJECT_FILE | awk -F'PHYSICAL_ID>' '{print $2}' | sed 's/<\///'`
if [ -z "$STR" -o "$STR" != "$ORGCODE" ]; then
  echo "文件[WEB-INF/classes/config/project-cfg.xml]中网省公司编码[$STR]输入错误，应该为[$ORGCODE],请修改!"
  exit 1
fi

STR=`sed -n '0,/<IP>/p' $PROJECT_FILE | sed -n '/<IP>/p' | awk -F'IP>' '{print $2}' | sed 's/<\///'`
if [ -z "$STR" -o "$STR" != "$VIRIP" ]; then
  echo "文件[WEB-INF/classes/config/project-cfg.xml]中CBS的IP地址填写错误,必须填虚拟IP[$VIRIP]"
  exit 1
fi


STR=`sed -n '0,/<PORT>/p' $PROJECT_FILE | sed -n '/<PORT>/p' | awk -F'PORT>' '{print $2}' | sed 's/<\///'`
if [ -z "$STR" -o "$STR" != "9001" ]; then
   echo "文件[WEB-INF/classes/config/project-cfg.xml]中CBS的PORT填写错误，必须为9001"
   exit 1
fi
#本机地址，非虚拟IP
STR=`sed -n '/<LIVE_CONTEXT>/p' $PROJECT_FILE | awk -F'LIVE_CONTEXT>' '{print $2}' | sed 's/<\///'`
isLocalHostUrl $VIRIP $SSH_PORT "hdms/live" $STR
if [ $? -ne 0 -a "$STR" != "http://localhost:$SSH_PORT/hdms/live" -a "$STR" != "http://127.0.0.1:$SSH_PORT/hdms/live" ]; then
   echo "文件[WEB-INF/classes/config/project-cfg.xml]中LIVE_CONTEXT字段配置错误"
   exit 1
fi

STR=`sed -n '/<DATA_REPORT_PATHS>/p' $PROJECT_FILE | awk -F'DATA_REPORT_PATHS>' '{print $2}' | sed 's/<\///'`
isLocalHostUrl $VIRIP $SSH_PORT "hdms/realdata/RealDataReport" $STR
if [ $? -ne 0 ]; then
   echo "文件[WEB-INF/classes/config/project-cfg.xml]中DATA_REPORT_PATHS字段配置错误，IP地址要使用本机地址，不要用虚拟IP"
   exit 1
fi

#sftp
SFTP_LINE=`grep -n "<SFTP>" $PROJECT_FILE | awk -F':' '{print $1}'`
if [ -z "$SFTP_LINE" ]; then
   echo "文件[WEB-INF/classes/config/project-cfg.xml]损坏，没有找到SFTP节点"
   exit 1
fi
STR=`sed -n "$SFTP_LINE,/<IP>/p" $PROJECT_FILE | sed -n '/<IP>/p' | awk -F'IP>' '{print $2}' | sed 's/<\///'`
isLocalHost "$STR"
if [ $? -eq 0 -o -z "$STR" -o "$STR" = "$VIRIP" ]; then
   echo "文件[WEB-INF/classes/config/project-cfg.xml]中SFTP的IP字段配置[$STR]错误，必须是本机IP"
   exit 1
fi
STR=`sed -n "$SFTP_LINE,/<PORT>/p" $PROJECT_FILE | sed -n '/<PORT>/p' | awk -F'PORT>' '{print $2}' | sed 's/<\///'`
if [ -z "$STR" -o "$STR" != "$SFTP_PORT" ]; then
   echo "文件[WEB-INF/classes/config/project-cfg.xml]中SFTP的PORT字段配置错误"
   exit 1
fi
STR=`sed -n "$SFTP_LINE,/<USER>/p" $PROJECT_FILE | sed -n '/<USER>/p' | awk -F'USER>' '{print $2}' | sed 's/<\///'`
if [ -z "$STR" -o "$STR" != "$SFTPUSER" ]; then
   echo "文件[WEB-INF/classes/config/project-cfg.xml]中SFTP的USER字段配置错误"
   exit 1
fi
STR=`sed -n "$SFTP_LINE,/<PASS>/p" $PROJECT_FILE | sed -n '/<PASS>/p' | awk -F'PASS>' '{print $2}' | sed 's/<\///'`
if [ -z "$STR" -o "$STR" != "$SFTPPWD" ]; then
   echo "文件[WEB-INF/classes/config/project-cfg.xml]中SFTP的PASS字段配置错误"
   exit 1
fi

##PATH
checkPATH(){
   STR=`sed -n "/<$1>/p" $PROJECT_FILE | awk -F"$1>" '{print $2}' | sed 's/<\///'`
   if [ -z "$STR" ]; then
        echo "文件[WEB-INF/classes/config/project-cfg.xml]中$1配置的路径[路径不能为空]" 
	return 1
   fi
  
   pdir=`dirname $STR` 
   if [ ! -d $pdir ]; then
	echo "文件[WEB-INF/classes/config/project-cfg.xml]中$1配置的路径[$STR根目录$pdir不存在,无法创建文件]"
	return 2
   fi
   
   SPACE=`df -TP "$pdir" | grep -v Filesystem | awk  '{print(($3/1024/1024)>'"$TOTALSPACE"')?"0":"1"}'` 
   if [ "$SPACE" = "1" ]; then
	echo "文件[WEB-INF/classes/config/project-cfg.xml]中$1配置的路径[$STR目录空间小于${TOTALSPACE}G]" 
	return 3
   fi
   return 0 
}
checkPATH "TIMER_DATA_FILE_PATH" || exit 1
checkPATH "QUERY_DATA_FILE_PATH" || exit 1
checkPATH "WAVE_DATA_FILE_PATH" || exit 1
checkPATH "REPACKAGE_DATA_FILE_PATH" || exit 1
checkPATH "RECALL_DATA_FILE_PATH" || exit 1
checkPATH "TIMER_DATA_PACKAGE_PATH" || exit 1
checkPATH "QUERY_DATA_PACKAGE_PATH" || exit 1
checkPATH "WAVE_DATA_PACKAGE_PATH" || exit 1
checkPATH "REPACKAGE_DATA_PACKAGE_PATH" || exit 1
checkPATH "RECALL_DATA_PACKAGE_PATH" || exit 1

#kafka
STR=`sed -n "/<BROKER_LIST>/p" $PROJECT_FILE | awk -F"BROKER_LIST>" '{print $2}' | sed 's/<\///'`
if [ -z "$STR" -o "$STR" != "$KAFKAADDR" ]; then
   echo "文件[WEB-INF/classes/config/project-cfg.xml]中KafKa总线的地址[$STR]填写错误,kafka固定地址[$KAFKAADDR]"
   exit 1
fi

##db配置
STR=`sed -n '/^datasource.url/p' $DB_FILE | awk -F'=' '{print $2}' | awk -F'jdbc:mysql://' '{print $2}' | awk -F'/' '{print $1}'`
if [ -z "$STR" -o "$STR" != "$DBVIRIP:8336" ]; then
   echo "文件[WEB-INF/classes/config/db/druid-mysql.properties]数据库的地址[$STR]填写错误，应填数据库服务虚拟IP[$DBVIRIP]"
   exit 1
fi

echo "检查JBOSS配置完成，ok!...success"
exit 0
