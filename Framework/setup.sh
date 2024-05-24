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
supress="> /dev/null 2>&1"

# Adding Submodules to safe.directory
echo -e "[${GREEN}+${RESET}] Adding Submodules to safe.directory..."
git config --global --add safe.directory "$truncated_cwd" $supress

# Initialize Submodules
echo -e "[${GREEN}+${RESET}] Initializing Submodules..."
git submodule init $supress

# Update Submodules
git submodule update $supress

# Install Kali Tools
echo -e "[${GREEN}+${RESET}] Installing Kali Tools..."
sudo apt install curl -y $supress
sudo ./dependencies.sh $supress
sudo apt install aircrack-ng -y $supress
sudo apt install john -y $supress
sudo apt install eaphammer -y $supress
sudo apt install dsniff -y $supress


# Install Mininet
echo -e "[${GREEN}+${RESET}] Installing Mininet..."
sudo apt install mininet -y --allow-downgrades $supress

# Move to mininet-wifi directory
cd "$cwd/mininet-wifi"

# Run Install Script
echo -e "[${GREEN}+${RESET}] Running Install Script..."
./util/install.sh -Wlnfv $supress

# Compile
echo -e "[${GREEN}+${RESET}] Compiling..."
sudo make install $supress

# Install openvswitch-testcontroller
echo -e "[${GREEN}+${RESET}] Installing openvswitch-testcontroller..."
sudo apt install openvswitch-testcontroller -y $supress
sudo ln /usr/bin/ovs-testcontroller /usr/bin/controller $supress

