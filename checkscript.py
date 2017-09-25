#!/usr/bin/env python
# -*- coding: gb2312 -*-

import paramiko
from scpclient import *
from contextlib import closing
import time
import re
import sys
import logging

#����ӿ�Ŀ¼
CHKJAVADIR="/tmp/checkJava"
#ǰ�û���ʱĿ¼
CHKDASDIR="/tmp/checkDAS"
#�洢������ʱĿ¼
CHKDCSDIR="/tmp/checkDCS"
#���ݿ������ʱĿ¼
CHKDBDIR="/tmp/checkDB"
global ORG_CODE
global VIRIP
global DBVIRIP
global InterfaceVirIP
global ALLCONNECT
ALLCONNECT={}
InterfaceVirIP=""
ORG_CODE="00"
VIRIP=""
DBVIRIP=""

# logging.basicConfig(level=logging.DEBUG,
#                 format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
#                 datefmt='%a, %d %b %Y %H:%M:%S',
#                 filename='checkscript.log',
#                 filemode='w')
#
# console = logging.StreamHandler(sys.stdout)
# console.setLevel(logging.INFO)
# formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
# console.setFormatter(formatter)
# logging.getLogger('').addHandler(console)

# ��ȡloggerʵ�����������Ϊ���򷵻�root logger
logger = logging.getLogger("AppName")
# ָ��logger�����ʽ
formatter = logging.Formatter('%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)-8s: %(message)s')
# �ļ���־
file_handler = logging.FileHandler("checkscript.log")
file_handler.setFormatter(formatter)  # ����ͨ��setFormatterָ�������ʽ
# ����̨��־
console_handler = logging.StreamHandler(sys.stdout)
console_handler.formatter = formatter  # Ҳ����ֱ�Ӹ�formatter��ֵ
# Ϊlogger��ӵ���־������
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# ָ����־������������Ĭ��ΪWARN����
logger.setLevel(logging.DEBUG)

class UserPwd:
    def __init__(self):
        self.ip=""
        self.port=16002
        self.pwd=""
        self.username = "root"
        self.name=""

def checkip(ip):
    p = re.compile('^((25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(25[0-5]|2[0-4]\d|[01]?\d\d?)$')
    if p.match(ip):
        return True
    else:
        return False

def EXIT(code):
    time.sleep(2)
    exit(code)

