#!/bin/sh
#usage tmpdir orgCode VirtualIP DBVIRIP
source /etc/profile

TMPDIR=$1
ORGCODE=$2
VIRIP=$3
DBVIRIP=$4
source $TMPDIR/func.sh

SSH_PORT=16001
SFTP_PORT=16002
#mysftp
SFTPUSER=mysftp
#~Mysftp2017hdms!
SFTPPWD=~Mysftp2017hdms!

TOTALSPACE=50

#kafka:10.68.28.95:9092
KAFKAADDR=10.68.28.95:9092
mkdir -p $TMPDIR

##检查是否备机, 1-主, 0-备
isLocalHost $VIRIP
if [ $? -eq 0 ]; then
#1-正在运行，0-停止
   isRunning cbs
   [ $? -ne 0 ] && echo "备服务器不需要启动cbs服务" && exit 1

   isRunning angel
   [ $? -ne 0 ] && echo "备服务器不需要启动angel服务" && exit 1
else
   isRunning cbs
   [ $? -ne 1 ] && echo "主服务器需要启动cbs服务" && exit 1

   isRunning angel
   [ $? -ne 1 ] && echo "主服务器不需要启动angel服务" && exit 1
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
  echo "文件[WEB-INF/classes/config/project-cfg.xml]中网省公司编码[$STR]输入错误,请修改!"
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
if [ $? -ne 0 ]; then
   echo "文件[WEB-INF/classes/config/project-cfg.xml]中LIVE_CONTEXT字段配置错误"
   exit 1
fi

STR=`sed -n '/<DATA_REPORT_PATHS>/p' $PROJECT_FILE | awk -F'DATA_REPORT_PATHS>' '{print $2}' | sed 's/<\///'`
isLocalHostUrl $VIRIP $SSH_PORT "hdms/realdata/RealDataReport" $STR
if [ $? -ne 0 ]; then
   echo "文件[WEB-INF/classes/config/project-cfg.xml]中DATA_REPORT_PATHS字段配置错误"
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
   echo "文件[WEB-INF/classes/config/project-cfg.xml]中SFTP的IP字段配置[$STR]错误"
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
   echo "文件[WEB-INF/classes/config/db/druid-mysql.properties]数据库的地址[$STR]填写错误，应填数据库服务虚拟IP"
   exit 1
fi

echo "检查JBOSS配置完成，ok!"
exit 0
