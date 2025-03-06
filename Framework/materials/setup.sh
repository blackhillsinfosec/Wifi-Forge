#!/bin/bash

# Color codes for formatting
RED='\033[91m'
GREEN='\033[92m'
MAGENTA='\033[35m'
CYAN='\033[36m'
RESET='\033[0m'

# Get current working directory
cwd=$(pwd)

# Format the string to only include the path to the repo's main file
# The exact path is needed to add to the safe.repositories file
index=$(echo "$cwd" | awk -F'/MiniNet-Framework' '{print length($1)+length("/MiniNet-Framework")}')
truncated_cwd=$(echo "$cwd" | cut -c 1-"$index")

# Change the config file to trust the submodule

# Adding Submodules to safe.directory
echo -e "[${GREEN}+${RESET}] Adding Submodules to safe.directory..."
git config --global --add safe.directory "$truncated_cwd" > /dev/null 2>&1

# Initialize Submodules
echo -e "[${GREEN}+${RESET}] Initializing Submodules..."
git submodule init > /dev/null 2>&1

# Update Submodules
git submodule update > /dev/null 2>&1

#set global pip variable break system packages to true
sudo python3 -m pip config set global.break-system-packages true  > /dev/null 2>&1


# Install Kali Tools
echo -e "[${GREEN}+${RESET}] Installing Tools..."
sudo apt update -y > /dev/null 2>&1
sudo apt install pip -y > /dev/null 2>&1
sudo apt install curl -y > /dev/null 2>&1
sudo apt install aircrack-ng -y > /dev/null 2>&1
sudo apt install john -y > /dev/null 2>&1
sudo apt install dsniff -y > /dev/null 2>&1
sudo apt install tmux -y > /dev/null 2>&1
sudo pip install tqdm --break-system-packages > /dev/null 2>&1
sudo pip install keyboard --break-system-packages > /dev/null 2>&1
sudo pip install libtmux --break-system-packages > /dev/null 2>&1


# Install Mininet
echo -e "[${GREEN}+${RESET}] Installing Mininet..."
sudo apt install mininet -y --allow-downgrades > /dev/null 2>&1


# Run Install Script
echo -e "[${GREEN}+${RESET}] Running Install Script..."
../mininet-wifi/util/install.sh -Wlnf > /dev/null 2>&1

# Compile
echo -e "[${GREEN}+${RESET}] Compiling..."
sudo make install > /dev/null 2>&1

# Install openvswitch-testcontroller
echo -e "[${GREEN}+${RESET}] Installing openvswitch-testcontroller..."
sudo apt install openvswitch-testcontroller -y > /dev/null 2>&1
sudo ln /usr/bin/ovs-testcontroller /usr/bin/controller > /dev/null 2>&1
sudo service openvswitch-switch start  > /dev/null 2>&1
sudo cp ./main_menu /bin  > /dev/null 2>&1