class baseConnect():
    def __init__(self,hostname,port,username,password):
        self.hostname=hostname
        self.port=port
        self.username=username
        self.password=password
        self.connect()
        self.execCmd("source /etc/profile")
        self.CPUAndMemRunInfo()
    def connect(self):
        #paramiko.util.log_to_file("paramiko.log")
        self.con = paramiko.SSHClient()
        self.con.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            self.con.connect(hostname=self.hostname, port=self.port, username=self.username, password=self.password)
        except :#paramiko.ssh_exception,e
            logger.error("%s %d connect failed![username=%s,pwd=%s]",self.hostname,self.port,self.username,self.password)
            exit(1)
        logger.info("connect %s:%d success"%(self.hostname,self.port))

    def disConnect(self):
        self.con.close()
        logger.info("disconnect %s:%d" % (self.hostname, self.port))

    def execCmd(self,cmd):
        logger.info("execCmd: %s",cmd)
        stdin, stdout, stderr = self.con.exec_command(cmd)
        # time.sleep(0.1)
        # stdin.write("Y")
        time.sleep(0.1)
        str = stdout.read()
        strErr = stderr.read()
        if str!='':
            # try:
            #     logger.info("execCmd stdout:%s",str.decode('utf8').encode('gb2312'))
            # except:
            #     logger.info("execCmd stdout:%s", str)
            return  str
        elif strErr != '':
            logger.error("%s" %strErr)
            exit(1)
            #return -1
        else:
            logger.warning("execCmd:%s return NULL",cmd)
            return -1

    def uploadFile(self,localPath,remotePath):
        '''�ϴ���������ָ���ļ�'''
        sshclient = paramiko.SSHClient()
        sshclient.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            sshclient.connect(hostname=self.hostname, port=self.port, username=self.username, password=self.password)
            with closing(Write(sshclient.get_transport(), remotePath)) as scp:
                scp.send_file(localPath, True)
        except:
            sshclient.close()
            #print "�ϴ��ļ�%s��ip=%s %sʧ��\n"%(localPath,self.hostname,remotePath)
            logger.error("�ϴ��ļ�%s��ip=%s %sʧ��\n"%(localPath,self.hostname,remotePath))
            exit(1)
        sshclient.close()
        return True

    def downloadFile(self,localPath,remotePath):
        '''�ӷ������л�ȡ�ļ�'''
        sshclient = paramiko.SSHClient()
        sshclient.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        sshclient.connect(hostname=self.hostname, port=self.port, username=self.username, password=self.password)
        # with closing(Read(sshclient.get_transport(), remotePath)) as scp:
        #     scp.receive(localPath)
        fp = open(localPath, 'w')
        cat = self.execCmd("cat %s" % remotePath)
        if cat != -1:
            fp.write(cat)
        fp.close()
    def isLocalHost(self,ip):
        if ip=="127.0.0.1":
            return True
        ips=self.execCmd("LC_ALL=C ifconfig  | grep 'inet addr:'| grep -v '127.0.0.1' |cut -d: -f2 | awk '{ print $1}'")
        for tmp_ip in ips:
            if tmp_ip == ip:
                return True
        return False

    def isLocalHostUrl(self,surl,sport,dstUrl):
        ips=self.execCmd("LC_ALL=C ifconfig  | grep 'inet addr:'| grep -v '127.0.0.1' |cut -d: -f2 | awk '{ print $1}'")
        for tmp_ip in ips:
            url="http://$tmp_ip:%d/%s"%sport,surl
            if url == dstUrl:
                return 0
        return 1

    def localHostType(self,port):
        '''�������'''
        name1 = self.execCmd("netstat -anp | grep %d | grep ESTABLISHED"%int(port))
        name = self.execCmd("echo \"%s\" | awk -F' ' '{print $7}' | awk -F'/' '{print $NF}'"%name1)
        if name =="":
            logger.info( "δ֪������[%s]"%self.hostname)
            exit(1)
        elif name.find("dlb") != -1:
            logger.info("������[%s]Ϊͨ��ǰ�û�"%self.hostname)
            name="dlb"
        elif name.find("dcs") != -1:
            logger.info("������[%s]Ϊ�洢������" % self.hostname)
            name="dcs"
        elif name.find("java") != -1:
            logger.info("������[%s]Ϊ����ӿڷ�����" % self.hostname)
            name="java"
        return name
    def CPUAndMemRunInfo(self):
        '''��ȡcpu���ڴ�ʹ�����'''
        try:
            cpuStr = self.execCmd("/usr/bin/top -n 1 | grep Cpu")
            logger.info("%s",cpuStr)
            memStr = self.execCmd("/usr/bin/top -n 1 |grep Mem")
            logger.info("%s",memStr)
        except:
            pass
        pass

