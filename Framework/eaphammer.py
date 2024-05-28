#!/usr/bin/python3

import time
import random
import os
import string
from tqdm import tqdm
from datetime import datetime
import sys

#variables
interface = "a-wlan0"

def print_file_names(message):
    datestring = datetime.strftime(datetime.now(), '%Y-%m-%d-%H-%M-%S')
    randstring = ''.join(random.choice(string.ascii_letters+string.digits) for _ in range(32))
    message += '-'.join([datestring,randstring])
    print(message)

#check argv
if len(sys.argv) != 6:
    print("Invalid Arguments!")
    exit()

if sys.argv[1] != "-e":
    print("Missing SSID")
    exit()

if sys.argv[2] and sys.argv[2] != "--creds":
    ssid = sys.argv[2]
else:
    print("Invalid SSID")
    exit()

if sys.argv[3] != "--creds":
    print("Specify --creds")
    exit()

if sys.argv[4] != "--interface":
    print("Specify --interface")
    exit()

if not sys.argv[5] or sys.argv[5] != "a-wlan0":
    print("Invalid Interface!")
    exit()


print('''
                     .__                                         
  ____ _____  ______ |  |__ _____    _____   _____   ___________ 
_/ __ \\\\__  \\ \\____ \\|  |  \\\\__  \\  /     \\ /     \\_/ __ \\_  __ \\
\\  ___/ / __ \\|  |_> >   Y  \\/ __ \\|  Y Y  \\  Y Y  \\  ___/|  | \\/
 \\___  >____  /   __/|___|  (____  /__|_|  /__|_|  /\\___  >__|   
     \\/     \\/|__|        \\/     \\/      \\/      \\/     \\/       


                        Now with  more fast travel than a next-gen Bethesda game. >:D

                             Version:  1.14.0
                            Codename:  Final Frontier
                              Author:  @s0lst1c3
                             Contact:  gabriel<<at>>transmitengage.com

    ''')


time.sleep(2)

print("[?] Am I root?")
print("[*] Checking for rootness...")
time.sleep(random.randint(0,2))
if os.getuid() != 0:
    print("[!] Error: this script must be run as root.")
    exit()
else:
    print("[*] I AM ROOOOOOOOOOOT")
print("[*] Root privs confirmed 8D")
print("[*] Saving current iptables configuration...")
time.sleep(random.randint(0,2))
print("[*] Reticulating radio frequency splines...\n\n")
time.sleep(random.randint(0,2))
print("[*] Using nmcli to tell NetworkManager not to manage attacker-wlan0...")
for i in tqdm(range(int(9e6))):
    pass

print("\n\n")
print("[*] Success: a-wlan0 no longer controlled by NetworkManager")
print("[*] WPA handshakes will be saved to wpa_hakeshake_capture")

print_file_names(f"[*] WPA handshakes will be saved to {os.getcwd()}/eaphammer/loot/wpa_handshake_capture")
print_file_names(f"Configuration file: {os.getcwd()}/wpa_handshake_capture\n\n")

print("[hostapd] AP starting...\n\n")

print("a-wlan0: interface state UNINITIALIZED->COUNTRY_UPDATE")
print(f"Using interface a-wlan0 with hwaddr 00:11:22:33:44:00 and ssid {ssid}")
print("a-wlan0: interface state COUNTRY_UPDATE->ENABLED")
print("attacker-wlan0: AP-ENABLED\n\n")


while exit_input != '\n':
    exit_input = input("Press enter to quit...\n\n")



