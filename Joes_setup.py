import os

#need to change the config file to trust the submodule
os.system("git submodule init")

os.system(f"git config --global --add safe.directory /home/ubuntu/MiniNet-Framework/mininet-wifi")

os.system("cd mininet-wifi")

os.system("sudo util/install.sh -Wlnfv")

os.system("sudo apt install mininet")

os.system("sudo make install")

os.system("sudo apt install openvswitch-testcontroller")
os.system("sudo ln /usr/bin/ovs-testcontroller /usr/bin/controller")
