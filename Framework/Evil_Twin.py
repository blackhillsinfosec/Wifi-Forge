import socket
import hashlib
from WifiForge import print_banner

def Evil_Twin_Lab(password):
	print_banner();
	hash_utf16le = password.encode('utf-16le')
	ntlm_hash = hashlib.new('md4', hash_utf16le).digest()
	return ntlm_hash