class InterfaceServer(baseConnect):
    def __init__(self,hostname,port,username,password):
        baseConnect.__init__(self,hostname,port,username,password)
        self.virtualIP=""

    def mkdirCheckJavaDir(self):
        ret = self.execCmd("ls -l /tmp/ | grep -w checkJava")
        if ret == -1:
            ret = self.execCmd("mkdir -p %s"%CHKJAVADIR)
            if ret == "":
                logger.info("�����ӿڷ�����ʱĿ¼�ɹ�")
            return ret

    def rmCheckJavaDir(self):
        ret = self.execCmd("ls -l /tmp/ | grep checkJava")
        if ret != -1:
            ret = self.execCmd("rm -rf %s"%CHKJAVADIR)

    def getVirtualAddress(self):
        '''��ȡ�����ַ'''
        ret=self.execCmd("sed -n \'/virtual_ipaddress/{n;p}\' /etc/keepalived/keepalived.conf | awk -F\'/\' \'{print $1}\'")
        if ret == -1:
            logger.error("����ӿڷ��������û���������������Ӻ�����ִ�м��")
            exit(1)
        else:
            ret=ret.expandtabs()
            ret=ret.strip()
            str=ret.splitlines(False)
            logger.info("����ӿڷ���������IP��ַ:%s"%str[0])
            self.virtualIP=str[0]
            return str
    def isCBSRunning(self):
        '''�ж�cbs�����Ƿ�����'''
        ret=self.execCmd("ps -ef | grep cbs | grep -v grep")
        if ret == -1:
            logger.error("cbs����û�����У�����ps -ef | grep angelȷ��angel������û�У����û�У�ͨ��/etc/init.d/hms start����,����У���ϵ��Ŀ��")
            exit(1)
        return True

    def getDBVirtualAddress(self):
        '''��ȡ���ݿ������ַ'''
        ipList=[]
        ret = self.execCmd("netstat -anp | grep cbs | grep 8336 | grep ESTABLISHED | awk -F' ' '{print $5}'|awk -F':' '{print $1}'")
        if ret == -1:
            logger.error("û�����ӵ����ݿ���������ڽӿڷ������ϣ�ͨ��checkpingȷ�����ݿ�����IP�Ƿ��������")
            exit(1)
        ipList = ret.splitlines(False)
        logger.info("���ݿ������IP��ַΪ%s"%ipList[0])
        return ipList

    def checkInterServerId(self):
        self.mkdirCheckJavaDir()
        fp=open("./tmpdir/weblist",'r')
        if fp== None:
            logger.info("tmpdir/weblist �ļ�������")
            return False
        else:
            fp.close()
        localDir = "./tmpdir/weblist"
        remoteDir = CHKJAVADIR
        ret = self.uploadFile(localDir, remoteDir+"/weblist")
        sid = self.execCmd("sed -n \'/<CLIENT_ID>/p\' %s/WEB-INF/classes/config/project-cfg.xml | awk -F\'CLIENT_ID>\' \'{print $2}\' | sed \'s/<\///\'"%CHKJAVADIR)
        str = self.execCmd("sed -n \"/^%s/p\" %s/weblist"%(sid.strip("\n"),CHKJAVADIR))
        if str == -1:
            logger.error("������ӿڷ���ID[%s]������һ̨�ӿڷ���ID��ͬ������������"%sid)
            self.rmCheckJavaDir()
            exit(1)
        # else:
        #     self.execCmd("sed -i \"/^%s/d\" %s/weblist"%(sid.strip("\n"),CHKJAVADIR))
        #     logger.info("���������ļ�������...ok, ��ʼ���������������")
        #     #self.downloadFile(localDir,remoteDir+"/weblist")

        self.execCmd("sed -i \"/^%s/d\" %s/weblist" % (sid.strip("\n"), CHKJAVADIR))
        localDir = "./tmpdir/weblist"
        fp = open(localDir, 'w')
        cat = self.execCmd("cat %s/weblist" % CHKJAVADIR)
        if cat != -1:
            fp.write(cat)
        fp.close()

    #��ȡ9001�˿ڵ�����ip
    def getAllConnectIp(self):
        ipdict={}
        lines = self.execCmd("netstat -anp | grep 9001 | grep -v LISTEN | grep cbs | awk -F' ' '{print $5}' | sort -u")
        if lines == -1:
            return ipdict
        lines=lines.splitlines(False)
        for line in lines:
            ip=self.execCmd("echo %s | awk -F':' '{print $1}'"%line)
            port=self.execCmd("echo %s | awk -F':' '{print $2}'"%line)
            ret=self.isLocalHost(ip.strip("\n"))
            if ret == True:
                logger.info("ip=%s Ϊ������ַ,�����һ��������..."%ip.strip("\n"))
                continue
            if VIRIP == ip.strip("\n"):
                logger.info("ip=%s Ϊ����ip,�����һ��������..." % ip.strip("\n"))
                continue
            #ipdict.append(ip.splitlines(False))
            ipdict[ip.strip("\n")]=port.strip("\n")
        return ipdict
    #������Ҫ�ļ��ű�
    def sendNeedFile(self):
        self.mkdirCheckJavaDir()
        localDir="./sh/checkJava.sh"
        remoteDir=CHKJAVADIR
        ret=self.uploadFile(localDir,remoteDir+"/checkJava.sh")
        self.execCmd("chmod a+x %s/checkJava.sh"%remoteDir)

        localDir="./sh/func.sh"
        remoteDir=CHKJAVADIR
        ret=self.uploadFile(localDir,remoteDir+"/func.sh")
        self.execCmd("chmod a+x %s/func.sh"%remoteDir)

        localDir="./tmpdir/weblist"
        remoteDir=CHKJAVADIR
        ret=self.uploadFile(localDir,remoteDir+"/weblist")
        pass

    def checkServerId(self,type):
        global ORG_CODE
        global VIRIP
        global DBVIRIP

        ret=self.execCmd("sh %s/checkJava.sh %s %s %s %s %s"%(CHKJAVADIR,CHKJAVADIR,ORG_CODE,VIRIP,DBVIRIP,type))
        try:
            if ret.find("success") == -1:
                logger.error("ͨ��ǰ�÷�����[$ip]��������ļ����ִ��󣬸�����ʾ�޸ĺ�����ִ�м��ű���"%self.hostname)
                exit(1)
        except:
            logger.info("-----checkServerId---except----")
        self.checkInterServerId()
        self.rmCheckJavaDir()

        pass


