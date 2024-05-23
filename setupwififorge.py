import os

RED = "\033[91m"
GREEN = "\033[92m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
RESET = "\033[0m"

cwd = os.getcwd()


if "/Framework" in cwd:
        cwd += "/../mininet-wifi"
else:
        cwd += "/mininet-wifi"


#need to change the config file to trust the submodule
supress = ">/dev/null"
print(f"{cwd}")
print(f"git config --global --add safe.directory {cwd}/../../MiniNet-Framework")
print(f"[{GREEN}+{RESET}] Adding Submodules to safe.directory...")
os.system(f"git config --global --add safe.directory {cwd}/../../MiniNet-Framework" + supress)

print(f"[{GREEN}+{RESET}] Initializating Submodules...")
os.system("git submodule init" + supress)

os.system("git submodule update" + supress)
'''
print(f"[{GREEN}+{RESET}] Installing Kali Tools...")
os.system("sudo apt install curl -y" + supress)
os.system("sudo ./dependencies.sh" + supress)
os.system("sudo apt install aircrack-ng -y" + supress)
os.system("sudo apt install john -y" + supress)
os.system("sudo apt install eaphammer -y" + supress)
os.system("sudo apt install dsniff -y" + supress)



os.chdir(cwd)

print(f"[{GREEN}+{RESET}] Running Install Script...")
os.system(f"{cwd}/util/install.sh -Wlnfv" + supress)

print(f"[{GREEN}+{RESET}] Installing Mininet...")
os.system("sudo apt install -y mininet" + supress)


print(f"[{GREEN}+{RESET}] Compiling...")
os.system("sudo make install" + supress)

print(f"[{GREEN}+{RESET}] Installing openvswitch-testcontroller...")
os.system("sudo apt install openvswitch-testcontroller" + supress)

os.system("sudo ln /usr/bin/ovs-testcontroller /usr/bin/controller" + supress)

with open(f"{cwd}/../Framework/first_install_check", "r+") as file:
	content = file.read()
	if "1" in content:
		file.truncate(0)
		file.write('0')
'''
