from scapy.all import *

send(IP(src="10.0.0.2", dst="10.0.0.1")/ICMP())
