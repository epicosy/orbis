#!/bin/bash

pip3 install -r requirements.txt
[[ $? -eq 1 ]] && echo "[Error] Failed to install orbis dependencies." && exit 1 ;

pip3 install setup.py
[[ $? -eq 1 ]] && echo "[Error] Failed to install orbis." && exit 1 ;

#Configs
config_path="/etc/orbis"
config_plugin_path="/etc/orbis/plugin"
mkdir -p $config_path && cp "config/orbis.yml" $config_path && mkdir -p $config_plugin_path
[[ $? -eq 1 ]] && echo "[Error] Failed to install synapser configs." && exit 1 ;
