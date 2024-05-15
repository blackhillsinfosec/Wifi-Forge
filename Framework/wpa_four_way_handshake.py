from mn_wifi.cli import CLI
from mn_wifi.net import Mininet_wifi
import os

def create_wifi_network():
    net = Mininet_wifi()

    # Create stations
    print('********* Creating stations ************\n')
    attacker = net.addStation('attacker')
    host1 = net.addStation('host1', passwd='qwerty', encrypt='wpa2')
    host2 = net.addStation('host2', passwd='qwerty', encrypt='wpa2')

    # Create access point
    print('********* Creating the Access Point ************\n')
    ap = net.addAccessPoint('ap1', ssid='mywifi', passwd='qwerty', encrypt='wpa2', mode='g', channel='6')

    net.configureNodes()
    print('********* Adding stations ************\n')
    net.addLink(host1, ap)
    net.addLink(host2, ap)

    net.build()
    ap.start([])
    print('********* Mininet started successfully ************\n')
    print('Run help command on the terminal to receive all the \n commands you can run in the given terminal')
    CLI(net)
    net.stop()
