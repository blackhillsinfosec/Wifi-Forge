#!/usr/bin/python

# Make sure to have the simpleTest running

import sys
import socket
import time
import os

from mininet.log import info


def client(message):
    host = '127.0.0.1'
    port = 12345  # Make sure it's within the > 1024 $$ <65535 range
    s = socket.socket()
    s.connect((host, port))
    s.send(str(message).encode('utf-8'))
    data = s.recv(1024).decode('utf-8')
    # info('Received from server: ' + data)
    s.close()


def read_data(file, node):
    f = open(file)
    lines = f.readlines()
    data = lines[0].split(',')
    data_drone = "set." + node + ".setPosition(\"" \
                 + str(50 - float(data[0]) * 20) + "," \
                 + str(50 - float(data[1]) * 20) + "," \
                 + str(50 - float(data[2]) * 20) + "\")"
    client(data_drone)
    time.sleep(0.5)


if __name__ == '__main__':

    nodes = []
    files = []

    if len(sys.argv) > 1:
        path = os.path.dirname(os.path.abspath(__file__))
        for n in range(1, len(sys.argv)):
            nodes.append(sys.argv[n])
            pfile = '{}/data/'.format(path) + sys.argv[n] + '.txt'
            files.append(pfile)
    else:
        info("No nodes defined")
        exit()

    while True:
        i = 0
        for x in files:
            read_data(x, nodes[i])
            i += 1
