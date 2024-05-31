"""
    Mininet-WiFi: A simple networking testbed for Wireless OpenFlow/SDWN!
    author: Ramon Fontes (ramonrf@dca.fee.unicamp.br)
"""

from time import time, sleep
from threading import Thread as thread
import random
import math

from pylab import cos, sin
from mininet.log import info
from mn_wifi.plot import PlotGraph
from mn_wifi.mobility import Mobility, ConfigMobLinks
from mn_wifi.node import Station, AP


class ReplayingMobility(Mobility):

    timestamp = False
    net = None

    def __init__(self, net, nodes=None):
        self.net = net
        Mobility.thread_ = thread(name='replayingMobility', target=self.mobility,
                                  args=(nodes,))
        Mobility.thread_.daemon = True
        Mobility.thread_._keep_alive = True
        Mobility.thread_.start()

    def timestamp_(self, node, time_):
        if time_ >= float(node.time[0]):
            pos = node.p[0]
            del node.p[0]
            del node.time[0]
            self.set_pos(node, pos)

    def notimestamp_(self, node, time_):
        if time_ >= node.currentTime:
            for n in range(0, node.params['speed']):
                if len(node.p) > 0:
                    pos = node.p[0]
                    del node.p[0]
                    node.currentTime += node.timestamp
                    self.set_pos(node, pos)

    def mobility(self, nodes):
        if nodes is None:
            nodes = self.net.stations + self.net.aps
        for node in nodes:
            if isinstance(node, Station):
                if hasattr(node, 'position') and node not in self.stations:
                    self.stations.append(node)
            if isinstance(node, AP):
                if hasattr(node, 'position') and node not in self.aps:
                    self.aps.append(node)

        if self.net.draw:
            self.net.isReplaying = False
            self.net.check_dimension(nodes)

        currentTime = time()
        for node in nodes:
            if 'speed' not in node.params:
                node.params['speed'] = 1.0
            node.currentTime = 1 / node.params['speed']
            node.timestamp = float(1.0 / node.params['speed'])
            if hasattr(node, 'time'):
                self.timestamp = True

        calc_pos = self.timestamp_ if self.timestamp else self.notimestamp_

        while self.thread_._keep_alive:
            time_ = time() - currentTime
            if len(nodes) == 0:
                break
            for node in nodes:
                if hasattr(node, 'p'):
                    calc_pos(node, time_)
                    if len(node.p) == 0:
                        nodes.remove(node)
                    ConfigMobLinks()
                    if self.net.draw:
                        node.update_2d()
            if self.net.draw:
                PlotGraph.pause()


class ReplayingBandwidth(Mobility):

    net = None

    def __init__(self, net):
        self.net = net
        Mobility.thread_ = thread(name='replayingBandwidth', target=self.throughput)
        Mobility.thread_.daemon = True
        Mobility.thread_._keep_alive = True
        Mobility.thread_.start()

    def throughput(self):
        currentTime = time()
        stations = self.net.stations
        while self.thread_._keep_alive:
            if len(stations) == 0:
                break
            time_ = time() - currentTime
            for sta in stations:
                if hasattr(sta, 'time'):
                    if time_ >= sta.time[0]:
                        sta.wintfs[0].config_tc(bw=sta.throughput[0], loss=0, latency=0)
                        # pos = '%d, %d, %d' % (sta.throughput[0], sta.throughput[0], 0)
                        # self.moveStationTo(sta, pos)
                        del sta.throughput[0]
                        del sta.time[0]
                        #info('%s\n' % sta.time[0])
                    if len(sta.time) == 1:
                        stations.remove(sta)
            # time.sleep(0.001)
        info("\nReplaying Process Finished!")


class ReplayingNetworkConditions(Mobility):

    net = None

    def __init__(self, net, **kwargs):
        self.net = net
        Mobility.thread_ = thread(name='replayingNetConditions', target=self.behavior)
        Mobility.thread_.daemon = True
        Mobility.thread_._keep_alive = True
        Mobility.thread_.start()

    def behavior(self):
        seconds = 5
        info('Replaying process starting in %s seconds\n' % seconds)
        sleep(seconds)
        info('Replaying process has been started\n')
        currentTime = time()
        stations = self.net.stations
        for sta in stations:
            sta.wintfs[0].freq = sta.wintfs[0].get_freq()
        while self.thread_._keep_alive:
            if len(stations) == 0:
                break
            time_ = time() - currentTime
            for sta in stations:
                if hasattr(sta, 'time'):
                    if time_ >= sta.time[0]:
                        if sta.wintfs[0].associatedTo:
                            bw = sta.bw[0]
                            loss = sta.loss[0]
                            latency = sta.latency[0]
                            sta.wintfs[0].config_tc(bw=bw, loss=loss, latency=latency)
                        del sta.bw[0]
                        del sta.loss[0]
                        del sta.latency[0]
                        del sta.time[0]
                    if len(sta.time) == 0:
                        stations.remove(sta)
            sleep(0.001)
        info('Replaying process has finished!')


