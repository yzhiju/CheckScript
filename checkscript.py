#!/usr/bin/env python
# -*- coding: utf-8 -*-

import paramiko
from scpclient import *
from contextlib import closing
import time
import re
#纵向接口目录
CHKJAVADIR="/tmp/checkJava"
#前置机临时目录
CHKDASDIR="/tmp/checkDAS"
#存储服务临时目录
CHKDCSDIR="/tmp/checkDCS"
#数据库服务临时目录
CHKDBDIR="/tmp/checkDB"

class UserPwd:
    def __init__(self):
        self.ip=""
        self.port=16002
        self.pwd=""

class baseConnect():
    def __init__(self,hostname,port,username,password):
        self.hostname=hostname
        self.port=port
        self.username=username
        self.password=password
        self.connect()

    def connect(self):
        paramiko.util.log_to_file("paramiko.log")
        self.con = paramiko.SSHClient()
        self.con.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            self.con.connect(hostname=self.hostname, port=self.port, username=self.username, password=self.password)
        except :#paramiko.ssh_exception,e
             print "%s connect failed!"%self.hostname
             exit(1)
        print "connect %s:%s success"%(self.hostname,self.port)

    def disConnect(self):
        self.con.close()

    def execCmd(self,cmd):
        stdin, stdout, stderr = self.con.exec_command(cmd)
        stdin.write("Y")
        str = stdout.read()
        if str!='':
            return  str
        else:
            strErr = stderr.read()
            print strErr
            return -1

    # def uploadAndExecu(self,localDir,remoteDir):
    #     print "upload file local dir:%s remote dir:%s remote hostname:%s,port:%d,"%localDir,\
    #         remoteDir,self.hostname,self.port
    #     try:
    #         t = paramiko.Transport((self.hostname, int(self.port)))
    #         t.connect(username=self.username, password=self.password)
    #         sftp = paramiko.SFTPClient.from_transport(t)
    #         ret=sftp.put(localDir, remoteDir)
    #     except Exception, e:
    #         print 'upload files failed:', e
    #         t.close()
    #     finally:
    #         t.close()
    #     return ret

    def uploadFile(self,localPath,remotePath):
        '''上传到服务器指定文件'''
        sshclient = paramiko.SSHClient()
        sshclient.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        sshclient.connect(hostname=self.hostname, port=self.port, username=self.username, password=self.password)
        with closing(Write(sshclient.get_transport(), remotePath)) as scp:
            scp.send_file(localPath, True)

    def downloadFile(self,localPath,remotePath):
        '''从服务器中获取文件'''
        sshclient = paramiko.SSHClient()
        sshclient.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        sshclient.connect(hostname=self.hostname, port=self.port, username=self.username, password=self.password)
        with closing(Read(sshclient.get_transport(), remotePath)) as scp:
            scp.receive(localPath)

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
        name1 = self.execCmd("netstat -anp | grep $port | grep ESTABLISHED")
        name = self.execCmd("echo \"%s\" | awk -F' ' '{print $7}' | awk -F'/' '{print $NF}'"%name1)
        if name =="":
            print "未知服务器[%s]"%self.hostname
            exit(1)
        elif name == "dlb":
            print "服务器[%s]为通信前置机"%self.hostname
            sid=self.execCmd("sed -n '/<ServerId>/p' /opt/HMS/DLB/DLB.xml")
            sid = self.execCmd("echo %s | awk -F'ServerId>' '{print $2}' | sed 's/<\///'"%sid)
            str=self.execCmd("sed -n \"/^%s/p\" $TMPDIR/daslist"%sid)
            if str == "":
                print "前置机[%s]服务ID[$SID]重复或者数据库未配置服务，请重新配置"%self.hostname
                exit(1)

        elif name == "dcs":
            print "服务器[%s]为存储服务器" % self.hostname
            sid=self.execCmd("sed -n '/<ServerId>/p' /opt/HMS/DCS/DCS.xml")
            sid = self.execCmd("echo %s | awk -F'ServerId>' '{print $2}' | sed 's/<\///'"%sid)
            str=self.execCmd("sed -n \"/^%s/p\" $TMPDIR/dcslist"%sid)
            if str == "":
                print "存储服务[%s]服务ID[%s]重复或者数据库未配置服务，请重新配置"%self.hostname,sid
                exit(1)

        elif name == "java":
            print "服务器[%s]为纵向接口服务器" % self.hostname



