import os

RED = "\033[91m"
GREEN = "\033[92m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
RESET = "\033[0m"

cwd = os.getcwd()

#Format the string to only include the path to the repo's main file
#The exact path is needed to add to the safe.repositories file
index = cwd.index("/MiniNet-Framework")
truncated_cwd = cwd[:index + len("/MiniNet-Framework")]


#need to change the config file to trust the submodule
supress = "" #">/dev/null 2>&1"
print(f"[{GREEN}+{RESET}] Adding Submodules to safe.directory...")
os.system(f"git config --global --add safe.directory {truncated_cwd}" + supress)

print(f"[{GREEN}+{RESET}] Initializating Submodules...")
os.system("git submodule init" + supress)

os.system("git submodule update" + supress)

print(f"[{GREEN}+{RESET}] Installing Kali Tools...")
os.system("sudo apt install curl -y" + supress)
os.system("sudo ./dependencies.sh" + supress)
os.system("sudo apt install aircrack-ng -y" + supress)
os.system("sudo apt install john -y" + supress)
os.system("sudo apt install eaphammer -y" + supress)
os.system("sudo apt install dsniff -y" + supress)


print(cwd+"===================================================")
os.chdir(cwd+"/mininet-wifi")


print(f"[{GREEN}+{RESET}] Installing Mininet...")
os.system("sudo apt install mininet -y --allow-downgrades" + supress)

print(f"[{GREEN}+{RESET}] Running Install Script...")
os.system("./util/install.sh -Wlnfv" + supress)




print(f"[{GREEN}+{RESET}] Compiling...")
os.system("sudo make install" + supress)

print(f"[{GREEN}+{RESET}] Installing openvswitch-testcontroller...")
os.system("sudo apt install openvswitch-testcontroller -y" + supress)

os.system("sudo ln /usr/bin/ovs-testcontroller /usr/bin/controller" + supress)

with open("../first_install_check", "r+") as file:
	content = file.read()
	if "1" in content:
		file.truncate(0)
		file.write('0')

