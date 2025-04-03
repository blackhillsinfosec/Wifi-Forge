from mn_wifi.net import Mininet_wifi
from framework.helper_functions.CONNECT_TMUX import CONFIG_TMUX
import os

def CRACKING_WPA_WITH_AIRCRACK():
    net = Mininet_wifi()

    print('Creating Stations')
    attacker = net.addStation('Attacker', wlans=1)

    #secure_wifi
    host1 = net.addStation('host1', passwd='123456789a', encrypt='wep')
    host2 = net.addStation('host2', passwd='123456789a', encrypt='wep')
    ap0 = net.addAccessPoint('ap0', ssid="WEP_Network", mode="g", channel="1",
                             passwd='123456789a', encrypt='wep',
                             failMode="standalone", datapath='user')
    #WPA-LAB
    host3 = net.addStation('host1', passwd='december2022', encrypt='wpa2')
    host4 = net.addStation('host2', passwd='december2022', encrypt='wpa2')
    ap1 = net.addAccessPoint('ap1', ssid='WPA2_Network', passwd='december2022', encrypt='wpa2', mode='g', channel='6')


    #Harlow_Home
    host5 = net.addStation('host5', passwd='password', encrypt='wpa2')
    host6 = net.addStation('host6', passwd='password', encrypt='wpa2')
    host7 = net.addStation('host7', passwd='password', encrypt='wpa2')
    ap2 = net.addAccessPoint('ap2', ssid='Harlow_Home_Wifi', passwd='password', encrypt='wpa2', mode='g', channel='11')


    #FBI_Van
    host8 = net.addStation('host8', passwd='supersecurepassword', encrypt='wpa2')
    ap3 = net.addAccessPoint('ap3', ssid='FBI_Van', passwd='supersecurepassword', encrypt='wpa2', mode='g', channel='1')


    #Hidden_SSID
    host9 = net.addStation('host9', passwd='iamhidden', encrypt='wpa2')
    ap4 = net.addAccessPoint('ap4', ssid='cantseeme', passwd='iamhidden', encrypt='wpa2', mode='g', channel='11')
       
    print('Creating the Access Point...')
    net.configureWifiNodes()

    print('Adding Stations...')
    net.addLink(host1, ap0)
    net.addLink(host2, ap0)

    net.addLink(host3, ap1)
    net.addLink(host4, ap1)

    net.addLink(host5, ap2)
    net.addLink(host6, ap2)
    net.addLink(host7, ap2)

    net.addLink(host8, ap3)

    net.addLink(host9, ap4)

    net.build()
    ap0.start([])
    ap1.start([])
    ap2.start([])
    ap3.start([])
    ap4.start([])
    
    CONFIG_TMUX(["Attacker"], "WPA_CRACK")

    net.stop()
    os.system("clear")
