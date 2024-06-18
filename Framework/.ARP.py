from mn_wifi.cli import CLI
from mn_wifi.net import Mininet_wifi
from WifiForge import print_banner
import os
'''
Estbalish an environment for learning ARP spoofing
See original script here: https://hackmd.io/@ramonfontes/cracking_wep
'''

def ARPSPOOF():
    net = Mininet_wifi()

    print("Creating stations...")
    attacker = net.addStation('a', position='10,30,0')
    host1 = net.addStation('host1', position='10,20,0')

    print('Creating the Access Point...')
    ap = net.addAccessPoint('ap1', ssid='new-ssid', mode='g', channel='1', position='10,10,0', failMode="standalone")
    net.configureWifiNodes()

    print('Adding Stations...')
    net.build()
    net.addNAT().configDefault()
    ap.start([])
    attacker.cmd('echo 1 > /proc/sys/net/ipv4/ip_forward')


    print_banner()
    print("\n")
    print('                        +-_-_-_- Environment started successfully -_-_-_-+')
    print('                             Type "xterm a" and press enter to begin')
    print('                            Type exit when the simulation is completed\n')
    
    CLI(net)
    
    net.stop()
    os.system("clear")
    exit()