class InterfaceServer(baseConnect):
    def __init__(self,hostname,port,username,password):
        baseConnect.__init__(self,hostname,port,username,password)

    def masterAndSlaveIsNomal(self):
        '''判断主从服务'''
        ret=self.execCmd("sed -n \'/virtual_ipaddress/{n;p}\' /etc/keepalived/keepalived.conf | awk -F\'/\' \'{print $1}\'")
        if ret == -1:
            exit(1)

    def isCBSRunning(self):
        '''判断cbs服务是否运行'''
        ret=self.execCmd("ps -ef | grep cbs | grep -v grep")
        if ret == -1:
            exit(1)
        if ret == "":
            print "cbs服务没有运行！"
            return False
        return True


    def getDBVirtualAddress(self):
        '''获取数据库虚拟地址'''
        ret = self.execCmd("netstat -anp | grep cbs | grep 8336 | grep ESTABLISHED | awk -F' ' '{print $5}'|awk -F':' '{print $1}")
        if ret == -1:
            exit(1)
        if ret == "":
            print "获取数据库地址失败"
            return False
        print "数据库的虚拟IP地址为%s"%ret
        return ret


    #获取9001端口的所以ip
    def getAllConnectIp(self):
        iplist=[]
        lines = self.execCmd("netstat -anp | grep 9001 | grep -v LISTEN | grep cbs | grep ESTABLISHED | awk -F' ' '{print $5}'")
        if lines == -1:
            return iplist
        for line in lines:
            ip=self.execCmd("echo %s | awk -F':' '{print $1}'"%line)
            port=self.execCmd("echo %s | awk -F':' '{print $2}'"%line)
            ret=self.isLocalHost(ip)
            if ret == True:
                print "ip=%s 为本机地址,检查下一个服务器..."%ip
                continue
            iplist.append(line)
        return iplist


class DBServer(baseConnect):
    '''数据库服务'''
    def __int__(self,hostname,port,username,password):
        baseConnect.__init__(self,hostname,port,username,password)
        self.execCmd("source /etc/profile")

    def mkdirCheckDBDir(self):
        ret = self.execCmd("mkdir -p %s"%CHKDBDIR)
        if ret == "":
            print "数据库服务临时目录成功"
        return ret

    def rmCheckDBDir(self):
        ret = self.execCmd("rm - rf %s"%CHKDBDIR)

    def getBackDBIp(self):
        ret=self.execCmd("sed -n '4p' $APP_ROOT/sgrdb/data8336/master.info")
        if ret == -1:
            exit(1)
        if ret == "":
            print "数据库主从没有做好,请重新建立主从"
            return False
        print "数据库从IP地址:%s"%ret
        return ret


    # SCPFILETODEST $ssh_port $user_name $DBVIRIP $TMPDIR / check_sync_status.bin $CHKDBDIR
    # ssh - p $ssh_port $user_name @$DBVIRIP
    # "sh $CHKDBDIR/check_sync_status.bin" | | echo
    # "数据库主从同步失败" & & ssh - p $ssh_port $user_name @$DBVIRIP
    # "rm -rf $CHKDBDIR" & & exit
    # 1
    # ssh - p $ssh_port $user_name @$DBVIRIP
    # "sh $CHKDBDIR/checkDB.sh $DBVIRIP" | | echo
    # "/opt/HMS/database.conf文件数据库地址必须填写数据库虚拟IP地址" & & ssh - p $ssh_port $user_name @$DBVIRIP
    # "rm -rf $CHKDBDIR" & & exit
    # 1
    def sendCheckSyncBinToCheckDBDir(self):
        localDir="./check_sync_status.bin"
        remoteDir=CHKDBDIR
        ret=self.uploadAndExecu(localDir,remoteDir)
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
    def getServerList(self):
        ret = self.execCmd("sgrdb -h127.0.0.1 -p8336 -umysql -p~Mysql2016pwd! --skip-column hdms "
                           "-e \"select serverid from servers where type=103\"> %s"%(CHKDBDIR+"/daslist"))
        ret = self.execCmd("sgrdb -h127.0.0.1 -p8336 -umysql -p~Mysql2016pwd! --skip-column hdms "
                           "-e \"select serverid from servers where type=104\"> %s"%(CHKDBDIR+"/dcslist"))
        ret = self.execCmd("sgrdb -h127.0.0.1 -p8336 -umysql -p~Mysql2016pwd! --skip-column hdms "
                           "-e \"select serverid from servers where type=105\"> %s"%(CHKDBDIR+"/weblist"))


