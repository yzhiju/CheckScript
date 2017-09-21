#!/usr/bin/env python
# -*- coding: gb2312 -*-

import paramiko
from scpclient import *
from contextlib import closing
import time
import re
import sys
import logging

#纵向接口目录
CHKJAVADIR="/tmp/checkJava"
#前置机临时目录
CHKDASDIR="/tmp/checkDAS"
#存储服务临时目录
CHKDCSDIR="/tmp/checkDCS"
#数据库服务临时目录
CHKDBDIR="/tmp/checkDB"
global ORG_CODE
global VIRIP
global DBVIRIP

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

# 获取logger实例，如果参数为空则返回root logger
logger = logging.getLogger("AppName")
# 指定logger输出格式
formatter = logging.Formatter('%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)-8s: %(message)s')
# 文件日志
file_handler = logging.FileHandler("checkscript.log")
file_handler.setFormatter(formatter)  # 可以通过setFormatter指定输出格式
# 控制台日志
console_handler = logging.StreamHandler(sys.stdout)
console_handler.formatter = formatter  # 也可以直接给formatter赋值
# 为logger添加的日志处理器
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# 指定日志的最低输出级别，默认为WARN级别
logger.setLevel(logging.INFO)

class UserPwd:
    def __init__(self):
        self.ip=""
        self.port=16002
        self.pwd=""
        self.username = "root"

def checkip(ip):
    p = re.compile('^((25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(25[0-5]|2[0-4]\d|[01]?\d\d?)$')
    if p.match(ip):
        return True
    else:
        return False

class baseConnect():
    def __init__(self,hostname,port,username,password):
        self.hostname=hostname
        self.port=port
        self.username=username
        self.password=password
        self.connect()
        self.execCmd("source /etc/profile")

    def connect(self):
        #paramiko.util.log_to_file("paramiko.log")
        self.con = paramiko.SSHClient()
        self.con.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            self.con.connect(hostname=self.hostname, port=self.port, username=self.username, password=self.password)
        except :#paramiko.ssh_exception,e
            logger.error("%s %d connect failed!"%(self.hostname,self.port))
            exit(1)
        logger.info("connect %s:%d success"%(self.hostname,self.port))

    def disConnect(self):
        self.con.close()

    def execCmd(self,cmd):
        stdin, stdout, stderr = self.con.exec_command(cmd)
        # time.sleep(0.1)
        # stdin.write("Y")
        time.sleep(0.1)
        str = stdout.read()
        strErr = stderr.read()
        if str!='':
            return  str
        elif strErr != '':
            logger.error("%s" %strErr)
            exit(1)
            #return -1
        else:
            return -1

    def uploadFile(self,localPath,remotePath):
        '''上传到服务器指定文件'''
        sshclient = paramiko.SSHClient()
        sshclient.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            sshclient.connect(hostname=self.hostname, port=self.port, username=self.username, password=self.password)
            with closing(Write(sshclient.get_transport(), remotePath)) as scp:
                scp.send_file(localPath, True)
        except:
            sshclient.close()
            #print "上传文件%s到ip=%s %s失败\n"%(localPath,self.hostname,remotePath)
            logger.error("上传文件%s到ip=%s %s失败\n"%(localPath,self.hostname,remotePath))
            return False
        sshclient.close()
        return True

    def downloadFile(self,localPath,remotePath):
        '''从服务器中获取文件'''
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

    def localHostType(self):
        '''主机类别'''
        name1 = self.execCmd("netstat -anp | grep %d | grep ESTABLISHED"%self.port)
        name = self.execCmd("echo \"%s\" | awk -F' ' '{print $7}' | awk -F'/' '{print $NF}'"%name1)
        if name =="":
            logger.info( "未知服务器[%s]"%self.hostname)
            exit(1)
        elif name.find("dlb") != -1:
            print "服务器[%s]为通信前置机"%self.hostname
            name="dlb"
            # sid=self.execCmd("sed -n '/<ServerId>/p' /opt/HMS/DLB/DLB.xml")
            # sid = self.execCmd("echo %s | awk -F'ServerId>' '{print $2}' | sed 's/<\///'"%sid)
            # str=self.execCmd("sed -n \"/^%s/p\" $TMPDIR/daslist"%sid)
            # if str == "":
            #     print "前置机[%s]服务ID[$SID]重复或者数据库未配置服务，请重新配置"%self.hostname
            #     exit(1)
        elif name.find("dcs") != -1:
            print "服务器[%s]为存储服务器" % self.hostname
            name="dcs"
            # sid=self.execCmd("sed -n '/<ServerId>/p' /opt/HMS/DCS/DCS.xml")
            # sid = self.execCmd("echo %s | awk -F'ServerId>' '{print $2}' | sed 's/<\///'"%sid)
            # str=self.execCmd("sed -n \"/^%s/p\" $TMPDIR/dcslist"%sid)
            # if str == "":
            #     print "存储服务[%s]服务ID[%s]重复或者数据库未配置服务，请重新配置"%self.hostname,sid
            #     exit(1)
        elif name.find("java") != -1:
            print "服务器[%s]为纵向接口服务器" % self.hostname
            name="java"
        return name


