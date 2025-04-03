from mininet.log import setLogLevel, info
from mn_wifi.cli import CLI
from mn_wifi.net import Mininet_wifi
from framework.helper_functions.CONNECT_TMUX import CONFIG_TMUX
from time import sleep
from WifiForge import print_banner
import os

def WEP_ATTACK():

    # BUILD NETWORK 

    setLogLevel('info')
    net = Mininet_wifi()

    print("Creating Stations...")
    attacker = net.addStation('Attacker', passwd='123456789a', encrypt='wep', wlans=2)
    host1 = net.addStation('host1', passwd='123456789a', encrypt='wep')
    host2 = net.addStation('host2', passwd='123456789a', encrypt='wep')
    ap1 = net.addAccessPoint('ap1', ssid="WEP_NETWORK", mode="g", channel="6",
                             passwd='123456789a', encrypt='wep',
                             failMode="standalone", datapath='user')

    print("Creating the Access Point...")
    net.configureWifiNodes()

    print("Adding Stations...")
    net.addLink(host1, ap1)
    net.addLink(host2, ap1)

    net.build()
    ap1.start([])
    
    CONFIG_TMUX(['Attacker', 'host1', 'host2'], "WEP_ATTACK")

    #KILL LAB
    os.system('clear')
    net.stop()
