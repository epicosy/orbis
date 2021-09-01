#!/bin/bash

# Setting Timezone
DEBIAN_FRONTEND=noninteractive apt-get install -y tzdata

apt-get update
apt install -y software-properties-common
add-apt-repository ppa:deadsnakes/ppa -y

# Install Python 3.8.10
apt install -y python3.8
[[ $? -eq 1 ]] && echo "[Error] Failed to install Python 3.8.10" && exit 1 ;

# Set default version of Python 3 to 3.8.10
update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.8 2
[[ $? -eq 1 ]] && echo "[Error] Failed to set default version of Python 3 to 3.8.10" && exit 1 ;

# Install pip for Python 3.8
apt-get install -y python3-distutils python3.8-dev 2>&1
curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
[[ $? -eq 1 ]] && echo "[Error] Failed to download pip for Python 3" && exit 1 ;
python3 get-pip.py 2>&1
[[ $? -eq 1 ]] && echo "[Error] Failed to install pip for Python 3" && exit 1 ;