class DBServer(baseConnect):
    '''���ݿ����'''
    dirFlag=False
    def __int__(self,hostname,port,username,password):
        baseConnect.__init__(self,hostname,port,username,password)
        self.execCmd("source /etc/profile")
        self.dirFlag=False

    def mkdirCheckDBDir(self):
        ret = self.execCmd("ls -l /tmp/ | grep checkDB")
        if ret == -1:
            ret = self.execCmd("mkdir -p %s"%CHKDBDIR)
            if ret == "":
                logger.info("���ݿ������ʱĿ¼�ɹ�")
            return ret

    def rmCheckDBDir(self):
        ret = self.execCmd("ls -l /tmp/ | grep -w checkDB")
        if ret != -1:
            ret = self.execCmd("rm -rf %s"%CHKDBDIR)


    def getBackDBIp(self):
        path=self.execCmd("source /etc/profile && echo $APP_ROOT")
        if path == -1:
            return ""
        path=path.strip("\n")
        ret=self.execCmd("sed -n '4p' %s/sgrdb/data8336/master.info"%path)
        if ret == -1:
            logger.error("8336���ݿ�����û�����ã�û��sgrdb/data8336/master.info�ļ�,�����½�������")
            exit(1)
        logger.info("���ݿ��IP��ַ:%s"%ret)
        ret = ret.strip("\n")
        return ret

    def sendCheckSyncBinToCheckDBDir(self):
        self.mkdirCheckDBDir()
        localDir="./sh/check_sync_status.bin"
        remoteDir=CHKDBDIR
        ret=self.uploadFile(localDir,remoteDir+"/check_sync_status.bin")
        self.execCmd("chmod a+x %s/check_sync_status.bin"%remoteDir)
        return ret

    def shCheckSyncBinFromCheckDBDir(self):
        ret = self.execCmd("ls -l %s/check_sync_status.bin" % CHKDBDIR)
        if ret == -1:
            return ret
        ret=self.execCmd("sh %s/check_sync_status.bin"%CHKDBDIR)
        logger.info("run check_sync_status.bin \n %s"%ret)
        return ret

    def sendCheckDbShToCheckDBDir(self):
        self.mkdirCheckDBDir()
        localDir="./sh/checkDB.sh"
        remoteDir=CHKDBDIR
        ret=self.uploadFile(localDir,remoteDir+"/checkDB.sh")
        self.execCmd("chmod a+x %s/checkDB.sh"%remoteDir)

        localDir="./sh/func.sh"
        remoteDir=CHKDBDIR
        ret=self.uploadFile(localDir,remoteDir+"/func.sh")
        self.execCmd("chmod a+x %s/func.sh"%remoteDir)

        return ret

    def shCheckDbShFromCheckDBDir(self,virip,type):
        ret = self.execCmd("ls -l %s/checkDB.sh" % CHKDBDIR)
        if ret == -1:
            return ret
        ret=self.execCmd("sh %s/checkDB.sh %s %s"%(CHKDBDIR,virip,type))
        logger.info("run checkDB.sh \n %s" % ret.decode('utf8').encode('gb2312'))
        try:
            if ret.find("success")==-1:
                logger.error("���ݿ�����[%s]��������ļ����ִ��󣬸�����ʾ�޸ĺ�����ִ�м��ű���"%self.hostname)
                exit(1)
        except:
            logger.info("-----shCheckDbShFromCheckDBDir---except----")

        return ret

    def sendCheckServerStatusToCheckDBDir(self):
        self.mkdirCheckDBDir()
        localDir="./sh/checkServerStatus.sh"
        remoteDir=CHKDBDIR
        ret=self.uploadFile(localDir,remoteDir+"/checkServerStatus.sh")
        self.execCmd("chmod a+x %s/checkServerStatus.sh"%remoteDir)

    def shCheckServerStatusFromCheckDBDir(self):
        self.execCmd("ifconfig")
        ret = self.execCmd("ls -l %s/checkServerStatus.sh" % CHKDBDIR)
        if ret == -1:
            return ret
        try:
            ret = self.execCmd("sh %s/checkServerStatus.sh" %CHKDBDIR)
            logger.info("run checkServerStatus.sh \n %s" % ret.decode('utf8').encode('gb2312'))
        except:
            logger.info("run checkServerStatus.sh \n %s" % ret)
        self.rmCheckDBDir()

    def getDBVirtualIp(self):
        ret=self.execCmd("sed -n '/virtual_ipaddress/{n;p}' /etc/keepalived/keepalived.conf | awk -F'/' '{print $1}'")
        if ret == -1:
            logger.error("get virtual ip failed")
            exit(1)
        logger.info("���ݿ����������IP��ַ:%s"%ret)
        return ret

    def isVirIpEqDbIp(self,virIp,dbIp):
        ret=self.execCmd("echo %s | grep %s"%virIp,dbIp)
        if ret == "":
            logger.info("/opt/HMS/database.conf������д���ݿ������IP��ַ")
            exit(1)
        return True
    #
    # def backHostCheck(self):
    #     ret = self.execCmd("sed -n '/sgrdb\/backup.sh/p' /etc/crontab" )
    #     if ret != -1:
    #         logger.info("��������Ҫִ�б�������")
    #         exit(1)
    #     ret = self.execCmd("sed -n '/sgrdb\/setmaster.sh/p' /etc/crontab")
    #     if ret != -1:
    #         logger.info("��������Ҫִ��I6000��ʱ����")
    #         exit(1)
    #
    # def masterHostCheck(self):
    #     ret = self.execCmd("sed -n '/sgrdb\/backup.sh/p' /etc/crontab" )
    #     if ret == -1:
    #         logger.info("������Ҫִ�б�������")
    #         exit(1)
    #     ret = self.execCmd("sed -n '/sgrdb\/setmaster.sh/p' /etc/crontab")
    #     if ret != -1:
    #         logger.info("������Ҫִ��I6000��ʱ����")
    #         exit(1)

    #Master
    def __sendServerListShell__(self):
        localDir = "./sh/getServerList.sh"
        remoteDir = CHKDBDIR
        ret = self.uploadFile(localDir, remoteDir+"/getServerList.sh")
        self.execCmd("chmod a+x %s/getServerList.sh" % remoteDir)
        return ret

    def getServerList(self):
        self.__sendServerListShell__()
        self.execCmd("sh %s/getServerList.sh 103 %s/daslist" %(CHKDBDIR,CHKDBDIR))
        self.execCmd("sh %s/getServerList.sh 104 %s/dcslist" %(CHKDBDIR,CHKDBDIR))
        self.execCmd("sh %s/getServerList.sh 105 %s/weblist" % (CHKDBDIR,CHKDBDIR))

        remoteDir = CHKDBDIR
        ret = self.execCmd("ls -l %s/daslist" % CHKDBDIR)
        if ret !="\n":
            localDir = "./tmpdir/daslist"
            fp=open(localDir,'w')
            cat = self.execCmd("cat %s/daslist" % CHKDBDIR)
            if cat !=-1:
                fp.write(cat)
            fp.close()
            # self.downloadFile(localDir,remoteDir+"/daslist")
        ret = self.execCmd("ls -l %s/dcslist" % CHKDBDIR)
        if ret !="\n":
            localDir = "./tmpdir/dcslist"
            fp=open(localDir,'w')
            cat = self.execCmd("cat %s/dcslist" % CHKDBDIR)
            if cat !=-1:
                fp.write(cat)
            fp.close()
            # self.downloadFile(localDir,remoteDir+"/dcslist")
        ret = self.execCmd("ls -l %s/weblist" % CHKDBDIR)
        if ret !="\n":
            localDir = "./tmpdir/weblist"
            fp=open(localDir,'w')
            cat = self.execCmd("cat %s/weblist" % CHKDBDIR)
            if cat !=-1:
                fp.write(cat)
            fp.close()
            # self.downloadFile(localDir,remoteDir+"/weblist")

