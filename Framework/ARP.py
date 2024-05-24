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
    ap1 = net.addAccessPoint('ap1', ssid='new-ssid', mode='g',
                             channel='1', position='10,10,0',
                             failMode="standalone")
    sta1 = net.addStation('sta1', position='10,20,0')
    sta2 = net.addStation('sta2', position='10,30,0')

    print("Configuring wifi nodes...")
    net.configureWifiNodes()

    print("Starting network...")
    net.build()
    net.addNAT().configDefault()
    ap1.start([])
    
    sta2.cmd('echo 1 > /proc/sys/net/ipv4/ip_forward')


    os.system("clear")
    print_banner()
    print("\n")
    print('                          +-_-_-_- ARP Spoof started Sucessfully -_-_-_-+')
    print('                             Type "xterm a" and press enter to begin')
    print('                            Type exit when the simulation is completed\n')
    CLI(net)
    net.stop()
