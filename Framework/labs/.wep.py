from mininet.log import setLogLevel, info
from mn_wifi.cli import CLI
from mn_wifi.net import Mininet_wifi
from time import sleep
from WifiForge import print_banner
import os


def WEP_NETWORK():
    setLogLevel('info')
    net = Mininet_wifi()

    print("Creating Stations...")
    attacker = net.addStation('a', passwd='123456789a', encrypt='wep', wlans=2)
    host1 = net.addStation('host1', passwd='123456789a', encrypt='wep')
    host2 = net.addStation('host2', passwd='123456789a', encrypt='wep')
    ap1 = net.addAccessPoint('ap1', ssid="WEP_NETWORK", mode="g", channel="6",
                             passwd='123456789a', encrypt='wep',
                             failMode="standalone", datapath='user')

    host3 = net.addStation('host3', passwd="0864213245", encrypt="wep")
    host4 = net.addStation('host4', passwd="0864213245", ecnrypt="wep")
    ap2 = net.addAccessPoint('ap2', ssid="home_wifi", mode="g", channel="1", passwd="0864213245", encrypt="wep", failMode="standalone",datapath="user")

    print("Creating the Access Point...")
    net.configureWifiNodes()

    print("Adding Stations...")
    #net.addLink(attacker, ap1)
    net.addLink(host1, ap1)
    net.addLink(host2, ap1)

    net.addLink(host3, ap2)
    net.addLink(host4, ap2)

    net.build()
    ap1.start([])
    ap2.start([])

    print_banner()
    print("\n")
    print('                        +-_-_-_- Environment started successfully -_-_-_-+')
    print('                             Type "xterm a" and press enter to begin')
    print('                            Type exit when the simulation is completed\n')

    CLI(net)

    os.system('clear')
    net.stop()
