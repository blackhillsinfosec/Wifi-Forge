from mn_wifi.cli import CLI
from mn_wifi.net import Mininet_wifi
from time import sleep


def WEP_attack():
    "Create a network."
    net = Mininet_wifi()

    print("*** Creating nodes\n")
    attacker = net.addStation('a', passwd='123456789a', encrypt='wep')
    sta2 = net.addStation('sta2', passwd='123456789a', encrypt='wep')
    sta3 = net.addStation('sta3', passwd='123456789a', encrypt='wep')
    ap1 = net.addAccessPoint('ap1', ssid="simplewifi", mode="g", channel="1",
                             passwd='123456789a', encrypt='wep',
                             failMode="standalone", datapath='user')

    print("*** Configuring wifi nodes\n")
    net.configureWifiNodes()

    print("*** Associating Stations\n")
    net.addLink(attacker, ap1)
    net.addLink(sta2, ap1)
    net.addLink(sta3, ap1)

    print("*** Starting network\n")
    net.build()
    ap1.start([])

    sleep(10)

    print("*** Running CLI\n")
    CLI(net)

    print("*** Stopping network\n")
    net.stop()
