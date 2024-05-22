import socket
import hashlib

def generate_ntlm_hash(password):
	hash_utf16le = password.encode('utf-16le')
	ntlm_hash = hashlib.new('md4', hash_utf16le).digest()
	return ntlm_hash
