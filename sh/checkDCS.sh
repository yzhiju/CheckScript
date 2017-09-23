#!/bin/sh
#usage tmpdir virip dbip

TMPDIR=$1
VIRIP=$2
DBVIRIP=$3
source $TMPDIR/func.sh

DCS_XML=/opt/HMS/DCS/DCS.xml

if [ ! -d /opt/HMS/DCS ]; then
   echo "配置文件损坏，重新安装服务"
   exit 1
fi

STR=`sed -n '/<BLS>/p' $DCS_XML | awk -F'BLS>' '{print $2}' | sed 's/<\///'`
if [ -z "$STR" -o "$STR" != "$VIRIP:9001" ]; then
   echo "文件[$DCS_XML]中CBS的地址填写错误，必须填写虚拟IP地址[$VIRIP:9001]"
   exit 1
fi 

STR=`sed -n '/<ListenInfo>/p' $DCS_XML | awk -F'ListenInfo>' '{print $2}' | sed 's/<\///' | awk -F':' '{print $1}'`
if [ -z "$STR" -o "$STR" = "127.0.0.1" ]; then
   echo "文件[$DCS_XML]中ListenInfo的地址填写错误, 不能为空和127.0.0.1"
   exit 1
fi
isLocalHost $STR
if [ $? -eq 0 ]; then
   echo "文件[$DCS_XML]中ListenInfo的地址填写错误，必须填写本机的IP地址"
   exit 1
fi

#检查database.conf文件是否填写虚拟IP数据库地址
STR=`sed -n '/host/p' /opt/HMS/database.conf  | awk -F'host="' '{print $2}' | awk -F'" ' '{print $1}'`
if [ -z "$STR" -o "$STR" != "$DBVIRIP" ]; then
   echo "数据库文件[/opt/HMS/database.conf] 数据库地址必须填写数据库虚拟IP地址[$DBVIRIP]"
   exit 1
fi
