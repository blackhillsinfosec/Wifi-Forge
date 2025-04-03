from mn_wifi.cli import CLI
from mn_wifi.net import Mininet_wifi
from framework.helper_functions.CONNECT_TMUX import CONFIG_TMUX
import os

def WIFIPHISHER():
    net = Mininet_wifi()

    print('Creating Stations...')
    attacker = net.addStation('Attacker', wlans=2,passwd='december2022', encrypt='wpa2')
    host1 = net.addStation('host1', passwd='december2022', encrypt='wpa2')
    host2 = net.addStation('host2', passwd='december2022', encrypt='wpa2')

    print('Creating the Access Point...')
    ap = net.addAccessPoint('ap1', ssid='mywifi', passwd='december2022', encrypt='wpa2', mode='g', channel='6')
    net.configureWifiNodes()

    print('Adding Stations...')
    net.addLink(attacker,ap)
    net.addLink(host1, ap)
    net.addLink(host2, ap)

    net.build()
    ap.start([])
    
    CONFIG_TMUX(["Attacker", "host1"], "WIFIPHISHER")

    net.stop()
    os.system("ps aux | grep 'wifiphisher' | awk '{print $2}' | xargs -I {} kill -9 {}")
    
