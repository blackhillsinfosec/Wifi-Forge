from mininet.term import makeTerm
from mininet.net import Mininet
from mininet.node import Controller
from mininet.cli import CLI
from mn_wifi.net import Mininet_wifi
import os

def create_wifi_WPS_Pixie_attack():
    net = Mininet_wifi()

    print("Creating nodes...")
    sta1 = net.addStation('sta1', encrypt='wpa2')
    sta2 = net.addStation('sta2', encrypt='wpa2')
    ap1 = net.addAccessPoint('ap1', ssid="secure_wifi", mode="g", channel="1",
                             passwd='123456789a', encrypt='wpa2',
                             failMode="standalone", datapath='user', wps_state='2',
                             config_methods='label display push_button keypad')

    print("Configuring nodes...")
    net.configureNodes()

    print("Associating Stations...")
    net.addLink(sta1, ap1)
    net.addLink(sta2, ap1)

    print("Starting network...")
    net.build()
    ap1.start([])


    ap1.cmd('hostapd_cli -i ap1-wlan1 wps_ap_pin set 12345670')
    sta1.cmd('iw dev sta1-wlan0 interface add mon0 type monitor')
    sta1.cmd('ip link set mon0 up')
    makeTerm(sta1)  #reaver -i mon0 -b 02:00:00:00:02:00 -vv

    os.system("clear")
    print_banner()
    print("\n")
    print('                    +-_-_-_- WEP 4 Way Hand-shake started Sucessfully -_-_-_-+')
    print('                             Type "xterm a" and press enter to begin')
    print('                            Type exit when the simulation is completed\n')

    CLI(net)

    net.stop()
