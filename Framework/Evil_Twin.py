from WifiForge import print_banner
from mininet.net import Mininet
from mininet.log import setLogLevel, info
from mininet.node import Controller
from mn_wifi.cli import CLI
from mn_wifi.net import Mininet_wifi
import os
'''
Estbalish an environment for learning WEP attacks
See original script here: https://hackmd.io/@ramonfontes/cracking_wep
'''

def EAPHAMMER_AND_NETNTLM_CRACKING():
	net = Mininet_wifi(controller=Controller)

	print("Creating Stations...")
	host1 = net.addStation('a', passwd='JERRY277626AA', encrypt='wpa2', wlans=2)
	host2 = net.addStation('host1', passwd='JERRY277626AA', encrypt='wpa2', wlans=2)

	print("Creating Access Point...")
	ap1 = net.addAccessPoint('ap1', ssid="CORP_NET", mode='g', channel='1', passwd="JERRY277626AA", encrypt="wpa2")
	c0 = net.addController('c0')
	net.configureWifiNodes()

	print('Adding Stations')
	net.addLink(host1, ap1)
	net.addLink(host2, ap1)

	net.build()
	c0.start()
	ap1.start([c0])

	net.build()
	c0.start()
	ap1.start([c0])

	os.system("clear")
	print_banner()
	print("\n")
	print('                    +-_-_-_- Eaphammer environment started Sucessfully -_-_-_-+')
	print('                             Type "xterm a" and press enter to begin')
	print('                            Type exit when the simulation is completed\n')

	CLI(net)

	net.stop()
	os.system("clear")
	exit()