class DataStorageServer(baseConnect):
    '''�洢����'''
    def __int__(self,hostname,port,username,password):
        baseConnect.__init__(self,hostname,port,username,password)
    def mkdirCheckDCSDir(self):
        ret = self.execCmd("ls -l /tmp/ | grep checkDCS")
        if ret == -1:
            ret = self.execCmd("mkdir -p %s"%CHKDCSDIR)
            if ret == "":
                logger.info("�洢������ʱĿ¼�ɹ�")
            return ret

    def rmCheckDCSDir(self):
        ret = self.execCmd("ls -l /tmp/ | grep checkDCS")
        if ret != -1:
            ret = self.execCmd("rm -rf %s"%CHKDCSDIR)
    #������Ҫ�ļ��ű�
    def sendNeedFile(self):
        self.mkdirCheckDCSDir()
        localDir="./sh/checkDCS.sh"
        remoteDir=CHKDCSDIR
        ret=self.uploadFile(localDir,remoteDir+"/checkDCS.sh")
        self.execCmd("chmod a+x %s/checkDCS.sh"%remoteDir)

        localDir="./sh/func.sh"
        remoteDir=CHKDCSDIR
        ret=self.uploadFile(localDir,remoteDir+"/func.sh")
        self.execCmd("chmod a+x %s/func.sh"%remoteDir)

        localDir="./tmpdir/dcslist"
        remoteDir=CHKDCSDIR
        ret=self.uploadFile(localDir,remoteDir+"/dcslist")
        pass

    def checkServerId(self):
        sid = self.execCmd("sed -n '/<ServerId>/p' /opt/HMS/DCS/DCS.xml")
        sid = self.execCmd("echo \"%s\" | awk -F'ServerId>' '{print $2}' | sed 's/<\///'"%sid.strip("\n"))
        str=self.execCmd("sed -n \"/^%s/p\" %s/dcslist"%(sid.strip("\n"),CHKDCSDIR))
        if str ==-1:
            logger.error("�洢����[%s]����ID[%s]�ظ��������ݿ�δ���÷�������������"%(self.hostname,sid.strip("\n")))
            exit(1)
        try:
            self.execCmd("sed -i \"/^%s/d\" %s/dcslist" % (sid.strip("\n"), CHKDCSDIR))
        except:
            logger.info("--------have except-----------------1")

        localDir = "./tmpdir/dcslist"
        fp = open(localDir, 'w')
        cat = self.execCmd("cat %s/dcslist" % CHKDCSDIR)
        if cat != -1:
            logger.info("wirte start %s",cat)
            fp.write(cat)
            logger.info("wirte end")
        fp.close()

        global VIRIP
        global DBVIRIP
        try:
            ret=self.execCmd("sh %s/checkDCS.sh %s %s %s"%(CHKDCSDIR,CHKDCSDIR,VIRIP,DBVIRIP))
            if ret.find("success") == -1:
                logger.error("�洢������[%s]��������ļ����ִ��󣬸�����ʾ�޸ĺ�����ִ�м��ű���"%self.hostname)
                exit(1)
            logger.info("-------------------------2")
            self.rmCheckDCSDir()
        except:
            logger.info("--------have except-----------------2")

