#!/bin/bash

cd /tmp
wget -O tests.tar.tz https://github.com/epicosy/cb-repair/raw/master/rep_pckg.tar.gz
tar -xvf tests.tar.tz
rm tests.tar.tz
cp -r tests/polls/* /usr/local/share/polls/
