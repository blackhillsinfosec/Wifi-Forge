"""
@file    connection.py
@author  Daniel Krajzewicz
@author  Laura Bieker
@author  Karol Stosiek
@author  Michael Behrisch
@date    2011-11-28
@version $Id: connection.py 13106 2012-12-02 13:44:57Z behrisch $

This file contains a Python-representation of a single connection.

SUMO, Simulation of Urban MObility; see http://sumo.sourceforge.net/
Copyright (C) 2008-2012 DLR (http://www.dlr.de/) and contributors
All rights reserved
"""
class Connection:
    """edge connection for a sumo network"""
    def __init__(self, fromEdge, toEdge, fromLane, toLane, direction, tls, tllink):
        self._from = fromEdge
        self._to = toEdge
        self._fromLane = fromLane
        self._toLane = toLane
        self._tls = tls
        self._tlLink = tllink
