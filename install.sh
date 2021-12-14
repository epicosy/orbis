#!/bin/bash

# Setting Timezone
DEBIAN_FRONTEND=noninteractive apt-get install -y tzdata

# Setup postgres
apt-get install -y postgresql libpq-dev
python3 -m pip install psycopg2

#sudo -u postgres -i
#/etc/init.d/postgresql start
#psql -U postgres --command "CREATE USER orbis WITH SUPERUSER PASSWORD 'orbis123';"
#createdb orbis
#exit

pip3 install -r requirements.txt 2>&1
[[ $? -eq 1 ]] && echo "[Error] Failed to install orbis dependencies." && exit 1 ;

pip3 install . 2>&1
[[ $? -eq 1 ]] && echo "[Error] Failed to install orbis." && exit 1 ;

#Configs
main_path="~/.orbis"
config_path=main_path + "/config"
config_plugin_path=config_path + "/plugins.d"
plugins_path=main_path + "/plugins"

mkdir -p $config_path && cp "config/orbis.yml" $config_path
mkdir -p $config_plugin_path && mkdir -p $plugins_path && cp -a "orbis/plugins/." $plugins_path
[[ $? -eq 1 ]] && echo "[Error] Failed to install orbis configs." && exit 1 ;