class InterfaceServer(baseConnect):
    def __init__(self,hostname,port,username,password):
        baseConnect.__init__(self,hostname,port,username,password)
        self.virtualIP=""

    def mkdirCheckJavaDir(self):
        ret = self.execCmd("mkdir -p %s"%CHKJAVADIR)
        if ret == "":
            print "创建接口服务临时目录成功"
        return ret

    def rmCheckJavaDir(self):
        ret = self.execCmd("rm -rf %s"%CHKJAVADIR)

    def getVirtualAddress(self):
        '''获取虚拟地址'''
        ret=self.execCmd("sed -n \'/virtual_ipaddress/{n;p}\' /etc/keepalived/keepalived.conf | awk -F\'/\' \'{print $1}\'")
        if ret == -1:
            print "纵向接口服务的主从没做，请先做好主从后重新执行检查"
            exit(1)
        else:
            ret=ret.expandtabs()
            ret=ret.strip()
            str=ret.splitlines(False)
            print "纵向接口服务器虚拟IP地址:%s"%str[0]
            self.virtualIP=str[0]
            return str
    def isCBSRunning(self):
        '''判断cbs服务是否运行'''
        ret=self.execCmd("ps -ef | grep cbs | grep -v grep")
        if ret == -1:
            print "判断cbs服务运行失败！"
            #exit(1)
        if ret == "":
            print "cbs服务没有运行！"
            return False
        return True

    def getDBVirtualAddress(self):
        '''获取数据库虚拟地址'''
        ipList=[]
        ret = self.execCmd("netstat -anp | grep cbs | grep 8336 | grep ESTABLISHED | awk -F' ' '{print $5}'|awk -F':' '{print $1}'")
        if ret == -1:
            print "获取数据库虚拟地址运行失败！"
            exit(1)
        if ret == "":
            print "获取数据库地址失败"
            return ipList
        ipList = ret.splitlines(False)
        print "数据库的虚拟IP地址为%s"%ipList[0]
        return ipList

    def checkInterServerId(self):
        self.mkdirCheckJavaDir()
        fp=open("./tmpdir/weblist",'r')
        if fp== None:
            print "tmpdir/weblist 文件不存在"
            return False
        else:
            fp.close()
        localDir = "./tmpdir/weblist"
        remoteDir = CHKJAVADIR
        ret = self.uploadFile(localDir, remoteDir+"/weblist")
        sid = self.execCmd("sed -n \'/<CLIENT_ID>/p\' %s/WEB-INF/classes/config/project-cfg.xml | awk -F\'CLIENT_ID>\' \'{print $2}\' | sed \'s/<\///\'"%CHKJAVADIR)
        str = self.execCmd("sed -n \"/^%s/p\" %s/weblist"%(sid.strip("\n"),CHKJAVADIR))
        if str == "":
            print "本纵向接口服务ID[%s]重复或者数据库未配置服务，请重新配置"%sid
            self.rmCheckJavaDir()
            exit(1)
        else:
            self.execCmd("sed -i \"/^%s/d\" %s/weblist"%(sid.strip("\n"),CHKJAVADIR))
            print "本机配置文件检查完成...ok, 开始检查其他服务器！"
            #self.downloadFile(localDir,remoteDir+"/weblist")
    #获取9001端口的所以ip
    def getAllConnectIp(self):
        iplist=[]
        lines = self.execCmd("netstat -anp | grep 9001 | grep -v LISTEN | grep cbs | grep ESTABLISHED | awk -F' ' '{print $5}'")
        if lines == -1:
            return iplist
        lines=lines.splitlines(False)
        for line in lines:
            ip=self.execCmd("echo %s | awk -F':' '{print $1}'"%line)
            port=self.execCmd("echo %s | awk -F':' '{print $2}'"%line)
            ret=self.isLocalHost(ip.strip("\n"))
            if ret == True:
                print "ip=%s 为本机地址,检查下一个服务器..."%ip
                continue
            iplist.append(ip.splitlines(False))
        return iplist
    #发送需要的检查脚本
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

    def checkServerId(self):
        global ORG_CODE
        global VIRIP
        global DBVIRIP
        ret=self.execCmd("sh %s/checkJava.sh %s %s %s %s"%(CHKJAVADIR,CHKJAVADIR,ORG_CODE,VIRIP,DBVIRIP))
        if str ==-1:
            print "通信前置服务器[$ip]检查配置文件出现错误，根据提示修改后重新执行检查脚本！"%self.hostname
            exit(1)
        self.checkInterServerId()
        self.rmCheckJavaDir()
        pass


