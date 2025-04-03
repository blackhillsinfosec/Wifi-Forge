from mininet.term import makeTerm
from mn_wifi.net import Mininet_wifi
from framework.helper_functions.CONNECT_TMUX import CONFIG_TMUX
import os

def WPS_PIXIE_DUST_ATTACK():
    net = Mininet_wifi()

    print("Creating Stations...")
    attacker = net.addStation('Attacker', encrypt='wpa2')
    host1 = net.addStation('host1', encrypt='wpa2')
    
    print('Creating the Access Point...')
    ap1 = net.addAccessPoint('ap1', ssid="secure_wifi", mode="g", channel="1",
                             passwd='123456789a', encrypt='wpa2',
                             failMode="standalone", datapath='user', wps_state='2',
                             config_methods='label display push_button keypad')
    net.configureWifiNodes()

    print("Adding Stations...")
    net.addLink(attacker, ap1)
    net.addLink(host1, ap1)

    net.build()
    ap1.start([])

    ap1.cmd('hostapd_cli -i ap1-wlan1 wps_ap_pin set 12345670')
    attacker.cmd('iw dev a-wlan0 interface add mon0 type monitor')
    attacker.cmd('ip link set mon0 up')

    CONFIG_TMUX(["Attacker", "host1"], "WPS")

    net.stop()
    os.system("clear")