class DataStorageServer(baseConnect):
    def __int__(self,hostname,port,username,password):
        baseConnect.__init__(self,hostname,port,username,password)


class CommFrontServer(baseConnect):
    '''通信前置机服务'''
    def __int__(self, hostname, port, username, password):
        baseConnect.__init__(self, hostname, port, username, password)


def checkip(ip):
    p = re.compile('^((25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(25[0-5]|2[0-4]\d|[01]?\d\d?)$')
    if p.match(ip):
        return True
    else:
        return False

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
        j = line.find(" ")
        userpwd.ip=line[0:i]
        userpwd.port=line[i:j]
        userpwd.pwd=line[j:-1]
        usrInfo[userpwd.ip]=userpwd
    return usrInfo

def GetInterfaceInfo():
    # ip = raw_input("纵向接口服务ip:")
    # ret=checkip(ip)
    # if re == False:
    #     print "输入ip错误"
    #     exit(1)
    # port = raw_input("纵向接口服务port:")
    # if port == 0:
    #     port=16002
    # user = raw_input("纵向接口服务用户名:")
    # pwd = raw_input("纵向接口服务密码:")
    ip="192.168.3.210"
    port=22
    user="yangzhiju"
    pwd="123456"
    return ip,port,user,pwd



'''
def sshclient_execmd(hostname, port, username, password, execmd):
    paramiko.util.log_to_file("paramiko.log")
    s = paramiko.SSHClient()
    s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    s.connect(hostname=hostname, port=port, username=username, password=password)
    stdin, stdout, stderr = s.exec_command("free")
    stdin.write("Y")
    str = stdout.read()
    print str
    fp = open("pyssh.log", 'w')
    fp.write("这就是一行测试\n")
    fp.write(str.decode(encoding="utf-8"))
    fp.close()
    stdin, stdout, stderr = s.exec_command("pwd")
    stdin.write("Y")  # Generally speaking, the first connection, need a simple interaction.
    str = stdout.read()
    print str
    stdin, stdout, stderr = s.exec_command("mkdir test")
    stdin.write("Y")  # Generally speaking, the first connection, need a simple interaction.
    str = stdout.read()
    print "result:"+str
    if str == "":
        print "ok"
    str = stderr.read()
    print "result2:"+str
    s.close()

'''
def main():
    hostname = "192.168.2.210"
    port = 22
    username = "yangzhiju"
    password = "123456"
    execmd = "free"
    print("%s:%d" % (hostname, port))
    #sshclient_execmd(hostname, port, username, password, execmd)
    interServer=InterfaceServer(hostname,port,username,password)
    return interServer

def dealProcess():
    usersInfo = ReadUserAndPwd()
    hostname,port,username,password = GetInterfaceInfo()
    interServer = InterfaceServer(hostname,port,username,password)
    All9001Ip=interServer.getAllConnectIp()
    if len(All9001Ip) ==0:
        print "纵向接口服务获取不到任何9001ip"
        exit(1)
    for ip in All9001Ip:
        #usersInfo.
        pass






if __name__ == "__main__":
   # main()
   dealProcess()
   time.sleep(5)
