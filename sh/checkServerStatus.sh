#!/bin/sh
source /etc/profile
DISCONNET_SERVERS=`sgrdb -umysql -p~Mysql2016pwd! -S /tmp/sgrdb8336.sock --skip-column hdms -e "select id,serverid, type,name,status from servers where status=2"`
if test "$DISCONNET_SERVERS"
then
	echo $DISCONNET_SERVERS
	echo "以上服务不在线，用checkPing检测该服务器能否连接接口服务器VIP的9001端口"
	exit 1
else
	echo "所有服务都在线"
fi

COUNT=`sgrdb -umysql -p~Mysql2016pwd! -S /tmp/sgrdb8336.sock --skip-column hdms -e "select count(id) from servers where type=103"`
echo "前置机个数为$COUNT，确认个数是否正确？？？"

COUNT=`sgrdb -umysql -p~Mysql2016pwd! -S /tmp/sgrdb8336.sock --skip-column hdms -e "select count(id) from servers where type=104"`
echo "数据存储服务器个数为$COUNT，确认个数是否正确？？？"

