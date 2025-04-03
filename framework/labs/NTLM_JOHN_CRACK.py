from mn_wifi.cli import CLI
from mn_wifi.net import Mininet_wifi
from framework.helper_functions.CONNECT_TMUX import CONFIG_TMUX
import os
'''
Estbalish an environment for learning WEP attacks
See original script here: https://hackmd.io/@ramonfontes/cracking_wep
'''

def NTLM_JOHN_CRACK():
	net = Mininet_wifi()

	print("Creating Stations...")
	host1 = net.addStation('Attacker', passwd='JERRY277626AA', encrypt='wpa2', wlans=2)
	host2 = net.addStation('host1', passwd='JERRY277626AA', encrypt='wpa2', wlans=2)

	print("Creating Access Point...")
	ap1 = net.addAccessPoint('ap1', ssid="CORP_NET", mode='g', channel='1', passwd="JERRY277626AA", encrypt="wpa2")
	c0 = net.addController('c0')
	net.configureWifiNodes()

	print('Adding Stations')
	net.addLink(host1, ap1)
	net.addLink(host2, ap1)

	net.build()
	ap1.start([])

	CONFIG_TMUX(["Attacker"], "NTLM_JOHN_CRACK")

	net.stop()
	os.system("rm /Wifi-Forge/framework/loot/4whs.pot")
	os.system("clear")


