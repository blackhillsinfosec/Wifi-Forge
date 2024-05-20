import os

RED = "\033[91m"
GREEN = "\033[92m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
RESET = "\033[0m"

#need to change the config file to trust the submodule
supress = ">/dev/null 2>&1"

print(f"[{GREEN}+{RESET}] Adding Submodules to safe.directory...")
os.system("git config --global --add safe.directory $(pwd)" + supress)

print(f"[{GREEN}+{RESET}] Initializating Submodules...")
os.system("git submodule init" + supress)

os.system("git submodule update" + supress)

print(f"[{GREEN}+{RESET}] Running Install Script...")
os.system("sudo mininet-wifi/util/install.sh -Wlnfv" + supress)

print(f"[{GREEN}+{RESET}] Installing Mininet...")
os.system("sudo apt install -y mininet" + supress)

cwd = os.getcwd() + "/../mininet-wifi"

try:
	os.chdir(cwd)
except:
	print(f"[{RED}!{RESET}] Directory Error! Was mininet-wifi successfully deployed?...")
	exit()

print(f"[{GREEN}+{RESET}] Compiling...")
os.system("sudo make install" + supress)

print(f"[{GREEN}+{RESET}] Installing openvswitch-testcontroller...")
os.system("sudo apt install openvswitch-testcontroller" + supress)

os.system("sudo ln /usr/bin/ovs-testcontroller /usr/bin/controller" + supress)
