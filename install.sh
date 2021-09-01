#!/bin/bash

# Setting Timezone
DEBIAN_FRONTEND=noninteractive apt-get install -y tzdata

pip3 install -r requirements.txt 2>&1
[[ $? -eq 1 ]] && echo "[Error] Failed to install orbis dependencies." && exit 1 ;

pip3 install . 2>&1
[[ $? -eq 1 ]] && echo "[Error] Failed to install orbis." && exit 1 ;

#Configs
config_path="/etc/orbis"
config_plugin_path="/etc/orbis/plugins.d"
plugins_path="/var/lib/orbis/plugins/tool"

mkdir -p $config_path && cp "config/orbis.yml" $config_path
mkdir -p $config_plugin_path && mkdir -p $plugins_path && cp -a "orbis/plugins/." $plugins_path
[[ $? -eq 1 ]] && echo "[Error] Failed to install orbis configs." && exit 1 ;