class CommFrontServer(baseConnect):
    '''ͨ��ǰ�û�����'''
    def __int__(self, hostname, port, username, password):
        baseConnect.__init__(self, hostname, port, username, password)

    def mkdirCheckDASDir(self):
        ret = self.execCmd("ls -l /tmp/ | grep checkDAS")
        if ret == -1:
            ret = self.execCmd("mkdir -p %s"%CHKDASDIR)
            if ret == "":
                logger.info("ǰ�û�������ʱĿ¼�ɹ�")
        return ret

    def rmCheckDASDir(self):
        ret = self.execCmd("ls -l /tmp/ | grep checkDAS")
        if ret != -1:
            ret = self.execCmd("rm -rf %s"%CHKDASDIR)

    def sendNeedFile(self):
        self.mkdirCheckDASDir()
        localDir="./sh/checkDAS.sh"
        remoteDir=CHKDASDIR
        ret=self.uploadFile(localDir,remoteDir+"/checkDAS.sh")
        self.execCmd("chmod a+x %s/checkDAS.sh"%remoteDir)

        localDir="./sh/func.sh"
        remoteDir=CHKDASDIR
        ret=self.uploadFile(localDir,remoteDir+"/func.sh")
        self.execCmd("chmod a+x %s/func.sh"%remoteDir)

        localDir="./tmpdir/daslist"
        remoteDir=CHKDASDIR
        ret=self.uploadFile(localDir,remoteDir+"/daslist")
        pass

    def checkServerId(self):
        sid = self.execCmd("sed -n '/<ServerId>/p' /opt/HMS/DLB/DLB.xml")
        sid = self.execCmd("echo \"%s\" | awk -F'ServerId>' '{print $2}' | sed 's/<\///'"%sid.strip("\n"))
        str=self.execCmd("sed -n \"/^%s/p\" %s/daslist"%(sid.strip("\n"),CHKDASDIR))
        if str ==-1:
            logger.error("ǰ�û�[%s]����ID[%s]�ظ��������ݿ�δ���÷�������������"%(self.hostname,sid.strip("\n")))
            exit(1)
        self.execCmd("sed -i \"/^%s/d\" %s/daslist" % (sid.strip("\n"), CHKDASDIR))
        localDir = "./tmpdir/daslist"
        fp = open(localDir, 'w')
        cat = self.execCmd("cat %s/daslist" % CHKDASDIR)
        if cat != -1:
            fp.write(cat)
        fp.close()

        global ORG_CODE
        global VIRIP
        global DBVIRIP
        ret=self.execCmd("sh %s/checkDAS.sh %s %s %s %s"%(CHKDASDIR,CHKDASDIR,ORG_CODE,VIRIP,DBVIRIP))
        try:
            if ret.find("success")==-1:
                logger.error("ͨ��ǰ�÷�����[$ip]��������ļ����ִ��󣬸�����ʾ�޸ĺ�����ִ�м��ű���"%self.hostname)
                exit(1)
        except:
            pass
        self.rmCheckDASDir()
        pass


