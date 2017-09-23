#!/bin/sh

TMPDIR=$1

source $TMPDIR/func.sh

if [ ! -f /opt/HMS/CBS/cbs ]; then
   echo "请把此脚本放在纵向接口主服务上运行!"
   exit 1
fi

printALLCode $TMPDIR/orgCode
ORG_CODE=00
FLAG=true
while $FLAG
do
   read -p "请输入网省公司名字:" INPUTSTR
   ORG_CODE=`findCode $TMPDIR/orgCode $INPUTSTR`
   if [ ! -z "$ORG_CODE" ]; then
      break
   fi
   
done

#纵向接口目录
CHKJAVADIR=/tmp/checkJava
#前置机临时目录
CHKDASDIR=/tmp/checkDAS
#存储服务临时目录
CHKDCSDIR=/tmp/checkDCS
#数据库服务临时目录
CHKDBDIR=/tmp/checkDB

chmod 777 trust_ssh.bin

VIRIP=`sed -n '/virtual_ipaddress/{n;p}' /etc/keepalived/keepalived.conf | awk -F'/' '{print $1}'`
if [ -z "$VIRIP" ]; then
   echo "纵向接口服务的主从没做，请先做好主从后重新执行检查"
   exit 1
fi
echo "本纵向接口服务器虚拟IP地址: $VIRIP"

isLocalHost $VIRIP
if [ $? -eq 0 ]; then
   echo "本服务器不是纵向接口主服务器!"
   echo "请把此脚本放在纵向接口主服务上运行!"
   exit 1
fi

isRunning cbs
if [ $? -eq 0 ]; then
   echo "cbs服务没有运行！"
   exit 1
fi

TMPDBIP=`netstat -anp | grep cbs | grep 8336 | grep ESTABLISHED | awk -F' ' '{print $5}'|awk -F':' '{print $1}'`
for virDBIP in $TMPDBIP
do
   DBVIRIP=$virDBIP
   break
done

if [ -z "$DBVIRIP" ]; then
    echo "获取数据库地址失败"
    exit 1
fi
echo "数据库的虚拟IP地址为$DBVIRIP."

FLAG=true
while $FLAG
do
   read -p "请输入服务器的用户名:" user_name
   if [ ! -z "$user_name" ]; then
      FLAG=false
   fi
done

read -p "请输入服务器的密码:" user_pwd
read -p "请输入服务器的ssh端口[16002]:" ssh_port
if [ -z "$ssh_port" ]; then
   ssh_port=16002
fi

#修改ssh配置文件
sed -i '/GSSAPIAuthentication/c\GSSAPIAuthentication no' /etc/ssh/ssh_config

#目标文件目录
echo "检查$DBVIRIP是否虚拟IP"
sh $TMPDIR/trust_ssh.bin $DBVIRIP $ssh_port $user_name $user_pwd
ssh -p $ssh_port $user_name@$DBVIRIP "mkdir -p $CHKDBDIR"
BACKDBIP=`ssh -p $ssh_port $user_name@$DBVIRIP "sed -n '4p' $APP_ROOT/sgrdb/data8336/master.info"`
[ -z "$BACKDBIP" ] && echo "数据库主从没有做好,请重新建立主从" && exit 1
echo "数据库从IP地址:$BACKDBIP"
SCPFILETODEST $ssh_port $user_name $DBVIRIP $TMPDIR/check_sync_status.bin $CHKDBDIR
ssh -p $ssh_port $user_name@$DBVIRIP "sh $CHKDBDIR/check_sync_status.bin" || echo "数据库主从同步失败" && ssh -p $ssh_port $user_name@$DBVIRIP "rm -rf $CHKDBDIR" && exit 1
ssh -p $ssh_port $user_name@$DBVIRIP "sh $CHKDBDIR/checkDB.sh $DBVIRIP" || echo "/opt/HMS/database.conf文件数据库地址必须填写数据库虚拟IP地址" && ssh -p $ssh_port $user_name@$DBVIRIP "rm -rf $CHKDBDIR" && exit 1

SCPFILETODEST $ssh_port $user_name $DBVIRIP $TMPDIR/func.sh $CHKDBDIR
SCPFILETODEST $ssh_port $user_name $DBVIRIP $TMPDIR/checkDB.sh $CHKDBDIR
ssh -p $ssh_port $user_name@$DBVIRIP "sh $CHKDBDIR/checkDB.sh $DBVIRIP" || echo "检查数据库服务器[$DBVIRIP]发现错误，终止检查，修改后重新执行脚本" && ssh -p $ssh_port $user_name@$DBVIRIP "rm -rf $CHKDBDIR" && exit 1

