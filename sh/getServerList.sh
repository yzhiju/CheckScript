#!/bin/sh

source /etc/profile
sgrdb -h127.0.0.1 -p8336 -umysql -p~Mysql2016pwd! --skip-column hdms -e "select serverid from servers where type=$1" > $2

exit $?
