#!/bin/sh
source /etc/profile
DISCONNET_SERVERS=`sgrdb -umysql -p~Mysql2016pwd! -S /tmp/sgrdb8336.sock --skip-column hdms -e "select id,serverid, type,name,status from servers where status=2"`
if test "$DISCONNET_SERVERS"
then
	echo $DISCONNET_SERVERS
	echo "���Ϸ������ߣ���checkPing���÷������ܷ����ӽӿڷ�����VIP��9001�˿�"
	exit 1
else
	echo "���з�������"
fi

COUNT=`sgrdb -umysql -p~Mysql2016pwd! -S /tmp/sgrdb8336.sock --skip-column hdms -e "select count(id) from servers where type=103"`
echo "ǰ�û�����Ϊ$COUNT��ȷ�ϸ����Ƿ���ȷ������"

COUNT=`sgrdb -umysql -p~Mysql2016pwd! -S /tmp/sgrdb8336.sock --skip-column hdms -e "select count(id) from servers where type=104"`
echo "���ݴ洢����������Ϊ$COUNT��ȷ�ϸ����Ƿ���ȷ������"