SCPFILETODEST $ssh_port $user_name $BACKDBIP $TMPDIR/func.sh $CHKDBDIR
SCPFILETODEST $ssh_port $user_name $BACKDBIP $TMPDIR/checkDB.sh $CHKDBDIR
ssh -p $ssh_port $user_name@$BACKDBIP "sh $CHKDBDIR/checkDB.sh $DBVIRIP" || echo "检查[$BACKDBIP]发现错误，终止检查，修改后重新执行脚本" && ssh -p $ssh_port $user_name@$DBVIRIP "rm -rf $CHKDBDIR" && exit 1

SCPFILETODEST $ssh_port $user_name $DBVIRIP $TMPDIR/getServerList.sh $CHKDBDIR
ssh -p $ssh_port $user_name@$DBVIRIP "sh $CHKDBDIR/getServerList.sh 103 $CHKDBDIR/daslist"
ssh -p $ssh_port $user_name@$DBVIRIP "sh $CHKDBDIR/getServerList.sh 104 $CHKDBDIR/dcslist"
ssh -p $ssh_port $user_name@$DBVIRIP "sh $CHKDBDIR/getServerList.sh 105 $CHKDBDIR/weblist"
SCPFILEFROMDEST $ssh_port $user_name $DBVIRIP $CHKDBDIR/daslist $TMPDIR
SCPFILEFROMDEST $ssh_port $user_name $DBVIRIP $CHKDBDIR/dcslist $TMPDIR
SCPFILEFROMDEST $ssh_port $user_name $DBVIRIP $CHKDBDIR/weblist $TMPDIR

ssh -p $ssh_port $user_name@$BACKDBIP "rm -rf $CHKDBDIR"
ssh -p $ssh_port $user_name@$DBVIRIP "rm -rf $CHKDBDIR"

##检查本机器
echo "检查本机器..."
mkdir -p $CHKJAVADIR
cp -f $TMPDIR/func.sh $CHKJAVADIR
cp -f $TMPDIR/checkJava.sh $CHKJAVADIR
#sh $CHKJAVADIR/checkJava.sh $CHKJAVADIR $ORG_CODE $VIRIP $DBVIRIP
[ $? -ne 0 ] && echo "配置文件配置错误，根据提示修改，重新检查！" && rm -rf $CHKJAVADIR && exit 1

SID=`sed -n '/<CLIENT_ID>/p' $CHKJAVADIR/WEB-INF/classes/config/project-cfg.xml | awk -F'CLIENT_ID>' '{print $2}' | sed 's/<\///'`
STR=`sed -n "/^$SID/p" $TMPDIR/weblist`
[ -z "$STR" ] && echo "本纵向接口服务ID[$SID]重复或者数据库未配置服务，请重新配置" && rm -rf $CHKJAVADIR && exit 1

sed -i "/^$SID/d" $TMPDIR/weblist
rm -rf $CHKJAVADIR
echo "本机配置文件检查完成...ok, 开始检查其他服务器！"

