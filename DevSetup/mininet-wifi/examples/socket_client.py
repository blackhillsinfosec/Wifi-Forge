#!/usr/bin/env python

import socket


def client():
    host = '127.0.0.1'
    port = 12345  # Make sure it's within the > 1024 $$ <65535 range
    message = ''
    while message != 'q' and message != 'exit':
        s = socket.socket()
        s.connect((host, port))
        message = input('-> ')
        s.send(str(message).encode('utf-8'))
        data = s.recv(1024).decode('utf-8')
        print('Received from server: ' + data)
        s.close()


if __name__ == '__main__':
    client()
