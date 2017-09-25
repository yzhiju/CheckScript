#!/bin/sh
#usage tmpdir orgcode virip

TMPDIR=$1
ORGCODE=$2
VIRIP=$3

source $TMPDIR/func.sh

echo "---------------------------------------"
echo "开始检查前置机服务器"

if [ ! -d /opt/HMS/DLB -o ! -d /opt/HMS/DAS ]; then
   echo "配置文件损坏，重新安装服务"  
   exit 1
fi 

DLB_XML=/opt/HMS/DLB/DLB.xml
DAS_XML=/opt/HMS/DAS/DAS.xml
##检查DLB.XML
STR=`sed -n '/<BLS>/p' $DLB_XML | awk -F'BLS>' '{print $2}' | sed 's/<\///'`
if [ -z "$STR" -o "$STR" != "$VIRIP:9001" ]; then
   echo "文件[$DLB_XML]中CBS的地址填写错误，必须填写虚拟IP地址[$VIRIP:9001]"
   exit 1
fi

STR=`sed -n '/<ListenInfo>/p' $DLB_XML | awk -F'ListenInfo>' '{print $2}' | sed 's/<\///'`
if [ -z "$STR" -o "$STR" != "127.0.0.1:9005" ]; then
   echo "文件[$DLB_XML]中ListenInfo的地址填写错误，必须填写[127.0.0.1:9005]"
   exit 1
fi

##DAS.xml
STR=`sed -n '/<BLS>/p' $DAS_XML | awk -F'BLS>' '{print $2}' | sed 's/<\///'`
if [ -z "$STR" -o "$STR" != "127.0.0.1:9005" ]; then
   echo "文件[$DAS_XML]中CBS的地址填写错误，必须填写[127.0.0.1:9005]"
   exit 1
fi

STR=`sed -n '/<HTTP>/p' $DAS_XML | awk -F'HTTP>' '{print $2}' | sed 's/<\///'`
if [ -z "$STR" -o "$STR" != "http://$VIRIP:16001/hdms/data/WaveDataUpload?" ]; then
   echo "文件[$DAS_XML]中HTTP的地址填写错误，必须填写虚拟IP路径URL[http://$VIRIP:16001/hdms/data/WaveDataUpload?]"
   exit 1
fi

STR=`sed -n '/<OrgCode>/p' $DAS_XML | awk -F'OrgCode>' '{print $2}' | sed 's/<\///'`
if [ -z "$STR" -o "$STR" != "$ORGCODE" ]; then
   echo "文件[$DAS_XML]中OrgCode的填写错误，必须填写正确的省公司编码[$ORGCODE]"
   exit 1
fi

echo "前置机配置检查完成...ok..success"
exit 0
