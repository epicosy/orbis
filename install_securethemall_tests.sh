#!/bin/bash

cd /tmp
wget https://github.com/SecureThemAll/cb-repair/raw/master/rep_pckg.tar.gz -O tests.tar.gz
tar -xvf tests.tar.gz
rm tests.tar.gz
cp -r rep_pckg/polls/* /usr/local/share/polls/
