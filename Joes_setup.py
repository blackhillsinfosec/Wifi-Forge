import os

#need to change the config file to trust the submodule
os.system("git config --global --add safe.directory $(pwd)")

os.system("echo $(pwd)")
os.system("git submodule init")
os.system("git submodule update") 


os.system("sudo mininet-wifi/util/install.sh -Wlnfv")

os.system("sudo apt install mininet")

cwd = os.getcwd() + "/../mininet-wifi"
print(cwd)
os.chdir(cwd)

os.system("sudo make install")

os.system("sudo apt install openvswitch-testcontroller")
os.system("sudo ln /usr/bin/ovs-testcontroller /usr/bin/controller")