LINES=`netstat -anp | grep 9001 | grep -v LISTEN | grep cbs | grep ESTABLISHED | awk -F' ' '{print $5}'`
for line in $LINES
do
   ip=`echo $line | awk -F':' '{print $1}'`
   port=`echo $line | awk -F':' '{print $2}'`
   echo "检查服务[$ip]..."
   isLocalHost $ip
   if [ $? -ne 0 ]; then
	echo "IP[$ip]为本机地址,检查下一个服务器..."
	continue
   fi
 
   sed -i "/^$ip/d" ~/.ssh/known_hosts
   sh $TMPDIR/trust_ssh.bin $ip $ssh_port $user_name $user_pwd
   if [ $? -eq 1 ]; then
	echo "输入的用户名或者密码错误！"
        exit 1
   elif [ $? -eq 2 ]; then
	echo "ssh 端口输入错误或者端口权限未开放！"
        exit 1
   fi
 
   EXE_NAME=`ssh -p $ssh_port $user_name@$ip "netstat -anp | grep $port | grep ESTABLISHED"`
   EXE_NAME=`echo "$EXE_NAME" | awk -F' ' '{print $7}' | awk -F'/' '{print $NF}'`
   if [ -z "$EXE_NAME" ]; then
	echo "未知服务器[$ip]"
	exit 1
   elif [ "$EXE_NAME" = "dlb" ]; then
	echo "目标服务器[$ip]为通信前置机"
	SID=`ssh -p $ssh_port $user_name@$ip "sed -n '/<ServerId>/p' /opt/HMS/DLB/DLB.xml"`
	SID=`echo $SID | awk -F'ServerId>' '{print $2}' | sed 's/<\///'`
	STR=`sed -n "/^$SID/p" $TMPDIR/daslist`
	if [ -z "$STR" ]; then
	    echo "前置机[$ip]服务ID[$SID]重复或者数据库未配置服务，请重新配置"
	    exit 1
	fi
	sed -i "/^$SID/d" $TMPDIR/daslist
	ssh -p $ssh_port $user_name@$ip "mkdir -p $CHKDASDIR"
        SCPFILETODEST $ssh_port $user_name $ip $TMPDIR/func.sh $CHKDASDIR
        SCPFILETODEST $ssh_port $user_name $ip $TMPDIR/checkDAS.sh $CHKDASDIR
        ssh -p $ssh_port $user_name@$ip "sh $CHKJAVADIR/checkDAS.sh $CHKDASDIR $ORG_CODE $VIRIP $DBVIRIP"
        if [ $? -ne 0 ]; then
           echo "通信前置服务器[$ip]检查配置文件出现错误，根据提示修改后重新执行检查脚本！"
	   ssh -p $ssh_port $user_name@$ip "rm -rf $CHKDASDIR"
   	   exit 1
        fi
	ssh -p $ssh_port $user_name@$ip "rm -rf $CHKDASDIR"
   elif [ "$EXE_NAME" = "dcs" ]; then
	echo "目标服务器[$ip]为存储服务器"
	SID=`ssh -p $ssh_port $user_name@$ip "sed -n '/<ServerId>/p' /opt/HMS/DCS/DCS.xml"`
	SID=`echo $SID | awk -F'ServerId>' '{print $2}' | sed 's/<\///'`
        STR=`sed -n "/^$SID/p" $TMPDIR/dcslist`
        if [ -z "$STR" ]; then
            echo "存储服务[$ip]服务ID[$SID]重复或者数据库未配置服务，请重新配置"
            exit 1
        fi
        sed -i "/^$SID/d" $TMPDIR/dcslist
	ssh -p $ssh_port $user_name@$ip "mkdir -p $CHKJAVADIR"
        SCPFILETODEST $ssh_port $user_name $ip $TMPDIR/func.sh $CHKDCSDIR
        SCPFILETODEST $ssh_port $user_name $ip $TMPDIR/checkDCS.sh $CHKDCSDIR
        ssh -p $ssh_port $user_name@$ip "sh $CHKJAVADIR/checkDCS.sh $CHKDCSDIR $VIRIP $DBVIRIP"
        if [ $? -ne 0 ]; then
           echo "存储服务器[$ip]检查配置文件出现错误，根据提示修改后重新执行检查脚本！"
	   ssh -p $ssh_port $user_name@$ip "rm -rf $CHKDCSDIR"
	   exit 1
        fi
	ssh -p $ssh_port $user_name@$ip "rm -rf $CHKDCSDIR"
   elif [ "$EXE_NAME" = "java" ]; then
        echo "目标服务器[$ip]为纵向接口服务器"
	ssh -p $ssh_port $user_name@$ip "mkdir -p $CHKJAVADIR"
	SCPFILETODEST $ssh_port $user_name $ip $TMPDIR/func.sh $CHKJAVADIR
	SCPFILETODEST $ssh_port $user_name $ip $TMPDIR/checkJava.sh $CHKJAVADIR
	ssh -p $ssh_port $user_name@$ip "sh $CHKJAVADIR/checkJava.sh $CHKJAVADIR $ORG_CODE $VIRIP $DBVIRIP"
	if [ $? -ne 0 ]; then
	   echo "纵向接口服务器[$ip]检查配置文件出现错误，根据提示修改后重新执行检查脚本！"
	   ssh -p $ssh_port $user_name@$ip "rm -rf $CHKJAVADIR"
	   exit 1
	fi

	SID=`ssh -p $ssh_port $user_name@$ip "sed -n '/<CLIENT_ID>/p' $CHKJAVADIR/WEB-INF/classes/config/project-cfg.xml"`
	SID=`echo $SID |awk -F'CLIENT_ID>' '{print $2}' | sed 's/<\///'`
	STR=`sed -n "/^$SID/p" $TMPDIR/weblist`
        if [ -z "$STR" ]; then
            echo "纵向接口[$ip]服务ID[$SID]重复或者数据库未配置服务，请重新配置"
	    ssh -p $ssh_port $user_name@$ip "rm -rf $CHKJAVADIR"
            exit 1
        fi
	sed -i "/^$SID/d" $TMPDIR/weblist
	ssh -p $ssh_port $user_name@$ip "rm -rf $CHKJAVADIR"
   fi	
 
done

echo "所有服务器检查项完成..ok"
exit 0