def ReadUserAndPwd():
    '''��ȡ���е��û���Ϣ'''
    fp = open("user", 'r')
    usrInfo={}
    c=0
    name=""
    while 1:
        line = fp.readline()
        c+=1
        if not line:
            break
        line=line.strip("\n")
        num=len(line)
        if line[0] == '[' and line[num-1] == ']':
            name=line.decode('utf8').encode('gb2312')
            continue
        userpwd=UserPwd()
        i=line.find(":")
        j = line.find(":",i+1)
        k = line.find(":",j+1)
        userpwd.ip=line[0:i]
        userpwd.port=line[i+1:j]
        userpwd.username=line[j+1:k]
        userpwd.pwd=line[k+1:].strip("\n")
        userpwd.name=name
        if c==2:
            global InterfaceVirIP
            InterfaceVirIP = userpwd.ip
        usrInfo[userpwd.ip]=userpwd
    #
    # for lip, ls in usrInfo.items():
    #     print "%s,%s"%(lip,ls.name)
    return usrInfo

def GetInterfaceInfo():
    '''��ȡ����ӿ�ip'''
    ip = raw_input("����ӿڷ�������ip:")
    ret=checkip(ip)
    if ret == False:
        logger.info("����ip����")
        exit(1)
    # port = raw_input("����ӿڷ���port:")
    # if port == "":
    #     port=16002
    # user = raw_input("����ӿڷ����û���:")
    # pwd = raw_input("����ӿڷ�������:")
    # ip="192.168.2.72"
    # port=22
    # user="root"
    # pwd="123456"
    logger.info("����ӿ� ip=%s",ip)
    return ip

#ǰ�û�
def dlbDealProcess(hostname,port,username,password):
    dlbServer=CommFrontServer(hostname,port,username,password)
    if None == dlbServer:
        pass
    dlbServer.sendNeedFile()
    dlbServer.checkServerId()
    dlbServer.disConnect()
    pass
#�洢������
def dcsDealProcess(hostname,port,username,password):
    dcsServer=DataStorageServer(hostname,port,username,password)
    if None == dcsServer:
        pass
    dcsServer.sendNeedFile()
    dcsServer.checkServerId()
    dcsServer.disConnect()
    pass

#�ӿڷ�����
def javaDealProcess(hostname,port,username,password):
    javaServer=InterfaceServer(hostname,port,username,password)
    if None == javaServer:
        pass
    javaServer.sendNeedFile()
    javaServer.checkServerId("slave")
    javaServer.disConnect()
    pass



