from mininet.node import Controller
from mininet.cli import CLI
from mn_wifi.net import Mininet_wifi
from WifiForge import print_banner
import os

def create_wifi_WEP_attack():
    net = Mininet_wifi(controller=Controller)
    print("WEP ATTACK")
    print('Creating stations...')
    sta1 = net.addStation('sta1', passwd='1234567891a', encrypt='wep')
    sta2 = net.addStation('sta2', passwd='123456789a', encrypt='wep')
    
    print('Creating the Access Point...')
    ap1 = net.addAccessPoint('ap1', ssid="simplewifi", mode="g", channel="1", passwd='123456789a', encrypt='wep', failMode="standalone", datapath='user')
    c1 = net.addController('c1')
    net.configureWifiNodes()

    print('Adding stations...')
    net.addLink(sta1, ap1)
    net.addLink(sta2, ap1)

    net.build()
    c1.start()
    ap1.start([c1])

    os.system("clear")
    print_banner()
    print("\n")
    print('                    +-_-_-_- WEP 4 Way Hand-shake started Sucessfully -_-_-_-+')
    print('                             Type "xterm a" and press enter to begin')
    print('                            Type exit when the simulation is completed\n')

    CLI(net)

    net.stop()
