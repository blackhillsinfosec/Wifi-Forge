import os

#need to change the config file to trust the submodule
os.system("git config --global --add safe.directory /home/ubuntu/MiniNet-Framework/mininet-wifi")

os.system("git submodule init")
os.system("git submodule update") 


os.system("sudo mininet-wifi/util/install.sh -Wlnfv")

os.system("sudo apt install mininet")

os.system("sudo make install")

os.system("sudo apt install openvswitch-testcontroller")
os.system("sudo ln /usr/bin/ovs-testcontroller /usr/bin/controller")