class DBServer(baseConnect):
    '''数据库服务'''
    dirFlag=False
    def __int__(self,hostname,port,username,password):
        baseConnect.__init__(self,hostname,port,username,password)
        self.execCmd("source /etc/profile")
        self.dirFlag=False

    def mkdirCheckDBDir(self):
        if self.dirFlag==False:
            ret = self.execCmd("mkdir -p %s"%CHKDBDIR)
            if ret == "":
                print "数据库服务临时目录成功"
            self.dirFlag=True
            return ret

    def rmCheckDBDir(self):
        if self.dirFlag==True:
            ret = self.execCmd("rm -rf %s"%CHKDBDIR)
            self.dirFlag = False

    def getBackDBIp(self):
        path=self.execCmd("source /etc/profile && echo $APP_ROOT")
        if path == -1:
            return ""
        path=path.strip("\n")
        ret=self.execCmd("sed -n '4p' %s/sgrdb/data8336/master.info"%path)
        if ret == -1:
            exit(1)
        if ret == "":
            print "数据库主从没有做好,请重新建立主从"
            return False
        print "数据库从IP地址:%s"%ret
        ret = ret.strip("\n")
        return ret

    def sendCheckSyncBinToCheckDBDir(self):
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
        print "run check_sync_status.bin \n %s"%ret
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

    def shCheckDbShFromCheckDBDir(self,virip):
        ret = self.execCmd("ls -l %s/checkDB.sh" % CHKDBDIR)
        if ret == -1:
            return ret
        ret=self.execCmd("sh %s/checkDB.sh %s"%(CHKDBDIR,virip))
        print "run checkDB.sh \n %s" % ret
        return ret

    def getDBVirtualIp(self):
        ret=self.execCmd("sed -n '/virtual_ipaddress/{n;p}' /etc/keepalived/keepalived.conf | awk -F'/' '{print $1}'")
        if ret == "":
            print "get virtual ip failed"
            return False
        print "数据库服务器虚拟IP地址:%s"%ret
        return ret

    def isVirIpEqDbIp(self,virIp,dbIp):
        ret=self.execCmd("echo %s | grep %s"%virIp,dbIp)
        if ret == "":
            print "/opt/HMS/database.conf必须填写数据库的虚拟IP地址"
            exit(1)
        return True

    def backHostCheck(self):
        ret = self.execCmd("sed -n '/sgrdb\/backup.sh/p' /etc/crontab" )
        if ret != -1:
            print "备机不需要执行备份任务"
            exit(1)
        ret = self.execCmd("sed -n '/sgrdb\/setmaster.sh/p' /etc/crontab")
        if ret != -1:
            print "备机不需要执行I6000定时任务"
            exit(1)

    def masterHostCheck(self):
        ret = self.execCmd("sed -n '/sgrdb\/backup.sh/p' /etc/crontab" )
        if ret == -1:
            print "主机需要执行备份任务！"
            exit(1)
        ret = self.execCmd("sed -n '/sgrdb\/setmaster.sh/p' /etc/crontab")
        if ret != -1:
            print "主机需要执行I6000定时任务！"
            exit(1)

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
    '''存储服务'''
    def __int__(self,hostname,port,username,password):
        baseConnect.__init__(self,hostname,port,username,password)
    def mkdirCheckDCSDir(self):
        ret = self.execCmd("mkdir -p %s"%CHKDCSDIR)
        if ret == "":
            print "存储服务临时目录成功"
        return ret

    def rmCheckDCSDir(self):
        ret = self.execCmd("rm -rf %s"%CHKDCSDIR)
    #发送需要的检查脚本
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
        sid = self.execCmd("echo %s | awk -F'ServerId>' '{print $2}' | sed 's/<\///'"%sid)
        str=self.execCmd("sed -n \"/^%s/p\" %s/dcslist"%(sid.strip("\n"),CHKDCSDIR))
        if str ==-1:
            print "前置机[%s]服务ID[%s]重复或者数据库未配置服务，请重新配置"%(self.hostname,sid.strip("\n"))
            exit(1)
        global ORG_CODE
        global VIRIP
        global DBVIRIP
        ret=self.execCmd("sh %s/checkDCS.sh %s %s %s %s"%(CHKDCSDIR,CHKDCSDIR,ORG_CODE,VIRIP,DBVIRIP))
        if str ==-1:
            print "通信前置服务器[$ip]检查配置文件出现错误，根据提示修改后重新执行检查脚本！"%self.hostname
            exit(1)

        self.rmCheckDCSDir()
        pass

