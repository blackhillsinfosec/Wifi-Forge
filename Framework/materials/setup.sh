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

# Function for animated spinner
echo_spinner() {
    local pid=$1
    local message=$2
    local symbols=("+" "x")
    echo -ne "[${GREEN}+${RESET}] $message"
    while kill -0 $pid 2>/dev/null; do
        for symbol in "${symbols[@]}"; do
            echo -ne "\r[${GREEN}${symbol}${RESET}] $message"
            sleep 0.5
        done
    done
    echo -e "\r[${GREEN}✔${RESET}] $message    "
}

# Adding Submodules to safe.directory
(git config --global --add safe.directory "$truncated_cwd" > /dev/null 2>&1) &
echo_spinner $! "Adding Submodules to safe.directory..."

# Initialize Submodules
(git submodule init > /dev/null 2>&1) &
echo_spinner $! "Initializing Submodules..."

# Update Submodules
(git submodule update > /dev/null 2>&1) &
echo_spinner $! "Updating Submodules..."

# Set global pip variable to break system packages
(sudo -E python3 -m pip config set global.break-system-packages true > /dev/null 2>&1) &
echo_spinner $! "Configuring pip..."

# Install Kali Tools
(sudo apt update -y > /dev/null 2>&1) &
echo_spinner $! "Updating package list..."

(sudo apt install -y ifupdown pip curl aircrack-ng john dsniff tmux > /dev/null 2>&1) &
echo_spinner $! "Installing required tools..."

# Install Mininet
(sudo apt install -y mininet --allow-downgrades > /dev/null 2>&1) &
echo_spinner $! "Installing Mininet..."

# Run Install Script
(../mininet-wifi/util/install.sh -Wlnf > /dev/null 2>&1) &
echo_spinner $! "Running Install Script..."

# Compile
(sudo make install > /dev/null 2>&1) &
echo_spinner $! "Compiling..."