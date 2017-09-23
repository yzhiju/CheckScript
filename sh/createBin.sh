
SCRIPT=install.sh
PACKET=packet.tar.bz2
BIN_NAME=chkconfig.bin
rm -f $BIN_NAME

tar cjf $PACKET * --exclude install.sh --exclude createBin.sh
cat $SCRIPT $PACKET > $BIN_NAME
rm -f $PACKET

chmod 777 $BIN_NAME
