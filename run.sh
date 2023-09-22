#!/bin/sh

SHARE_DIR=/share/SimpleServer

if [ ! -f $SHARE_DIR/server.py ]; then
	mkdir $SHARE_DIR
	mv /server.py $SHARE_DIR
    mv /client.py $SHARE_DIR
fi
/makeconf.sh

echo "[Info] Simple Server"
cd $SHARE_DIR
python3 $SHARE_DIR/server.py

# for dev
while true; do echo "still live"; sleep 100; done