class CommFrontServer(baseConnect):
    '''通信前置机服务'''
    def __int__(self, hostname, port, username, password):
        baseConnect.__init__(self, hostname, port, username, password)

    def mkdirCheckDASDir(self):
        ret = self.execCmd("mkdir -p %s"%CHKDASDIR)
        if ret == "":
            print "前置机服务临时目录成功"
        return ret

    def rmCheckDASDir(self):
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
        sid = self.execCmd("echo %s | awk -F'ServerId>' '{print $2}' | sed 's/<\///'"%sid)
        str=self.execCmd("sed -n \"/^%s/p\" %s/daslist"%(sid.strip("\n"),CHKDASDIR))
        if str ==-1:
            print "前置机[%s]服务ID[%s]重复或者数据库未配置服务，请重新配置"%(self.hostname,sid.strip("\n"))
            exit(1)
        global ORG_CODE
        global VIRIP
        global DBVIRIP
        ret=self.execCmd("sh %s/checkDAS.sh %s %s %s %s"%(CHKDASDIR,CHKDASDIR,ORG_CODE,VIRIP,DBVIRIP))
        if str ==-1:
            print "通信前置服务器[$ip]检查配置文件出现错误，根据提示修改后重新执行检查脚本！"%self.hostname
            exit(1)

        self.rmCheckDASDir()
        pass


def ReadUserAndPwd():
    fp = open("user", 'r')
    usrInfo={}
    while 1:
        line = fp.readline()
        if not line:
            break
        num=len(line)
        if line[0] == '[' and line[num-1] == ']':
             continue
        userpwd=UserPwd()
        i=line.find(":")
        j = line.find(" ",i+1)
        k = line.find(" ",j+1)
        userpwd.ip=line[0:i]
        userpwd.port=line[i+1:j]
        userpwd.username=line[j+1:k]
        userpwd.pwd=line[k+1:-1]
        usrInfo[userpwd.ip]=userpwd
    return usrInfo

def GetInterfaceInfo():
    ip = raw_input("纵向接口服务ip:")
    ret=checkip(ip)
    if re == False:
        print "输入ip错误"
        exit(1)
    port = raw_input("纵向接口服务port:")
    if port == 0:
        port=16002
    user = raw_input("纵向接口服务用户名:")
    pwd = raw_input("纵向接口服务密码:")
    # ip="192.168.2.72"
    # port=22
    # user="root"
    # pwd="123456"
    return ip,port,user,pwd