def dealProcess():
    global ALLCONNECT
    logger.info("dealProcess....")
    usersInfo = ReadUserAndPwd()
    global  InterfaceVirIP
    if InterfaceVirIP == "":
        logger.error("user�ļ�������ӿڷ���������IPû������")
        exit(1)
    hostname = InterfaceVirIP
    interServerInfo = usersInfo.get(hostname)
    interServer = InterfaceServer(hostname,int(interServerInfo.port),interServerInfo.username,interServerInfo.pwd)
    if interServer ==None:
        logger.error("����interServer ʧ�� ")
        exit(1)

    ALLCONNECT[hostname] = interServerInfo.name
    virIp=interServer.getVirtualAddress()
    interServer.isCBSRunning()
    virDBIpList=interServer.getDBVirtualAddress()
    if len(virDBIpList) == 0:
        exit(1)
    virDBIp=virDBIpList[0]
    virDBIpInfo = usersInfo.get(virDBIp)
    if None == virDBIpInfo:
        logger.info("δ�ҵ����ݿ�����ip��Ӧ���û�����")
        exit(1)
    virDBServer= DBServer(virDBIpInfo.ip,int(virDBIpInfo.port),virDBIpInfo.username,virDBIpInfo.pwd)
    if None == virDBServer:
        exit(1)
    ALLCONNECT[virDBIpInfo.ip] = virDBIpInfo.name
    backDBIp=virDBServer.getBackDBIp()
    virDBServer.mkdirCheckDBDir()
    virDBServer.sendCheckSyncBinToCheckDBDir()
    virDBServer.sendCheckDbShToCheckDBDir()
    virDBServer.shCheckSyncBinFromCheckDBDir()
    virDBServer.shCheckDbShFromCheckDBDir(virDBIp,"master")
    virDBServer.getServerList()
    virDBServer.rmCheckDBDir()

    backDBIpInfo = usersInfo.get(backDBIp)
    if None == backDBIpInfo:
        logger.info("δ�ҵ����ݿ�back ip��Ӧ���û�����")
        exit(1)
    backDBServer = DBServer(backDBIpInfo.ip, int(backDBIpInfo.port), backDBIpInfo.username, backDBIpInfo.pwd)
    if None == backDBServer:
        exit(1)
    ALLCONNECT[backDBIpInfo.ip] = backDBIpInfo.name
    backDBServer.sendCheckDbShToCheckDBDir()
    backDBServer.shCheckDbShFromCheckDBDir(virDBIp,"slave")
    backDBServer.rmCheckDBDir()
    #disconnect db
    virDBServer.disConnect()
    backDBServer.disConnect()

    global VIRIP
    global DBVIRIP
    VIRIP=virIp[0]
    DBVIRIP=virDBIp
    #��鱾��(��)
    interServer.sendNeedFile()
    interServer.checkServerId("master")

    All9001Ip=interServer.getAllConnectIp()
    if len(All9001Ip) ==0:
        logger.info("����ӿڷ����ȡ�����κ�����9001ip")
        exit(1)

    for ip,port in All9001Ip.items():
        info=usersInfo.get(ip)
        if None==info:
            continue
        basecon=baseConnect(info.ip,int(info.port), info.username,info.pwd)
        if None == basecon:
            logger.info("ssh����ip[%s]ʧ��",info.ip)
            exit(1)
        typeName=basecon.localHostType(port)
        basecon.disConnect()
        if typeName == "dlb":
            dlbDealProcess(info.ip,int(info.port), info.username,info.pwd)

            pass
        elif typeName =="dcs":
            dcsDealProcess(info.ip,int(info.port), info.username,info.pwd)
            pass
        elif typeName =="java":
            javaDealProcess(info.ip,int(info.port), info.username,info.pwd)
            pass
        else:
            logger.info("δ֪������ ip:%s"%info.ip)
            continue
        ALLCONNECT[info.ip] = info.name
        pass

    revirDBServer= DBServer(virDBIpInfo.ip,int(virDBIpInfo.port),virDBIpInfo.username,virDBIpInfo.pwd)
    revirDBServer.sendCheckServerStatusToCheckDBDir()
    revirDBServer.shCheckServerStatusFromCheckDBDir()
    revirDBServer.disConnect()
    logger.info("�������ӳɹ��ķ�������")
    for lip,lname in ALLCONNECT.items():
        logger.info("%s,%s",lip,lname)

if __name__ == "__main__":

    fp=open("./orgCode",'r')
    if fp ==None:
        logger.info("open file ./orgCode failed")
    content=fp.read()
    content=content.decode('utf8').encode('gb2312')
    print content

    ORG_CODE=content.strip("\n")
    dealProcess()
    raw_input("������Enter���˳�:")
