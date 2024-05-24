from mininet.node import Controller
from mininet.cli import CLI
from mn_wifi.net import Mininet_wifi
from WifiForge import print_banner
import os

def WEP_attack():
    net = Mininet_wifi(controller=Controller)
    
    print('Creating stations...')
    
    attacker = net.addStation('a', wlans=2, password='12345', encrypt='wep')
    sta1 = net.addStation('sta1', passwd='12345678', encrypt='wep')
    sta2 = net.addStation('sta2', passwd='12345678', encrypt='wep')
    
    print('Creating the Access Point...')
    ap = net.addAccessPoint('ap1', ssid="mywifi", mode="g", channel="6", passwd='123456789a', encrypt='wep')
    c0 = net.addController('c0', controller=Controller)
    net.configureWifiNodes()

    print('Adding stations...')
    net.addLink(attacker, ap)
    net.addLink(sta1, ap)
    net.addLink(sta2, ap)

    net.build()
    c0.start()
    ap.start([c0])

    print_banner()    
    print("\n")
    print('                    +-_-_-_- WEP 4 Way Hand-shake started Sucessfully -_-_-_-+')
    print('                             Type "xterm a" and press enter to begin')
    print('                            Type exit when the simulation is completed\n')

    CLI(net)

    net.stop()