#前置机
def dlbDealProcess(hostname,port,username,password):
    dlbServer=CommFrontServer(hostname,port,username,password)
    if None == dlbServer:
        pass
    dlbServer.sendNeedFile()
    dlbServer.checkServerId()
    pass
#存储服务器
def dcsDealProcess(hostname,port,username,password):
    dcsServer=DataStorageServer(hostname,port,username,password)
    if None == dcsServer:
        pass
    dcsServer.sendNeedFile()
    dcsServer.checkServerId()
    pass

#接口服务器
def javaDealProcess(hostname,port,username,password):
    javaServer=InterfaceServer(hostname,port,username,password)
    if None == javaServer:
        pass
    javaServer.sendNeedFile()
    javaServer.checkServerId()
    pass



def dealProcess():
    logger.info("dealProcess....")
    usersInfo = ReadUserAndPwd()
    hostname,port,username,password = GetInterfaceInfo()
    interServer = InterfaceServer(hostname,int(port),username,password)
    if interServer ==None:
        logger.error("创建interServer 失败 ")
        exit(1)
    virIp=interServer.getVirtualAddress()
    interServer.isCBSRunning()
    virDBIpList=interServer.getDBVirtualAddress()
    if len(virDBIpList) == 0:
        exit(1)
    virDBIp=virDBIpList[0]
    virDBIpInfo = usersInfo.get(virDBIp)
    if None == virDBIpInfo:
        print "未找到数据库虚拟ip对应的用户密码"
        exit(1)
    virDBServer= DBServer(virDBIpInfo.ip,int(virDBIpInfo.port),virDBIpInfo.username,virDBIpInfo.pwd)
    if None == virDBServer:
        exit(1)
    backDBIp=virDBServer.getBackDBIp()
    virDBServer.mkdirCheckDBDir()
    virDBServer.sendCheckSyncBinToCheckDBDir()
    virDBServer.sendCheckDbShToCheckDBDir()
    virDBServer.shCheckSyncBinFromCheckDBDir()
    virDBServer.shCheckDbShFromCheckDBDir(virDBIp)
    virDBServer.getServerList()
    virDBServer.rmCheckDBDir()

    backDBIpInfo = usersInfo.get(backDBIp)
    if None == backDBIpInfo:
        print "未找到数据库back ip对应的用户密码"
        exit(1)
    backDBServer = DBServer(backDBIpInfo.ip, int(backDBIpInfo.port), backDBIpInfo.username, backDBIpInfo.pwd)
    if None == backDBServer:
        exit(1)
    backDBServer.sendCheckDbShToCheckDBDir()
    backDBServer.shCheckDbShFromCheckDBDir(virDBIp)
    backDBServer.rmCheckDBDir()
    #disconnect db
    virDBServer.disConnect()
    backDBServer.disConnect()

    #interServer.checkInterServerId()
    global VIRIP
    global DBVIRIP
    VIRIP=virIp[0]
    DBVIRIP=virDBIp
    All9001Ip=interServer.getAllConnectIp()
    if len(All9001Ip) ==0:
        print "纵向接口服务获取不到任何其它9001ip"
        exit(1)

    for ip in All9001Ip:
        info=usersInfo.get(ip[0])
        if None==info:
            continue
        basecon=baseConnect(info.ip,int(info.port), info.username,info.pwd)
        if None == basecon:
            print "ssh连接ip[%s]失败"
            exit(1)
        typeName=basecon.localHostType()
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
            print "未知服务器 ip:%s"%info.ip
            pass
        pass



if __name__ == "__main__":

    fp=open("./orgCode",'r')
    if fp ==None:
        print "open file ./orgCode failed"
    content=fp.read()
    print content.decode('utf8').encode('gb2312')
    inputstr = raw_input("请输入网省公司名字:")
    index=content.find(inputstr)
    pos=index+len(inputstr)+2
    ORG_CODE=content[pos:pos+2]
    #ORG_CODE="18"
    dealProcess()
    time.sleep(5)