class ReplayingRSSI(Mobility):

    print_bw = False
    print_loss = False
    print_latency = False
    print_distance = False
    net = None

    def __init__(self, net, ppm='friis', n=32, **kwargs):
        self.net = net
        for key in kwargs:
            setattr(self, key, kwargs[key])

        Mobility.thread_ = thread(name='replayingRSSI', target=self.rssi,
                              args=(ppm, n))
        Mobility.thread_.daemon = True
        Mobility.thread_._keep_alive = True
        Mobility.thread_.start()

    def rssi(self, ppm, n):
        currentTime = time()
        staList = self.net.stations
        ang = {}
        for sta in staList:
            ang[sta] = random.uniform(0, 360)
            sta.wintfs[0].freq = sta.wintfs[0].get_freq()
        while self.thread_._keep_alive:
            if len(staList) == 0:
                break
            time_ = time() - currentTime
            for sta in staList:
                if hasattr(sta, 'time'):
                    if time_ >= sta.time[0]:
                        ap = sta.wintfs[0].associatedTo.node  # get AP
                        sta.wintfs[0].rssi = sta.rssi[0]
                        if ap:
                            rssi = sta.rssi[0]
                            dist = self.calc_dist(sta, ap, rssi, ppm, n)
                            self.set_pos(sta, ap, dist, ang[sta])
                            sta.wintfs[0].configWLink(dist)
                        del sta.rssi[0]
                        del sta.time[0]
                    if len(sta.time) == 0:
                        staList.remove(sta)
            sleep(0.01)

    def set_pos(self, sta, ap, dist, ang):
        x = float('%.2f' % (dist * cos(ang) + int(ap.position[0])))
        y = float('%.2f' % (dist * sin(ang) + int(ap.position[1])))
        sta.position = x, y, 0
        ConfigMobLinks(sta)
        if self.net.draw:
            try:
                sta.update_2d()
            except:
                pass
        # sta.verifyingNodes(sta)

    def calc_dist(self, sta, ap, rssi, ppm, n=32.0):
        pT = ap.wintfs[0].txpower
        gT = ap.wintfs[0].antennaGain
        gR = sta.wintfs[0].antennaGain
        if ppm in dir(self):
            dist = self.__getattribute__(ppm)(sta, ap, pT, gT, gR, rssi, n)
            return int(dist)

    @classmethod
    def pathLoss(cls, sta, ap, dist, wlan=0):
        """Path Loss Model:
        (f) signal frequency transmited(Hz)
        (d) is the distance between the transmitter and the receiver (m)
        (c) speed of light in vacuum (m)
        (L) System loss"""
        f = sta.wintfs[wlan].freq * 10 ** 9  # Convert Ghz to Hz
        c = 299792458.0
        L = 1
        if dist == 0:
            dist = 0.1
        lambda_ = c / f  # lambda: wavelength (m)
        denominator = lambda_ ** 2
        numerator = (4 * math.pi * dist) ** 2 * L
        pathLoss_ = 10 * math.log10(numerator / denominator)

        return pathLoss_

    @classmethod
    def friis(cls, sta, ap, pT, gT, gR, signalLevel, n):
        """Based on Free Space Propagation Model"""
        c = 299792458.0
        L = 2.0
        freq = sta.wintfs[0].freq * 10 ** 9  # Convert Ghz to Hz
        gains = gR + gT + pT
        lambda_ = float(c) / float(freq)  # lambda: wavelength (m)
        numerator = 10.0 ** (abs(signalLevel - gains) / 10.0)
        dist = (lambda_ / (4.0 * math.pi)) * ((numerator / L) ** (0.5))

        return dist

    def logDistance(self, sta, ap, pT, gT, gR, signalLevel, n):
        """Based on Log Distance Propagation Loss Model"""
        gains = gR + gT + pT
        ref_dist = 1
        exp = 2
        pathLossDb = self.pathLoss(sta, ap, ref_dist)
        rssi = gains - signalLevel - pathLossDb
        dist = 10 ** ((rssi + 10 * exp * math.log10(ref_dist)) / (10 * exp))

        return dist

    @classmethod
    def ITU(cls, sta, ap, pT, gT, gR, signalLevel, N):
        """Based on International Telecommunication Union (ITU) Propagation
        Loss Model"""
        lF = 0  # Floor penetration loss factor
        nFloors = 0  # Number of Floors
        gains = pT + gT + gR
        freq = sta.wintfs[0].freq * 10 ** 3
        dist = 10.0 ** ((-20.0 * math.log10(freq) - lF * nFloors + 28.0 +
                         abs(signalLevel - gains)) / N)

        return dist
