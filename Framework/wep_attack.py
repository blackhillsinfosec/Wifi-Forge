from mn_wifi.cli import CLI
from mn_wifi.net import Mininet_wifi
from time import sleep


def WEP_attack():
    "Create a network."
    net = Mininet_wifi()

    print("*** Creating nodes\n")
    attacker = net.addStation('a', passwd='123456789a', encrypt='wep')
    host1 = net.addStation('host1', passwd='123456789a', encrypt='wep')
    host2 = net.addStation('host2', passwd='123456789a', encrypt='wep')
    ap1 = net.addAccessPoint('ap1', ssid="simplewifi", mode="g", channel="6",
                             passwd='123456789a', encrypt='wep',
                             failMode="standalone", datapath='user')

    print("*** Configuring wifi nodes\n")
    net.configureWifiNodes()

    print("*** Associating Stations\n")
    net.addLink(attacker, ap1)
    net.addLink(host1, ap1)
    net.addLink(host2, ap1)

    print("*** Starting network\n")
    net.build()
    ap1.start([])

    print_banner()
    print("\n")
    print('                          +-_-_-_- WEP lab started Sucessfully -_-_-_-+')
    print('                             Type "xterm a" and press enter to begin')
    print('                            Type exit when the simulation is completed\n')

    print("*** Running CLI\n")
    CLI(net)

    print("*** Stopping network\n")
    os.system('clear')
    net.stop()
    exit()