from mn_wifi.cli import CLI
from mn_wifi.net import Mininet_wifi
from WifiForge import print_banner
import os
'''
Estbalish an environment for learning ARP spoofing
See original script here: https://hackmd.io/@ramonfontes/cracking_wep
'''

def create_arp_spoof():
    net = Mininet_wifi()

    print("Creating nodes...")
    attacker = net.addStation('a', wlans=2,passwd='december2022', encrypt='wpa2')
    host1 = net.addStation('host1', position='10,20,0')
    host2 = net.addStation('host2', position='10,30,0')

    print('Creating the Access Point...')
    ap = net.addAccessPoint('ap1', ssid='new-ssid', mode='g', channel='1', position='10,10,0', failMode="standalone")
    net.configureWifiNodes()

    print('Adding stations...')
    net.build()
    net.addNAT().configDefault()
    ap.start([])
    host2.cmd('echo 1 > /proc/sys/net/ipv4/ip_forward')


    print_banner()
    print("\n")
    print('                          +-_-_-_- ARP Spoof started Sucessfully -_-_-_-+')
    print('                             Type "xterm a" and press enter to begin')
    print('                            Type exit when the simulation is completed\n')
    
    CLI(net)
    
    net.stop()
    os.system("clear")
    exit()