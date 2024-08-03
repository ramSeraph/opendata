#!/bin/bash

apt update
apt install -y --no-install-recommends unzip wget jq
cd /
wget https://github.com/jthomperoo/simple-proxy/releases/download/v1.2.0/simple-proxy_linux_amd64.zip
unzip simple-proxy_linux_amd64.zip
chmod a+x simple-proxy

nohup ./simple-proxy -port 80 -logtostderr -v -2 &
