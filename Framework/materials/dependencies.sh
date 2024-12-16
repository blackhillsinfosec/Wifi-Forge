#/bin/bash

#Remove previous kali.org repo
# Check if the sources.list file exists
if [ -f /etc/apt/sources.list ]; then
  # Create a backup of the file
  sudo cp /etc/apt/sources.list /etc/apt/sources.list.bak

  # Remove all lines containing "kali.org" from the file
  sudo grep -v "kali.org" /etc/apt/sources.list > /tmp/sources.list
  sudo mv /tmp/sources.list /etc/apt/sources.list
else
  echo "Error: /etc/apt/sources.list not found"
  exit
fi

sleep 5

if (( $EUID != 0 )); then
    echo "Please run as root"
    exit
fi

echo "deb http://http.kali.org/kali kali-rolling main contrib non-free" | sudo tee /etc/apt/sources.list
name=$(curl -s https://http.kali.org/kali/pool/main/k/kali-archive-keyring/ | grep "all.deb" | awk -F'[<>]' '{for (i=1; i<=NF; i++) print $i}' | grep "all.deb" | sed -n '2p')
wget https://http.kali.org/kali/pool/main/k/kali-archive-keyring/$name
sudo apt install ./$name
sudo apt update
rm $name
