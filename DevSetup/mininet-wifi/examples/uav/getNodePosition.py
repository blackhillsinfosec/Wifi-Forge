#!/usr/bin/python


import sys
import time
import glob
import re

from mininet.log import info


def read_data(file, drone, node):
    f = open(file)
    lines = f.readlines()
    data = lines[0].split(',')
    #info(node, " Drone", drone, " x", data[0], " y", data[1], " z", data[2])
    time.sleep(0.5)


if __name__ == '__main__':

    files = glob.glob("examples/uav/data/*")
    node = []
    drones = []
    sta = []
    validindex = 0
    
    for f in files:
        m = re.search('data/(.+?).txt', f)
        if m:
            node.append(m.group(1))

    for d in node:
        drones.append(re.sub("[^0-9]", "", d))

    if len(sys.argv) > 1:
        sta = sys.argv[1]
    else:
        while True:
            i = 0
            for x in files:
                read_data(x, drones[i], node[i])
                i += 1

    for a in sys.argv:
        if a in node:
            i = node.index(sta)
            validindex = 1

    if validindex == 0:
        info("Node not valid")
        exit()

    while True:
        read_data(files[i], drones[i], node[i])