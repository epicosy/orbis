#!/bin/bash

# Setting frontend, apt-utils, and timezone
DEBIAN_FRONTEND=noninteractive apt-get install -y dialog apt-utils tzdata 2>&1

# Setup postgres
DEBIAN_FRONTEND=noninteractive apt-get install -y postgresql libpq-dev
python3 -m pip install psycopg2 2>&1
[[ $? -eq 1 ]] && echo "[Error] Failed to install postgres." && exit 1 ;


su - postgres -c "/etc/init.d/postgresql start && psql -U postgres -c \"CREATE USER orbis WITH SUPERUSER PASSWORD 'orbis123';\""
[[ $? -eq 1 ]] && echo "[Error] Failed to create user role." && exit 1 ;

echo "[Success] Created psql user"

pip3 install -r requirements.txt 2>&1
[[ $? -eq 1 ]] && echo "[Error] Failed to install orbis dependencies." && exit 1 ;

echo "[Success] Installed dependencies."

pip3 install . 2>&1
[[ $? -eq 1 ]] && echo "[Error] Failed to install orbis." && exit 1 ;

echo "[Success] Installed orbis."

mkdir -p ~/.orbis/config/plugins.d && mkdir -p ~/.orbis/plugins && cp config/orbis.yml ~/.orbis/config/
[[ $? -eq 1 ]] && echo "[Error] Failed to install orbis configs." && exit 1 ;

echo "[Success] Created default configuration file paths."

orbis plugin install -d $ORBIS_PLUGIN_PATH 2>&1
[[ $? -eq 1 ]] && echo "[Error] Failed to install plugin." && exit 1 ;