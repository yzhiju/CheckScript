

isLocalHost(){
        if [ "$1" = "127.0.0.1" ]; then
                return 1
        fi
        IPS=`LC_ALL=C ifconfig  | grep 'inet addr:'| grep -v '127.0.0.1' |cut -d: -f2 | awk '{ print $1}'`
        for tmp_ip in $IPS
        do
                if [ "$tmp_ip" = "$1" ]; then
                        return 1
                fi
        done

        return 0
}

##$1虚拟IP地址， $2端口,$3 url, $4 dstUrl,返回0表示成功，1-失败
isLocalHostUrl(){
     IPS=`LC_ALL=C ifconfig  | grep 'inet addr:'| grep -v '127.0.0.1'| grep -v "$1" |cut -d: -f2 | awk '{ print $1}'`
        for tmp_ip in $IPS
        do
                STR="http://$tmp_ip:$2/$3"
                if [ "$STR" = "$4" ]; then
                        return 0
                fi
        done

        return 1
}


isRunning(){
        STR=`ps -ef | grep $1 | grep -v grep`
        if [ ! -z "$STR" ]; then
            return 1
        fi
        return 0
}

printALLCode(){
        echo "网省公司列表:"
        cat $1 | while read CODE
        do
                STR=`echo "$CODE" | awk -F' ' '{print $1}'`
                echo "   $STR"
        done
}

findCode(){
    if [ -z "$2" ]; then
        return 1
    fi

    cat $1 | while read CODE
    do
        STR=`echo "$CODE" | awk -F' ' '{print $1}'`
        if [ "$STR" = "$2" ]; then
            STR=`echo "$CODE" | awk -F' ' '{print $2}'`
            echo "$STR"
        fi
    done
}

##usage srcport srcusername srchost srcFile dstDir
SCPFILETODEST()
{
	expect << EOF
	spawn scp -P $1 $4 $2@$3:$5
	expect {
		"password:" {send "$src_passwd\n";exp_continue}
		"yes/no*" {send "yes\n";exp_continue}
		eof {exit}
}
EOF
}

SCPFILEFROMDEST()
{
        expect << EOF
        spawn scp -P $1 $2@$3:$4 $5
        expect {
                "password:" {send "$src_passwd\n";exp_continue}
                "yes/no*" {send "yes\n";exp_continue}
                eof {exit}
}
EOF
}
