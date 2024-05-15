#!/usr/bin/python

# Make sure to have the server side running in CoppeliaSim
# Run setNodePosition.py to update station location
# If there is an error to connect to the socket run sudo pkill -9 -f python

import sys
import time
import os

from mininet.log import info

try:
    import sim
except:
    info('--------------------------------------------------------------')
    info('"sim.py" could not be imported. This means very probably that')
    info('either "sim.py" or the remoteApi library could not be found.')
    info('Make sure both are in the same folder as this file,')
    info('or appropriately adjust the file "sim.py"')
    info('--------------------------------------------------------------')
    info('')


def drone_position(args):
    drones = [[] for i in range(3)]
    drones_names = ['Quadricopter_base', 'Quadricopter_base#0', 'Quadricopter_base#1']
    nodes = []
    data = [[] for i in range(3)]

    if len(args) > 1:
        for n in range(1, len(args)):
            nodes.append(args[n])
    else:
        info("No nodes defined")
        exit()

    info('Program started')
    sim.simxFinish(-1)  # just in case, close all opened connections
    clientID = sim.simxStart('127.0.0.1', 19999, True, True, 5000, 5)  # Connect to CoppeliaSim

    if clientID != -1:
        res = None
        info('Connected to remote API server')
        # Getting the ID of the drones from the simulation
        for i in range(0, len(drones)):
            [res, drones[i]] = sim.simxGetObjectHandle(clientID,
                                                       drones_names[i],
                                                       sim.simx_opmode_oneshot_wait)

        if res == sim.simx_return_ok:
            info('Connected with CoppeliaSim')
        else:
            info('Remote API function call returned with error code: ', res)

        time.sleep(2)
        # Starting the getPosition function streaming
        for i in range(0, len(drones)):
            sim.simxGetObjectPosition(clientID,
                                      drones[i],
                                      -1,
                                      sim.simx_opmode_streaming)

        while True:
            # Getting the positions as buffers
            for i in range(0, len(drones)):
                # Try to retrieve the streamed data
                returnCode, data[i] = sim.simxGetObjectPosition(clientID,
                                                                drones[i],
                                                                -1,
                                                                sim.simx_opmode_buffer)
            # Storing the position in data files
            for i in range(0, len(data)):
                send_file(data[i], nodes[i])

            time.sleep(1)

        # Now close the connection to CoppeliaSim:
        sim.simxFinish(clientID)
    else:
        info('Failed connecting to remote API server')
    info('Program ended')


def send_file(data, node):
    path = os.path.dirname(os.path.abspath(__file__))
    file_name = "{}/data/".format(path) + node + ".txt"
    f = open(file_name, "w")
    file_position = ','.join(map(str, data))
    f.write(file_position)
    f.close()


if __name__ == '__main__':
    drone_position(sys.argv)
