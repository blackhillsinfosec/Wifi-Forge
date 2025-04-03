#!/bin/bash

# Disable immediate exit so we can handle errors properly
set +e

# Color codes for formatting
RED='\033[91m'
GREEN='\033[92m'
MAGENTA='\033[35m'
CYAN='\033[36m'
RESET='\033[0m'

# Get current working directory
cwd=$(pwd)

# Format the string to only include the path to the repo's main file
index=$(echo "$cwd" | awk -F'/MiniNet-framework' '{print length($1)+length("/MiniNet-framework")}')
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

    wait $pid
    exit_code=$?
    if [ $exit_code -ne 0 ]; then
        echo -e "\r[${RED}✖${RESET}] $message (Failed)"
    else
        echo -e "\r[${GREEN}✔${RESET}] $message    "
    fi
}

# Run a command with error detection
run_command() {
    ($1 > /dev/null 2>&1) &
    local pid=$!
    echo_spinner $pid "$2"
}

# Adding Submodules to safe.directory
run_command "git config --global --add safe.directory \"$truncated_cwd\"" "Adding Submodules to safe.directory..."

# Initialize Submodules
run_command "git submodule init" "Initializing Submodules..."

# Update Submodules
run_command "git submodule update" "Updating Submodules..."

# Set global pip variable to break system packages
run_command "sudo -E python3 -m pip config set global.break-system-packages true" "Configuring pip..."

# Install Kali Tools
run_command "sudo apt update -y" "Updating package list..."
run_command "sudo apt install -y ifupdown pip curl aircrack-ng john dsniff tmux" "Installing required tools..."

# Install Mininet
run_command "sudo apt install -y mininet --allow-downgrades" "Installing Mininet..."

# Run Install Script
run_command "../mininet-wifi/util/install.sh -Wlnf" "Running Install Script..."

# Compile
run_command "sudo make install" "Compiling..."

echo -e "WifiForge Finished Installing!"
