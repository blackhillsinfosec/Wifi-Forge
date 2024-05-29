# -*- coding: utf-8 -*-
# Eclipse SUMO, Simulation of Urban MObility; see https://eclipse.org/sumo
# Copyright (C) 2008-2017 German Aerospace Center (DLR) and others.
# This program and the accompanying materials
# are made available under the terms of the Eclipse Public License v2.0
# which accompanies this distribution, and is available at
# http://www.eclipse.org/legal/epl-v20.html

# @file    __init__.py
# @author  Michael Behrisch
# @author  Lena Kalleske
# @author  Mario Krumnow
# @author  Daniel Krajzewicz
# @author  Jakob Erdmann
# @date    2008-10-09
# @version $Id$

from __future__ import print_function
from __future__ import absolute_import
import socket
import time
import subprocess


from .domain import _defaultDomains
from .connection import Connection
from .exceptions import FatalTraCIError, TraCIException
from . import _simulation

simulation = _simulation.SimulationDomain()

_connections = {}
_traceFile = {}
_traceGetters = {}
# cannot use immutable type as global variable
_currentLabel = [""]
_connectHook = None


def setConnectHook(hookFunc):
    global _connectHook
    _connectHook = hookFunc


def _STEPS2TIME(step):
    """Conversion from time steps in milliseconds to seconds as float"""
    return step / 1000.


def connect(port=8813, numRetries=10, host="localhost", proc=None, waitBetweenRetries=1):
    """
    Establish a connection to a TraCI-Server and return the
    connection object. The connection is not saved in the pool and not
    accessible via traci.switch. It should be safe to use different
    connections established by this method in different threads.
    """
    for retry in range(1, numRetries + 2):
        try:
            conn = Connection(host, port, proc)
            if _connectHook is not None:
                _connectHook(conn)
            return conn
        except socket.error as e:
            if proc is not None and proc.poll() is not None:
                raise TraCIException("TraCI server already finished")
            if retry > 1:
                print("Could not connect to TraCI server at %s:%s" % (host, port), e)
            if retry < numRetries + 1:
                print(" Retrying in %s seconds" % waitBetweenRetries)
                time.sleep(waitBetweenRetries)
    raise FatalTraCIError("Could not connect in %s tries" % (numRetries + 1))


def init(port=8813, numRetries=10, host="localhost",
         label="default", proc=None, doSwitch=True):
    """
    Establish a connection to a TraCI-Server and store it under the given
    label. This method is not thread-safe. It accesses the connection
    pool concurrently.
    """
    _connections[label] = connect(port, numRetries, host, proc)
    if doSwitch:
        switch(label)
    return _connections[label].getVersion()


def start(cmd, port=None, numRetries=10, label="default"):
    """
    Start a sumo server using cmd, establish a connection to it and
    store it under the given label. This method is not thread-safe.
    """
    sumoProcess = subprocess.Popen(cmd + ["--remote-port", str(port)])
    _connections[label] = connect(port, numRetries, "localhost", sumoProcess)
    switch(label)
    return getVersion()


def load(args):
    """load([optionOrParam, ...])
    Let sumo load a simulation using the given command line like options
    Example:
      load(['-c', 'run.sumocfg'])
      load(['-n', 'net.net.xml', '-r', 'routes.rou.xml'])
    """
    print(_connections)
    return _connections[""].load(args)


def simulationStep(step=0):
    """
    Make a simulation step and simulate up to the given second in sim time.
    If the given value is 0 or absent, exactly one step is performed.
    Values smaller than or equal to the current sim time result in no action.
    """
    if "" not in _connections:
        raise FatalTraCIError("Not connected.")
    return _connections[""].simulationStep(step)


def addStepListener(listener):
    """addStepListener(traci.StepListener) -> int
    Append the step listener (its step function is called at the end of every call to traci.simulationStep())
    to the current connection.
    Returns the ID assigned to the listener if it was added successfully, None otherwise.
    """
    if "" not in _connections:
        raise FatalTraCIError("Not connected.")
    return _connections[""].addStepListener(listener)


def removeStepListener(listenerID):
    """removeStepListener(traci.StepListener) -> bool
    Remove the step listener from the current connection's step listener container.
    Returns True if the listener was removed successfully, False if it wasn't registered.
    """
    if "" not in _connections:
        raise FatalTraCIError("Not connected.")
    return _connections[""].removeStepListener(listenerID)


def getVersion():
    return _connections[""].getVersion()


def setOrder(order):
    return _connections[""].setOrder(order)


def close(wait=True):
    _connections[""].close(wait)


def switch(label):
    _connections[""] = _connections[label]
    for domain in _defaultDomains:
        domain._setConnection(_connections[""])


def getConnection(label ="default"):
    if not label in _connections:
        raise TraCIException("connection with label '%s' is not known")
    return _connections[label]