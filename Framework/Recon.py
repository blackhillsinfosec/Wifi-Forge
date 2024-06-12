from mininet.node import Controller
from mn_wifi.cli import CLI
from mn_wifi.net import Mininet_wifi
from WifiForge import print_banner
import os

def RECON():
    net = Mininet_wifi(controller=Controller)

    print('Creating Stations...')
    attacker = net.addStation('a', wlans=2,passwd='december2022', encrypt='wpa2')
    host1 = net.addStation('host1', passwd='december2022', encrypt='wpa2')
    host2 = net.addStation('host2', passwd='december2022', encrypt='wpa2')

    print('Creating the Access Point...')
    ap = net.addAccessPoint('ap1', ssid='mywifi', passwd='december2022', encrypt='wpa2', mode='g', channel='6')
    c0 = net.addController('c0', controller=Controller)
    net.configureWifiNodes()

    print('Adding Stations...')
    net.addLink(attacker,ap)
    net.addLink(host1, ap)
    net.addLink(host2, ap)

    net.build()
    c0.start()
    ap.start([c0])
    
    print_banner()
    print("\n")
    print('                       +-_-_-_- Recon environment started Sucessfully -_-_-_-+')
    print('                             Type "xterm a" and press enter to begin')
    print('                            Type exit when the simulation is completed\n')
    
    CLI(net)

    net.stop()
    os.system("clear")
    exit()