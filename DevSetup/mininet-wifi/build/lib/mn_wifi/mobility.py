"""
   Mininet-WiFi: A simple networking testbed for Wireless OpenFlow/SDWN!
   author: Ramon Fontes (ramonrf@dca.fee.unicamp.br)
"""

from threading import Thread as thread
from time import sleep, time
from os import system as sh, getpid
from glob import glob
import numpy as np
from numpy.random import rand

from mininet.log import debug
from mn_wifi.link import mesh, adhoc, ITSLink, master
from mn_wifi.associationControl import AssociationControl as AssCtrl
from mn_wifi.plot import PlotGraph
from mn_wifi.wmediumdConnector import w_cst, wmediumd_mode


class Mobility(object):
    aps = []
    stations = []
    mobileNodes = []
    ac = None  # association control method
    pause_simulation = False
    allAutoAssociation = True
    thread_ = ''

    def move_factor(self, node, diff_time):
        """:param node: node
        :param diff_time: difference between initial and final time.
        Useful for calculating the speed"""
        diff_time += 1
        init_pos = (node.params['initPos'])
        fin_pos = (node.params['finPos'])
        node.position = init_pos
        pos_x = float(fin_pos[0]) - float(init_pos[0])
        pos_y = float(fin_pos[1]) - float(init_pos[1])
        pos_z = float(fin_pos[2]) - float(init_pos[2]) if len(fin_pos) == 3 else float(0)

        pos = round(pos_x/diff_time*0.1, 2),\
              round(pos_y/diff_time*0.1, 2),\
              round(pos_z/diff_time*0.1, 2)
        return pos

    @staticmethod
    def get_position(pos):
        x = float('%s' % pos[0])
        y = float('%s' % pos[1])
        z = float('%s' % pos[2]) if len(pos) == 3 else float('%s' % 0)
        return x, y, z

    @staticmethod
    def speed(node, pos_x, pos_y, pos_z, mob_time):
        node.params['speed'] = round(abs((pos_x + pos_y + pos_z) / mob_time), 2)

    def calculate_diff_time(self, node, time=0):
        if time != 0:
            node.endTime = time
            node.endT = time
        diff_time = node.endTime - node.startTime - 1
        node.moveFac = self.move_factor(node, diff_time)

    def set_pos(self, node, pos):
        node.position = pos
        if wmediumd_mode.mode == w_cst.INTERFERENCE_MODE and self.thread_._keep_alive:
            node.set_pos_wmediumd(pos)

    def set_wifi_params(self):
        "Opens a thread for wifi parameters"
        if self.allAutoAssociation:
            thread_ = thread(name='wifiParameters', target=self.parameters)
            thread_.daemon = True
            thread_.start()

    def remove_staconf(self, intf):
        sh('rm %s_%s.staconf >/dev/null 2>&1' % (intf.node, intf.id))

    def get_pidfile(self, intf):
        pid = "mn%d_%s_%s_wpa.pid" % (getpid(), intf.node, intf.id)
        return pid

    def kill_wpasupprocess(self, intf):
        pid = self.get_pidfile(intf)
        sh('pkill -f \'wpa_supplicant -B -Dnl80211 -P %s -i %s\'' % (pid, intf.name))

    def check_if_wpafile_exist(self, intf):
        file = '%s_%s.staconf' % (intf.name, intf.id)
        if glob(file):
            self.remove_staconf(intf)

    @staticmethod
    def remove_node_in_range(intf, ap_intf):
        if ap_intf.node in intf.apsInRange:
            intf.apsInRange.pop(ap_intf.node, None)
            ap_intf.stationsInRange.pop(intf.node, None)

    def ap_out_of_range(self, intf, ap_intf):
        "When ap is out of range"
        if ap_intf == intf.associatedTo:
            if ap_intf.encrypt and not ap_intf.ieee80211r:
                if ap_intf.encrypt == 'wpa' and not ap_intf.ieee80211r:
                    self.kill_wpasupprocess(intf)
                    self.check_if_wpafile_exist(intf)
            elif wmediumd_mode.mode == w_cst.SNR_MODE:
                intf.setSNRWmediumd(ap_intf, -10)
            if not ap_intf.ieee80211r:
                intf.disconnect(ap_intf)
            self.remove_node_in_range(intf, ap_intf)
        elif not intf.associatedTo:
            intf.rssi = 0

    def ap_in_range(self, intf, ap, dist):
        for ap_intf in ap.wintfs.values():
            if isinstance(ap_intf, master):
                rssi = intf.get_rssi(ap_intf, dist)
                intf.apsInRange[ap_intf.node] = rssi
                ap_intf.stationsInRange[intf.node] = rssi
                if ap_intf == intf.associatedTo:
                    if intf not in ap_intf.associatedStations:
                        ap_intf.associatedStations.append(intf)
                    if dist >= 0.01:
                        if intf.bgscan_module or (intf.active_scan
                                                  and intf.encrypt == 'wpa'):
                            pass
                        else:
                            intf.rssi = rssi
                            # send rssi to hwsim
                            if hasattr(intf.node, 'phyid'):
                                intf.rec_rssi()
                            if wmediumd_mode.mode != w_cst.WRONG_MODE:
                                if wmediumd_mode.mode == w_cst.SNR_MODE:
                                    intf.setSNRWmediumd(ap_intf, intf.rssi-(-91))
                            else:
                                if hasattr(intf.node, 'pos') and intf.node.position != intf.node.pos:
                                    intf.node.pos = intf.node.position
                                    intf.configWLink(dist)

    def check_in_range(self, intf, ap_intf):
        dist = intf.node.get_distance_to(ap_intf.node)
        if dist > ap_intf.range:
            self.ap_out_of_range(intf, ap_intf)
            return 0
        return 1

    def set_handover(self, intf, aps):
        for ap in aps:
            dist = intf.node.get_distance_to(ap)
            for ap_wlan, ap_intf in enumerate(ap.wintfs.values()):
                self.do_handover(intf, ap_intf)
            self.ap_in_range(intf, ap, dist)

    @staticmethod
    def check_if_ap_exists(intf, ap_intf):
        for wlan in intf.node.wintfs.values():
            if wlan.associatedTo == ap_intf:
                return 0
        return 1

    def do_handover(self, intf, ap_intf):
        "Association Control: mechanisms that optimize the use of the APs"
        changeAP = False
        if self.ac and intf.associatedTo and ap_intf.node != intf.associatedTo:
            changeAP = AssCtrl(intf, ap_intf, self.ac).changeAP
        if self.check_if_ap_exists(intf, ap_intf):
            if not intf.associatedTo or changeAP:
                if ap_intf.node != intf.associatedTo:
                    intf.associate_infra(ap_intf)

    def parameters(self):
        "Applies channel params and handover"
        mob_nodes = list(set(self.mobileNodes) - set(self.aps))
        while self.thread_._keep_alive:
            self.config_links(mob_nodes)

    def associate_interference_mode(self, intf, ap_intf):
        if intf.bgscan_module or (intf.active_scan and 'wpa' in intf.encrypt):
            if not intf.associatedTo:
                intf.associate_infra(ap_intf)
                intf.associatedTo = 'bgscan' if intf.bgscan_module else 'active_scan'
            return 0

        return self.check_in_range(intf, ap_intf)

    def config_links(self, nodes):
        for node in nodes:
            for intf in node.wintfs.values():
                if isinstance(intf, adhoc) or isinstance(intf, mesh) or isinstance(intf, ITSLink):
                    pass
                else:
                    aps = []
                    for ap in self.aps:
                        for ap_intf in ap.wintfs.values():
                            if not isinstance(ap_intf, adhoc) and not isinstance(ap_intf, mesh):
                                if wmediumd_mode.mode == w_cst.INTERFERENCE_MODE:
                                    ack = self.associate_interference_mode(intf, ap_intf)
                                else:
                                    ack = self.check_in_range(intf, ap_intf)
                                if ack and ap not in aps:
                                    aps.append(ap)
                    self.set_handover(intf, aps)
        sleep(0.0001)


class ConfigMobility(Mobility):

    def __init__(self, *args, **kwargs):
        self.config_mobility(*args, **kwargs)

    def config_mobility(self, *args, **kwargs):
        'configure Mobility Parameters'
        node = args[0]
        stage = args[1]

        if stage == 'start':
            pos = kwargs['position'].split(',') if 'position' in kwargs \
                else node.coord[0].split(',')
            node.params['initPos'] = self.get_position(pos)
            node.startTime = kwargs['time']
        elif stage == 'stop':
            pos = kwargs['position'].split(',') if 'position' in kwargs \
                else node.coord[1].split(',')
            node.params['finPos'] = self.get_position(pos)
            node.speed = 1
            self.calculate_diff_time(node, kwargs['time'])


class ConfigMobLinks(Mobility):

    def __init__(self, node=None):
        self.config_mob_links(node)

    def config_mob_links(self, node):
        "Applies channel params and handover"
        from mn_wifi.node import AP
        if node:
            if isinstance(node, AP) or node in self.aps:
                nodes = self.stations
            else:
                nodes = [node]
        else:
            nodes = self.stations
        self.config_links(nodes)


class model(Mobility):

    def __init__(self, **kwargs):
        self.start_thread(**kwargs)

    def start_thread(self, **kwargs):
        debug('Starting mobility thread...\n')
        Mobility.thread_ = thread(name='mobModel', target=self.models, kwargs=kwargs)
        Mobility.thread_.daemon = True
        Mobility.thread_._keep_alive = True
        Mobility.thread_.start()
        self.set_wifi_params()

    def models(self, stations=None, aps=None, stat_nodes=None, mob_nodes=None,
               draw=False, seed=1, mob_model='RandomWalk',
               min_wt=1, max_wt=5, max_x=100, max_y=100, **kwargs):
        "Used when a mobility model is set"
        np.random.seed(seed)
        self.ac = kwargs.get('ac_method', None)
        n_groups = kwargs.get('n_groups', 1)
        self.stations, self.mobileNodes, self.aps = stations, stations, aps

        for node in mob_nodes:
            args = {'min_x': 0, 'min_y': 0,
                    'max_x': max_x, 'max_y': max_y,
                    'min_v': 10, 'max_v': 10}
            for key in args.keys():
                setattr(node, key, node.params.get(key, args[key]))

        if draw:
            nodes = mob_nodes + stat_nodes
            PlotGraph(nodes=nodes, max_x=max_x, max_y=max_y, **kwargs)

        if not mob_nodes:
            if draw:
                PlotGraph.pause()
            return

        debug('Configuring the mobility model %s\n' % mob_model)
        if mob_model == 'RandomWalk':  # Random Walk model
            for node in mob_nodes:
                array_ = ['constantVelocity', 'constantDistance']
                for param in array_:
                    if not hasattr(node, param):
                        setattr(node, param, 1)
            mob = random_walk(mob_nodes)
        elif mob_model == 'TruncatedLevyWalk':  # Truncated Levy Walk model
            mob = truncated_levy_walk(mob_nodes)
        elif mob_model == 'RandomDirection':  # Random Direction model
            mob = random_direction(mob_nodes, dimensions=(max_x, max_y))
        elif mob_model == 'RandomWayPoint':  # Random Waypoint model
            for node in mob_nodes:
                array_ = ['constantVelocity', 'constantDistance',
                          'min_v', 'max_v']
                for param in array_:
                    if not hasattr(node, param):
                        setattr(node, param, '1')
            mob = random_waypoint(mob_nodes, wt_min=min_wt, wt_max=max_wt)
        elif mob_model == 'GaussMarkov':  # Gauss-Markov model
            mob = gauss_markov(mob_nodes, alpha=0.99)
        elif mob_model == 'ReferencePoint':  # Reference Point Group model
            mob = reference_point_group(mob_nodes, n_groups,
                                        dimensions=(max_x, max_y),
                                        aggregation=0.5)
        elif mob_model == 'TimeVariantCommunity':
            mob = tvc(mob_nodes, n_groups, dimensions=(max_x, max_y),
                      aggregation=[0.5, 0.], epoch=[100, 100])
        elif mob_model == 'CRP':
            mob = coherence_ref_point(mob_nodes, n_groups, (max_x, max_y),
                                      kwargs['pointlist'])
        else:
            raise Exception("Mobility Model not defined or doesn't exist!")

        current_time = time()
        while (time() - current_time) < kwargs['mob_start_time']:
            pass

        self.start_mob_mod(mob, mob_nodes, draw)

    def start_mob_mod(self, mob, nodes, draw):
        """
        :param mob: mobility params
        :param nodes: list of nodes
        """
        for xy in mob:
            for idx, node in enumerate(nodes):
                pos = round(xy[idx][0], 2), round(xy[idx][1], 2), 0.0
                self.set_pos(node, pos)
                if draw:
                    node.update_2d()
            if draw:
                PlotGraph.pause()
            else:
                sleep(0.5)
            while self.pause_simulation:
                pass


class Tracked(Mobility):
    "Used when the position of each node is previously defined"

    def __init__(self, **kwargs):
        self.start_thread(**kwargs)

    def start_thread(self, **kwargs):
        debug('Starting mobility thread...\n')
        Mobility.thread_ = thread(target=self.configure, kwargs=kwargs)
        Mobility.thread_.daemon = True
        Mobility.thread_._keep_alive = True
        Mobility.thread_.start()
        self.set_wifi_params()

    def configure(self, stations, aps, stat_nodes, mob_nodes,
                  draw, **kwargs):
        self.ac = kwargs.get('ac_method', None)
        self.stations = stations
        self.aps = aps
        self.mobileNodes = mob_nodes
        nodes = stations + aps

        for node in mob_nodes:
            node.position = node.params['initPos']
            node.matrix_id = 0
            node.time = node.startTime

        dim = 'update_2d'
        if draw:
            kwargs['nodes'] = stat_nodes + mob_nodes
            PlotGraph(**kwargs)
            if hasattr(PlotGraph, 'plot3d'):
                dim = 'update_3d'

        coordinate = {}
        for node in nodes:
            if hasattr(node, 'coord'):
                coordinate[node] = self.set_coordinates(node)
        self.run(mob_nodes, draw, coordinate, dim, **kwargs)

    def run(self, mob_nodes, draw, coordinate, dim, mob_start_time=0,
            mob_stop_time=10, reverse=False, mob_rep=1, **kwargs):

        for rep in range(mob_rep):
            t1 = time()
            i = 0.1
            if reverse:
                for node in mob_nodes:
                    if rep % 2 == 1 or (rep % 2 == 0 and rep > 0):
                        fin_pos = node.params['finPos']
                        node.params['finPos'] = node.params['initPos']
                        node.params['initPos'] = fin_pos

            if not coordinate:
                coordinate = {}
                for node in mob_nodes:
                    self.calculate_diff_time(node)
                    coordinate[node] = self.create_coord(node, tracked=True)

            while mob_start_time <= time() - t1 <= mob_stop_time:
                t2 = time()
                if t2 - t1 >= i:
                    for node, pos in coordinate.items():
                        if (t2 - t1) >= node.startTime and node.time <= node.endTime:
                            node.matrix_id += 1
                            if node.matrix_id < len(coordinate[node]):
                                pos = pos[node.matrix_id]
                            else:
                                pos = pos[len(coordinate[node]) - 1]
                            self.set_pos(node, pos)
                            node.time += 0.1
                            if draw:
                                node_update = getattr(node, dim)
                                node_update()
                    PlotGraph.pause()
                    i += 0.1
                while self.pause_simulation:
                    pass
            if rep == mob_rep:
                self.thread_._keep_alive = False

    @staticmethod
    def get_total_displacement(node):
        x, y, z = 0, 0, 0
        for num, coord in enumerate(node.coord):
            if num > 0:
                c0 = node.coord[num].split(',')
                c1 = node.coord[num-1].split(',')
                x += abs(float(c0[0]) - float(c1[0]))
                y += abs(float(c0[1]) - float(c1[1]))
                z += abs(float(c0[2]) - float(c1[2]))
        return (x, y, z)

    def create_coord(self, node, tracked=False):
        coord = []
        if tracked:
            pos = node.position
            for _ in range((node.endTime - node.startTime) * 10):
                x = round(pos[0], 2) + round(node.moveFac[0], 2)
                y = round(pos[1], 2) + round(node.moveFac[1], 2)
                z = round(pos[2], 2) + round(node.moveFac[2], 2) if len(pos)==3 else 0
                pos = (x, y, z)
                coord.append((x, y, z))
        else:
            for idx in range(len(node.coord) - 1):
                coord.append([node.coord[idx], node.coord[idx + 1]])
        return coord

    def dir(self, p1, p2):
        if p1 > p2:
            return False
        return True

    def mob_time(self, node):
        t1 = node.startTime
        if hasattr(node, 'time'):
            t1 = node.time
        t2 = node.endTime
        t = t2 - t1
        return t

    def get_points(self, node, a0, a1, total):
        x1, y1 = float(a0[0]), float(a0[1])
        z1 = float(a0[2]) if len(a0) > 2 else float(0)
       
        x2, y2 = float(a1[0]), float(a1[1])
        z2 = float(a1[2]) if len(a1) > 2 else float(0)
        points = []
        perc_dif = []
        ldelta = [0, 0, 0]
        faxes = [x1, y1, z1]  # first reference point
        laxes = [x2, y2, z2]  # last refence point
        dif = [abs(x2-x1), abs(y2-y1), abs(z2-z1)]   # difference first and last axes
        for n in dif:
            if n == 0:
                perc_dif.append(0)
            else:
                # we get the difference among axes to calculate the speed
                perc_dif.append((n * 100) / total[dif.index(n)])

        dmin = min(x for x in perc_dif if x != 0)
        t = self.mob_time(node) * 1000  # node simulation time
        dt = t * (dmin / 100)

        for n in perc_dif:
            if n != 0:
                ldelta[perc_dif.index(n)] = dif[perc_dif.index(n)] / dt

        # direction of the node
        dir = (self.dir(x1, x2), self.dir(y1, y2), self.dir(z1, z2))

        for n in np.arange(0, dt, 1):
            for delta in ldelta:
                if dir[ldelta.index(delta)]:
                    if n < dt - 1:
                        faxes[ldelta.index(delta)] += delta
                    else:
                        faxes[ldelta.index(delta)] = laxes[ldelta.index(delta)]
                else:
                    if n < dt - 1:
                        faxes[ldelta.index(delta)] -= delta
                    else:
                        faxes[ldelta.index(delta)] = laxes[ldelta.index(delta)]
            points.append(self.get_position(faxes))
        return points

    def set_coordinates(self, node):
        coord = self.create_coord(node)
        total = self.get_total_displacement(node)
        points = []
        for c in coord:
            a0 = c[0].split(',')
            a1 = c[1].split(',')
            points += (self.get_points(node, a0, a1, total))

        t = self.mob_time(node) * 10
        interval = len(points) / t
        pointsL = []
        for id in np.arange(0, len(points), interval):
            if id < len(points) - interval:
                pointsL.append(points[int(id)])
            else:
                # set the last position according to the coordinates
                pointsL.append(points[int(len(points)-1)])
        return pointsL


# coding: utf-8
#
#  Copyright (C) 2008-2010 Istituto per l'Interscambio Scientifico I.S.I.
#  You can contact us by email (isi@isi.it) or write to:
#  ISI Foundation, Viale S. Severo 65, 10133 Torino, Italy.
#
#  This program was written by Andre Panisson <panisson@gmail.com>
#
'''
Created on Jan 24, 2012
Modified by Ramon Fontes (ramonrf@dca.fee.unicamp.br)
@author: Andre Panisson
@contact: panisson@gmail.com
@organization: ISI Foundation, Torino, Italy
@source: https://github.com/panisson/pymobility
@copyright: http://dx.doi.org/10.5281/zenodo.9873
'''

# define a Uniform Distribution
U = lambda MIN, MAX, SAMPLES: rand(*SAMPLES.shape) * (MAX - MIN) + MIN

# define a Truncated Power Law Distribution
P = lambda ALPHA, MIN, MAX, SAMPLES: ((MAX ** (ALPHA + 1.) - 1.) * \
                                      rand(*SAMPLES.shape) + 1.) ** (1. / (ALPHA + 1.))

# define an Exponential Distribution
E = lambda SCALE, SAMPLES: -SCALE * np.log(rand(*SAMPLES.shape))


# *************** Palm state probability **********************
def pause_probability_init(wt_min, wt_max, min_v,
                           max_v, dimensions):
    np.seterr(divide='ignore', invalid='ignore')
    alpha1 = ((wt_max + wt_min) * (max_v - min_v)) / \
             (2 * np.log(max_v / min_v))
    delta1 = np.sqrt(np.sum(np.square(dimensions)))
    return alpha1 / (alpha1 + delta1)

# *************** Palm residual ******************************
def residual_time(mean, delta, shape=(1,)):
    t1 = mean - delta
    t2 = mean + delta
    u = rand(*shape)
    residual = np.zeros(shape)
    if delta != 0.0:
        case_1_u = u < (2. * t1 / (t1 + t2))
        residual[case_1_u] = u[case_1_u] * (t1 + t2) / 2.
        residual[np.logical_not(case_1_u)] = \
            t2 - np.sqrt((1. - u[np.logical_not(case_1_u)]) * (t2 * t2 - t1 * t1))
    else:
        residual = u * mean
    return residual


# *********** Initial speed ***************************
def initial_speed(speed_mean, speed_delta, shape=(1,)):
    v0 = speed_mean - speed_delta
    v1 = speed_mean + speed_delta
    u = rand(*shape)
    return pow(v1, u) / pow(v0, u - 1)


def init_random_waypoint(nr_nodes, dimensions, min_v, max_v,
                         wt_min, wt_max):

    x = np.empty(nr_nodes)
    y = np.empty(nr_nodes)
    x_waypoint = np.empty(nr_nodes)
    y_waypoint = np.empty(nr_nodes)
    speed = np.empty(nr_nodes)
    pause_time = np.empty(nr_nodes)
    moving = np.ones(nr_nodes)
    speed_mean, speed_delta = (min_v + max_v) / 2., (max_v - min_v) / 2.
    pause_mean, pause_delta = (wt_min + wt_max) / 2., (wt_max - wt_min) / 2.

    # steady-state pause probability for Random Waypoint
    q0 = pause_probability_init(wt_min, wt_max, min_v, max_v, dimensions)

    max_x = dimensions[0]
    max_y = dimensions[1]
    for i in range(nr_nodes):
        while True:
            if rand() < q0[i]:
                # moving[i] = 0.
                # speed_mean = np.delete(speed_mean, i)
                # speed_delta = np.delete(speed_delta, i)
                # M_0
                x1 = rand() * max_x[i]
                x2 = rand() * max_x[i]
                # M_1
                y1 = rand() * max_y[i]
                y2 = rand() * max_y[i]
                break

            # M_0
            x1 = rand() * max_x[i]
            x2 = rand() * max_x[i]
            # M_1
            y1 = rand() * max_y[i]
            y2 = rand() * max_y[i]

            # r is a ratio of the length of the randomly chosen path over
            # the length of a diagonal across the simulation area
            r = np.sqrt(((x2 - x1) * (x2 - x1) +
                         (y2 - y1) * (y2 - y1)) / \
                        (max_x[i] * max_x[i] +
                         max_y[i] * max_y[i]))
            if rand() < r:
                moving[i] = 1.
                break

        x[i] = x1
        y[i] = y1

        x_waypoint[i] = x2
        y_waypoint[i] = y2

    # steady-state positions
    # initially the node has traveled a proportion u2 of the path from (x1,y1) to (x2,y2)
    u2 = rand(*x.shape)
    x[:] = u2 * x + (1 - u2) * x_waypoint
    y[:] = u2 * y + (1 - u2) * y_waypoint

    # steady-state speed and pause time
    paused_bool = moving == 0.
    paused_idx = np.where(paused_bool)[0]
    pause_time[paused_idx] = residual_time(pause_mean, pause_delta, paused_idx.shape)
    speed[paused_idx] = 0.0

    moving_bool = np.logical_not(paused_bool)
    moving_idx = np.where(moving_bool)[0]
    pause_time[moving_idx] = 0.0
    speed[moving_idx] = initial_speed(speed_mean, speed_delta, moving_idx.shape)

    return x, y, x_waypoint, y_waypoint, speed, pause_time


class RandomWaypoint(object):
    def __init__(self, nodes, wt_min=None, wt_max=None):
        """
        Random Waypoint model.
        Required arguments:
          *nr_nodes*:
            Integer, the number of nodes.
          *dimensions*:
            Tuple of Integers, the x and y dimensions of the simulation area.
        keyword arguments:
          *velocity*:
            Tuple of Integers, the minimum and maximum values for node velocity.
          *wt_max*:
            Integer, the maximum wait time for node pauses.
            If wt_max is 0 or None, there is no pause time.
        """
        self.nodes = nodes
        self.nr_nodes = len(nodes)
        self.wt_min = wt_min
        self.wt_max = wt_max
        self.init_stationary = True

    def __iter__(self):

        NODES = np.arange(self.nr_nodes)

        MAX_V = U(0, 0, NODES)
        MIN_V = U(0, 0, NODES)
        MAX_X = U(0, 0, NODES)
        MAX_Y = U(0, 0, NODES)
        MIN_X = U(0, 0, NODES)
        MIN_Y = U(0, 0, NODES)

        for node in range(self.nr_nodes):
            MAX_V[node] = self.nodes[node].max_v / 10.
            MIN_V[node] = self.nodes[node].min_v / 10.
            MAX_X[node] = self.nodes[node].max_x
            MAX_Y[node] = self.nodes[node].max_y
            MIN_X[node] = self.nodes[node].min_x
            MIN_Y[node] = self.nodes[node].min_y

        dimensions = (MAX_X, MAX_Y)

        if self.init_stationary:
            x, y, x_waypoint, y_waypoint, velocity, wt = \
                init_random_waypoint(self.nr_nodes, dimensions,
                                     MIN_V, MAX_V, self.wt_min, self.wt_max)

        else:
            NODES = np.arange(self.nr_nodes)
            x = U(MIN_X, MAX_X, NODES)
            y = U(MIN_Y, MAX_Y, NODES)
            x_waypoint = U(MIN_X, MAX_X, NODES)
            y_waypoint = U(MIN_Y, MAX_Y, NODES)
            wt = np.zeros(self.nr_nodes)
            velocity = U(MIN_V, MAX_V, NODES)

        theta = np.arctan2(y_waypoint - y, x_waypoint - x)
        costheta = np.cos(theta)
        sintheta = np.sin(theta)

        while True:
            # update node position
            x += velocity * costheta
            y += velocity * sintheta

            # calculate distance to waypoint
            d = np.sqrt(np.square(y_waypoint - y) + np.square(x_waypoint - x))
            # update info for arrived nodes
            arrived = np.where(np.logical_and(d <= velocity, wt <= 0.))[0]

            # step back for nodes that surpassed waypoint
            x[arrived] = x_waypoint[arrived]
            y[arrived] = y_waypoint[arrived]

            if self.wt_max:
                velocity[arrived] = 0.
                wt[arrived] = U(self.wt_min, self.wt_max, arrived)
                # update info for paused nodes
                wt[np.where(velocity == 0.)[0]] -= 1.
                # update info for moving nodes
                arrived = np.where(np.logical_and(velocity == 0., wt < 0.))[0]

            if arrived.size > 0 and len(arrived) == 1:
                wx = U(MIN_X, MAX_X, arrived)
                x_waypoint[arrived] = wx[arrived]
                wy = U(MIN_Y, MAX_Y, arrived)
                y_waypoint[arrived] = wy[arrived]
                v = U(MIN_V, MAX_V, arrived)
                velocity[arrived] = v[arrived]
                theta[arrived] = np.arctan2(y_waypoint[arrived] - y[arrived],
                                            x_waypoint[arrived] - x[arrived])
                costheta[arrived] = np.cos(theta[arrived])
                sintheta[arrived] = np.sin(theta[arrived])

            self.velocity = velocity
            self.wt = wt
            yield np.dstack((x, y))[0]


class StochasticWalk(object):
    def __init__(self, nodes, FL_DISTR, VEL_DISTR, WT_DISTR=None,
                 border_policy='reflect', model=None):
        """
        Base implementation for models with direction uniformly chosen from [0,pi]:
        random_direction, random_walk, truncated_levy_walk
        Required arguments:
          *nr_nodes*:
            Integer, the number of nodes.
          *dimensions*:
            Tuple of Integers, the x and y dimensions of the simulation area.
          *FL_DISTR*:
            A function that, given a set of samples,
             returns another set with the same size of the input set.
            This function should implement the distribution of flight lengths
             to be used in the model.
          *VEL_DISTR*:
            A function that, given a set of flight lengths,
             returns another set with the same size of the input set.
            This function should implement the distribution of velocities
             to be used in the model, as random or as a function of the flight
             lengths.
        keyword arguments:
          *WT_DISTR*:
            A function that, given a set of samples,
             returns another set with the same size of the input set.
            This function should implement the distribution of wait times
             to be used in the node pause.
            If WT_DISTR is 0 or None, there is no pause time.
          *border_policy*:
            String, either 'reflect' or 'wrap'. The policy that is used when
            the node arrives to the border.
            If 'reflect', the node reflects off the border.
            If 'wrap', the node reappears at the opposite edge
            (as in a torus-shaped area).
        """
        self.b = [0]
        self.nodes = nodes
        self.collect_fl_stats = False
        self.collect_wt_stats = False
        self.border_policy = border_policy
        self.nr_nodes = len(nodes)
        self.FL_DISTR = FL_DISTR
        self.VEL_DISTR = VEL_DISTR
        self.WT_DISTR = WT_DISTR
        self.model = model

    def __iter__(self):
        def reflect(xy):
            # node bounces on the margins
            b = np.where(xy[:, 0] < MIN_X)[0]
            if b.size > 0:
                xy[b, 0] = 2 * MIN_X[b] - xy[b, 0]
                cosintheta[b, 0] = -cosintheta[b, 0]
            b = np.where(xy[:, 0] > MAX_X)[0]
            if b.size > 0:
                xy[b, 0] = 2 * MAX_X[b] - xy[b, 0]
                cosintheta[b, 0] = -cosintheta[b, 0]
            b = np.where(xy[:, 1] < MIN_Y)[0]
            if b.size > 0:
                xy[b, 1] = 2 * MIN_Y[b] - xy[b, 1]
                cosintheta[b, 1] = -cosintheta[b, 1]
            b = np.where(xy[:, 1] > MAX_Y)[0]
            if b.size > 0:
                xy[b, 1] = 2 * MAX_Y[b] - xy[b, 1]
                cosintheta[b, 1] = -cosintheta[b, 1]
            self.b = b

        def wrap(xy):
            b = np.where(xy[:, 0] < MIN_X)[0]
            if b.size > 0: xy[b, 0] += MAX_X[b]
            b = np.where(xy[:, 0] > MAX_X)[0]
            if b.size > 0: xy[b, 0] -= MAX_X[b]
            b = np.where(xy[:, 1] < MIN_Y)[0]
            if b.size > 0: xy[b, 1] += MAX_Y[b]
            b = np.where(xy[:, 1] > MAX_Y)[0]
            if b.size > 0: xy[b, 1] -= MAX_Y[b]
            self.b = b

        if self.border_policy == 'reflect':
            borderp = reflect
        elif self.border_policy == 'wrap':
            borderp = wrap
        else:
            borderp = self.border_policy

        NODES = np.arange(self.nr_nodes)

        MAX_X = U(0, 0, NODES)
        MAX_Y = U(0, 0, NODES)
        MIN_X = U(0, 0, NODES)
        MIN_Y = U(0, 0, NODES)

        for node in range(len(self.nodes)):
            MAX_X[node] = self.nodes[node].max_x
            MAX_Y[node] = self.nodes[node].max_y
            MIN_X[node] = self.nodes[node].min_x
            MIN_Y[node] = self.nodes[node].min_y

        xy = U(0, MAX_X[self.b], np.dstack((NODES, NODES))[0])
        fl = self.FL_DISTR(NODES)
        velocity = self.VEL_DISTR(fl)
        theta = U(0, 1.8 * np.pi, NODES)
        cosintheta = np.dstack((np.cos(theta), np.sin(theta)))[0] * \
                     np.dstack((velocity, velocity))[0]
        wt = np.zeros(self.nr_nodes)

        if self.collect_fl_stats: self.fl_stats = list(fl)
        if self.collect_wt_stats: self.wt_stats = list(wt)

        while True:
            xy += cosintheta
            fl -= velocity

            # step back for nodes that surpassed fl
            arrived = np.where(np.logical_and(velocity > 0., fl <= 0.))[0]

            if arrived.size > 0:
                diff = fl.take(arrived) / velocity.take(arrived)
                xy[arrived] += np.dstack((diff, diff))[0] * cosintheta[arrived]

            # apply border policy
            borderp(xy)

            if self.WT_DISTR:
                velocity[arrived] = 0.
                wt[arrived] = self.WT_DISTR(arrived)
                if self.collect_wt_stats: self.wt_stats.extend(wt[arrived])
                # update info for paused nodes
                wt[np.where(velocity == 0.)[0]] -= 1.
                arrived = np.where(np.logical_and(velocity == 0., wt < 0.))[0]

            # update info for moving nodes
            if arrived.size > 0:
                theta = U(0, 2 * np.pi, arrived)
                fl[arrived] = self.FL_DISTR(arrived)
                if self.collect_fl_stats: self.fl_stats.extend(fl[arrived])
                if self.model == 'RandomDirection':
                    velocity[arrived] = self.VEL_DISTR(fl[arrived][0])[arrived]
                elif self.model == 'TruncatedLevyWalk':
                    velocity[arrived] = self.VEL_DISTR(fl[arrived])
                else:
                    velocity[arrived] = self.VEL_DISTR(fl[arrived])[arrived]
                v = velocity[arrived]
                cosintheta[arrived] = np.dstack((v * np.cos(theta),
                                                 v * np.sin(theta)))[0]
            yield xy


class RandomWalk(StochasticWalk):
    def __init__(self, nodes, border_policy='reflect'):
        """
        Random Walk mobility model.
        This model is based in the Stochastic Walk, but both the flight
        length and node velocity distributions are in fact constants,
        set to the *distance* and *velocity* parameters. The waiting time
        is set to None.
        Required arguments:
          *nr_nodes*:
            Integer, the number of nodes.
        keyword arguments:
          *velocity*:
            Double, the value for the constant node velocity. Default is 1.0
          *distance*:
            Double, the value for the constant distance traveled in each step.
            Default is 1.0
          *border_policy*:
            String, either 'reflect' or 'wrap'. The policy that is used when the
            node arrives to the border.
            If 'reflect', the node reflects off the border.
            If 'wrap', the node reappears at the opposite edge
            (as in a torus-shaped area).
        """
        nr_nodes = len(nodes)
        NODES = np.arange(nr_nodes)
        VELOCITY = U(0, 0, NODES)
        velocity = VELOCITY
        distance = VELOCITY

        for node in range(len(nodes)):
            velocity[node] = nodes[node].constantVelocity
            distance[node] = nodes[node].constantDistance

            if velocity[node] > distance[node]:
                # In this implementation, each step is 1 second,
                # it is not possible to have a velocity larger than the distance
                raise Exception('Velocity must be <= Distance')

        fl = np.zeros(nr_nodes) + distance
        vel = np.zeros(nr_nodes) + velocity

        FL_DISTR = lambda SAMPLES: np.array(fl[:len(SAMPLES)])
        VEL_DISTR = lambda FD: np.array(vel[:len(FD)])

        StochasticWalk.__init__(self, nodes, FL_DISTR, VEL_DISTR,
                                border_policy=border_policy)


class RandomDirection(StochasticWalk):
    def __init__(self, nodes, dimensions, wt_max=None, border_policy='reflect'):
        """
        Random Direction mobility model.
        This model is based in the Stochastic Walk. The flight length is chosen
        from a uniform distribution, with minimum 0 and maximum set to the maximum
        dimension value. The velocity is also chosen from a uniform distribution,
        with boundaries set by the *velocity* parameter.
        If wt_max is set, the waiting time is chosen from a uniform distribution
        with values between 0 and wt_max. If wt_max is not set, waiting time is
        set to None.
        Required arguments:
          *nr_nodes*:
            Integer, the number of nodes.
          *dimensions*:
            Tuple of Integers, the x and y dimensions of the simulation area.
        keyword arguments:
          *wt_max*:
            Double, maximum value for the waiting time distribution.
            If wt_max is set, the waiting time is chosen from a uniform
            distribution with values between 0 and wt_max.
            If wt_max is not set, the waiting time is set to None.
            Default is None.
          *border_policy*:
            String, either 'reflect' or 'wrap'. The policy that is used
            when the node arrives to the border. If 'reflect', the node reflects
            off the border. If 'wrap', the node reappears at the opposite edge
            (as in a torus-shaped area).
        """
        nr_nodes = len(nodes)
        NODES = np.arange(nr_nodes)

        max_v = U(0, 0, NODES)
        min_v = U(0, 0, NODES)

        MAX_V = max_v
        MIN_V = min_v

        for node in range(len(nodes)):
            MAX_V[node] = nodes[node].max_v / 10.
            MIN_V[node] = nodes[node].min_v / 10.

        FL_MAX = max(dimensions)

        FL_DISTR = lambda SAMPLES: U(0, FL_MAX, SAMPLES)
        if wt_max:
            WT_DISTR = lambda SAMPLES: U(0, wt_max, SAMPLES)
        else:
            WT_DISTR = None
        VEL_DISTR = lambda FD: U(MIN_V, MAX_V, FD)

        StochasticWalk.__init__(self, nodes, FL_DISTR, VEL_DISTR,
                                WT_DISTR, border_policy, model='RandomDirection')


class TruncatedLevyWalk(StochasticWalk):
    def __init__(self, nodes, FL_EXP=-2.6, FL_MAX=50., WT_EXP=-1.8,
                 WT_MAX=100., border_policy='reflect'):
        """
        Truncated Levy Walk mobility model, based on the following paper:
        Injong Rhee, Minsu Shin, Seongik Hong, Kyunghan Lee, and Song Chong.
        On the Levy-Walk Nature of Human Mobility.
            In 2008 IEEE INFOCOM - Proceedings of the 27th Conference on Computer
            Communications, pages 924-932. April 2008.
        The implementation is a special case of the more generic Stochastic Walk,
        in which both the flight length and waiting time distributions are
        truncated power laws, with exponents set to FL_EXP and WT_EXP and
        truncated at FL_MAX and WT_MAX. The node velocity is a function of the
        flight length.
        Required arguments:
          *nr_nodes*:
            Integer, the number of nodes.
        keyword arguments:
          *FL_EXP*:
            Double, the exponent of the flight length distribution.
            Default is -2.6
          *FL_MAX*:
            Double, the maximum value of the flight length distribution.
            Default is 50
          *WT_EXP*:
            Double, the exponent of the waiting time distribution.
            Default is -1.8
          *WT_MAX*:
            Double, the maximum value of the waiting time distribution.
            Default is 100
          *border_policy*:
            String, either 'reflect' or 'wrap'. The policy that is used when the
            node arrives to the border. If 'reflect', the node reflects off the
            border. If 'wrap', the node reappears at the opposite edge (as in a
            torus-shaped area).
        """
        FL_DISTR = lambda SAMPLES: P(FL_EXP, 1., FL_MAX, SAMPLES)
        if WT_EXP and WT_MAX:
            WT_DISTR = lambda SAMPLES: P(WT_EXP, 1., WT_MAX, SAMPLES)
        else:
            WT_DISTR = None
        VEL_DISTR = lambda FD: np.sqrt(FD) / 10.

        StochasticWalk.__init__(self, nodes, FL_DISTR, VEL_DISTR,
                                WT_DISTR, border_policy, model='TruncatedLevyWalk')


class HeterogeneousTruncatedLevyWalk(StochasticWalk):
    def __init__(self, nodes, dimensions, WT_EXP=-1.8, WT_MAX=100.,
                 FL_EXP=-2.6, FL_MAX=50., border_policy='reflect'):
        """
        This is a variant of the Truncated Levy Walk mobility model.
        This model is based in the Stochastic Walk.
        The waiting time distribution is a truncated power law with exponent
        set to WT_EXP and truncated WT_MAX. The flight length is a uniform
        distribution, different for each node. These uniform distributions are
        created by taking both min and max values from a power law with exponent
        set to FL_EXP and truncated FL_MAX. The node velocity is a function of
        the flight length.
        Required arguments:
          *nr_nodes*:
            Integer, the number of nodes.
          *dimensions*:
            Tuple of Integers, the x and y dimensions of the simulation area.
        keyword arguments:
          *WT_EXP*:
            Double, the exponent of the waiting time distribution.
             Default is -1.8
          *WT_MAX*:
            Double, the maximum value of the waiting time distribution.
            Default is 100
          *FL_EXP*:
            Double, the exponent of the flight length distribution.
            Default is -2.6
          *FL_MAX*:
            Double, the maximum value of the flight length distribution.
            Default is 50
          *border_policy*:
            String, either 'reflect' or 'wrap'. The policy that is used when
            the node arrives to the border. If 'reflect', the node reflects off
            the border. If 'wrap', the node reappears at the opposite edge
            (as in a torus-shaped area).
        """
        nr_nodes = len(nodes)
        NODES = np.arange(nr_nodes)
        FL_MAX = P(-1.8, 10., FL_MAX, NODES)
        FL_MIN = FL_MAX / 10.

        FL_DISTR = lambda SAMPLES: rand(len(SAMPLES)) * \
                                   (FL_MAX[SAMPLES] - FL_MIN[SAMPLES]) + \
                                   FL_MIN[SAMPLES]
        WT_DISTR = lambda SAMPLES: P(WT_EXP, 1., WT_MAX, SAMPLES)
        VEL_DISTR = lambda FD: np.sqrt(FD) / 10.

        StochasticWalk.__init__(self, nr_nodes, dimensions, FL_DISTR,
                                VEL_DISTR, WT_DISTR=WT_DISTR,
                                border_policy=border_policy)


def random_waypoint(*args, **kwargs):
    return iter(RandomWaypoint(*args, **kwargs))


def stochastic_walk(*args, **kwargs):
    return iter(StochasticWalk(*args, **kwargs))


def random_walk(*args, **kwargs):
    return iter(RandomWalk(*args, **kwargs))


def random_direction(*args, **kwargs):
    return iter(RandomDirection(*args, **kwargs))


def truncated_levy_walk(*args, **kwargs):
    return iter(TruncatedLevyWalk(*args, **kwargs))


def heterogeneous_truncated_levy_walk(*args, **kwargs):
    return iter(HeterogeneousTruncatedLevyWalk(*args, **kwargs))


def gauss_markov(nodes, velocity_mean=1., alpha=1., variance=1.):
    """
    Gauss-Markov Mobility Model, as proposed in
    Camp, T., Boleng, J. & Davies, V. A survey of mobility models for ad hoc
    network research.
    Wireless Communications and Mobile Computing 2, 483-502 (2002).
    Required arguments:
      *nr_nodes*:
        Integer, the number of nodes.
    keyword arguments:
      *velocity_mean*:
        The mean velocity
      *alpha*:
        The tuning parameter used to vary the randomness
      *variance*:
        The randomness variance
    """
    nr_nodes = len(nodes)
    NODES = np.arange(nr_nodes)

    MAX_X = U(0, 0, NODES)
    MAX_Y = U(0, 0, NODES)
    MIN_X = U(0, 0, NODES)
    MIN_Y = U(0, 0, NODES)

    for node in range(len(nodes)):
        MAX_X[node] = nodes[node].max_x
        MAX_Y[node] = nodes[node].max_y
        MIN_X[node] = nodes[node].min_x
        MIN_Y[node] = nodes[node].min_y

    x = U(MIN_X, MAX_X, NODES)
    y = U(MIN_Y, MAX_Y, NODES)
    velocity = np.zeros(nr_nodes) + velocity_mean
    theta = U(0, 2 * np.pi, NODES)
    angle_mean = theta
    alpha2 = 1.0 - alpha
    alpha3 = np.sqrt(1.0 - alpha * alpha) * variance

    while True:
        x = x + velocity * np.cos(theta)
        y = y + velocity * np.sin(theta)

        # node bounces on the margins
        b = np.where(x < MIN_X)[0]
        x[b] = 2 * MIN_X[b] - x[b]
        theta[b] = np.pi - theta[b]
        angle_mean[b] = np.pi - angle_mean[b]

        b = np.where(x > MAX_X)[0]
        x[b] = 2 * MAX_X[b] - x[b]
        theta[b] = np.pi - theta[b]
        angle_mean[b] = np.pi - angle_mean[b]

        b = np.where(y < MIN_Y)[0]
        y[b] = 2 * MIN_Y[b] - y[b]
        theta[b] = -theta[b]
        angle_mean[b] = -angle_mean[b]

        b = np.where(y > MAX_Y)[0]
        y[b] = 2 * MAX_Y[b] - y[b]
        theta[b] = -theta[b]
        angle_mean[b] = -angle_mean[b]
        # calculate new speed and direction based on the model
        velocity = (alpha * velocity +
                    alpha2 * velocity_mean +
                    alpha3 * np.random.normal(0.0, 1.0, nr_nodes))

        theta = (alpha * theta +
                 alpha2 * angle_mean +
                 alpha3 * np.random.normal(0.0, 1.0, nr_nodes))

        yield np.dstack((x, y))[0]


def reference_point_group(nodes, n_groups, dimensions,
                          velocity=(0.1, 1.), aggregation=0.1):
    """
    Reference Point Group Mobility model, discussed in the following paper:
        Xiaoyan Hong, Mario Gerla, Guangyu Pei, and Ching-Chuan Chiang. 1999.
        A group mobility model for ad hoc wireless networks. In Proceedings of
        the 2nd ACM international workshop on Modeling, analysis and simulation
        of wireless and mobile systems (MSWiM '99). ACM, New York, NY, USA,
        53-60.
    In this implementation, group trajectories follow a random direction model,
    while nodes follow a random walk around the group center.
    The parameter 'aggregation' controls how close the nodes are to the group
    center.
    Required arguments:
      *nr_nodes*:
        list of integers, the number of nodes in each group.
      *dimensions*:
        Tuple of Integers, the x and y dimensions of the simulation area.
    keyword arguments:
      *velocity*:
        Tuple of Doubles, the minimum and maximum values for group velocity.
      *aggregation*:
        Double, parameter (between 0 and 1) used to aggregate the nodes in the
        group. Usually between 0 and 1, the more this value approximates to 1,
        the nodes will be more aggregated and closer to the group center.
        With a value of 0, the nodes are randomly distributed in the simulation
        area. With a value of 1, the nodes are close to the group center.
    """

    nr_nodes = [0 for _ in range(n_groups)]
    group = 0
    for n in range(len(nodes)):
        nr_nodes[group] += 1
        group += 1
        if n_groups == group:
            group = 0

    try:
        iter(nr_nodes)
    except TypeError:
        nr_nodes = [nr_nodes]

    NODES = np.arange(sum(nr_nodes))

    groups = []
    prev = 0
    for (i, n) in enumerate(nr_nodes):
        groups.append(np.arange(prev, n + prev))
        prev += n

    g_ref = np.empty(sum(nr_nodes), dtype=np.int)
    for (i, g) in enumerate(groups):
        for n in g:
            g_ref[n] = i

    FL_MAX = max(dimensions)
    MIN_V, MAX_V = velocity
    FL_DISTR = lambda SAMPLES: U(0, FL_MAX, SAMPLES)
    VEL_DISTR = lambda FD: U(MIN_V, MAX_V, FD)

    MAX_X, MAX_Y = dimensions
    x = U(0, MAX_X, NODES)
    y = U(0, MAX_Y, NODES)
    velocity = 1.
    theta = U(0, 2 * np.pi, NODES)
    costheta = np.cos(theta)
    sintheta = np.sin(theta)

    GROUPS = np.arange(len(groups))
    g_x = U(0, MAX_X, GROUPS)
    g_y = U(0, MAX_X, GROUPS)
    g_fl = FL_DISTR(GROUPS)
    g_velocity = VEL_DISTR(g_fl)
    g_theta = U(0, 2 * np.pi, GROUPS)
    g_costheta = np.cos(g_theta)
    g_sintheta = np.sin(g_theta)

    while True:
        x = x + velocity * costheta
        y = y + velocity * sintheta
        g_x = g_x + g_velocity * g_costheta
        g_y = g_y + g_velocity * g_sintheta

        for (i, g) in enumerate(groups):
            # step to group direction + step to group center
            x_g = x[g]
            y_g = y[g]
            c_theta = np.arctan2(g_y[i] - y_g, g_x[i] - x_g)

            x[g] = x_g + g_velocity[i] * g_costheta[i] + aggregation * np.cos(c_theta)
            y[g] = y_g + g_velocity[i] * g_sintheta[i] + aggregation * np.sin(c_theta)

        # node and group bounces on the margins
        b = np.where(x < 0)[0]
        if b.size > 0:
            x[b] = -x[b]
            costheta[b] = -costheta[b]
            g_idx = np.unique(g_ref[b])
            g_costheta[g_idx] = -g_costheta[g_idx]
        b = np.where(x > MAX_X)[0]
        if b.size > 0:
            x[b] = 2 * MAX_X - x[b]
            costheta[b] = -costheta[b]
            g_idx = np.unique(g_ref[b])
            g_costheta[g_idx] = -g_costheta[g_idx]
        b = np.where(y < 0)[0]
        if b.size > 0:
            y[b] = -y[b]
            sintheta[b] = -sintheta[b]
            g_idx = np.unique(g_ref[b])
            g_sintheta[g_idx] = -g_sintheta[g_idx]
        b = np.where(y > MAX_Y)[0]
        if b.size > 0:
            y[b] = 2 * MAX_Y - y[b]
            sintheta[b] = -sintheta[b]
            g_idx = np.unique(g_ref[b])
            g_sintheta[g_idx] = -g_sintheta[g_idx]

        # update info for nodes
        theta = U(0, 2 * np.pi, NODES)
        costheta = np.cos(theta)
        sintheta = np.sin(theta)

        # update info for arrived groups
        g_fl = g_fl - g_velocity
        g_arrived = np.where(np.logical_and(g_velocity > 0., g_fl <= 0.))[0]

        if g_arrived.size > 0:
            g_theta = U(0, 2 * np.pi, g_arrived)
            g_costheta[g_arrived] = np.cos(g_theta)
            g_sintheta[g_arrived] = np.sin(g_theta)
            g_fl[g_arrived] = FL_DISTR(g_arrived)
            g_velocity[g_arrived] = VEL_DISTR(g_fl[g_arrived])

        yield np.dstack((x, y))[0]


def tvc(nodes, n_groups, dimensions, velocity=(0.1, 1.),
        aggregation=[0.5, 0.], epoch=[100, 100]):
    """
    Time-variant Community Mobility Model, discussed in the paper
        Wei-jen Hsu, Thrasyvoulos Spyropoulos, Konstantinos Psounis, and Ahmed Helmy,
        "Modeling Time-variant User Mobility in Wireless Mobile Networks,"
        INFOCOM 2007, May 2007.
    This is a variant of the original definition, in the following way:
    - Communities don't have a specific area, but a reference point where the
       community members aggregate around.
    - The community reference points are not static, but follow a random
    direction model.
    - You can define a list of epoch stages, each value is the duration of the
    stage.
       For each stage a different aggregation value is used (from the aggregation
       parameter).
    - Aggregation values should be doubles between 0 and 1.
       For aggregation 0, there's no attraction point and the nodes move in a random
       walk model. For aggregation near 1, the nodes move closer to the community
       reference point.
    Required arguments:
      *nr_nodes*:
        list of integers, the number of nodes in each group.
      *dimensions*:
        Tuple of Integers, the x and y dimensions of the simulation area.
    keyword arguments:
      *velocity*:
        Tuple of Doubles, the minimum and maximum values for community velocities.
      *aggregation*:
        List of Doubles, parameters (between 0 and 1) used to aggregate the nodes
        around the community center.
        Usually between 0 and 1, the more this value approximates to 1,
        the nodes will be more aggregated and closer to the group center.
        With aggregation 0, the nodes are randomly distributed in the simulation area.
        With aggregation near 1, the nodes are closer to the group center.
      *epoch*:
        List of Integers, the number of steps each epoch stage lasts.
    """

    nr_nodes = [0 for _ in range(n_groups)]
    group = 0
    for n in range(len(nodes)):
        nr_nodes[group] += 1
        group += 1
        if n_groups == group:
            group = 0

    if len(aggregation) != len(epoch):
        raise Exception("The parameters 'aggregation' and 'epoch' should be "
                        "of same size")

    try:
        iter(nr_nodes)
    except TypeError:
        nr_nodes = [nr_nodes]

    NODES = np.arange(sum(nr_nodes))

    epoch_total = sum(epoch)

    def AGGREGATION(t):
        acc = 0
        for i in range(len(epoch)):
            acc += epoch[i]
            if t % epoch_total <= acc: return aggregation[i]
        raise Exception("Something wrong here")

    groups = []
    prev = 0
    for (i, n) in enumerate(nr_nodes):
        groups.append(np.arange(prev, n + prev))
        prev += n

    g_ref = np.empty(sum(nr_nodes), dtype=np.int)
    for (i, g) in enumerate(groups):
        for n in g:
            g_ref[n] = i

    FL_MAX = max(dimensions)
    MIN_V, MAX_V = velocity
    FL_DISTR = lambda SAMPLES: U(0, FL_MAX, SAMPLES)
    VEL_DISTR = lambda FD: U(MIN_V, MAX_V, FD)

    def wrap(x, y):
        b = np.where(x < 0)[0]
        if b.size > 0:
            x[b] += MAX_X
        b = np.where(x > MAX_X)[0]
        if b.size > 0:
            x[b] -= MAX_X
        b = np.where(y < 0)[0]
        if b.size > 0:
            y[b] += MAX_Y
        b = np.where(y > MAX_Y)[0]
        if b.size > 0:
            y[b] -= MAX_Y

    MAX_X, MAX_Y = dimensions
    x = U(0, MAX_X, NODES)
    y = U(0, MAX_Y, NODES)
    velocity = 1.
    theta = U(0, 2 * np.pi, NODES)
    costheta = np.cos(theta)
    sintheta = np.sin(theta)

    GROUPS = np.arange(len(groups))
    g_x = U(0, MAX_X, GROUPS)
    g_y = U(0, MAX_X, GROUPS)
    g_fl = FL_DISTR(GROUPS)
    g_velocity = VEL_DISTR(g_fl)
    g_theta = U(0, 2 * np.pi, GROUPS)
    g_costheta = np.cos(g_theta)
    g_sintheta = np.sin(g_theta)

    t = 0

    while True:

        t += 1
        # get aggregation value for this step
        aggr = AGGREGATION(t)

        x = x + velocity * costheta
        y = y + velocity * sintheta

        # move reference point only if nodes have to go there
        if aggr > 0:

            g_x = g_x + g_velocity * g_costheta
            g_y = g_y + g_velocity * g_sintheta

            # group wrap around when outside the margins (torus shaped area)
            wrap(g_x, g_y)

            # update info for arrived groups
            g_arrived = np.where(np.logical_and(g_velocity > 0., g_fl <= 0.))[0]
            g_fl = g_fl - g_velocity

            if g_arrived.size > 0:
                g_theta = U(0, 2 * np.pi, g_arrived)
                g_costheta[g_arrived] = np.cos(g_theta)
                g_sintheta[g_arrived] = np.sin(g_theta)
                g_fl[g_arrived] = FL_DISTR(g_arrived)
                g_velocity[g_arrived] = VEL_DISTR(g_fl[g_arrived])

            # update node position according to group center
            for (i, g) in enumerate(groups):
                # step to group direction + step to reference point
                x_g = x[g]
                y_g = y[g]

                dy = g_y[i] - y_g
                dx = g_x[i] - x_g
                c_theta = np.arctan2(dy, dx)

                # invert angle if wrapping around
                invert = np.where((np.abs(dy) > MAX_Y / 2) !=
                                  (np.abs(dx) > MAX_X / 2))[0]
                c_theta[invert] = c_theta[invert] + np.pi

                x[g] = x_g + g_velocity[i] * g_costheta[i] + aggr * np.cos(c_theta)
                y[g] = y_g + g_velocity[i] * g_sintheta[i] + aggr * np.sin(c_theta)

        # node wrap around when outside the margins (torus shaped area)
        wrap(x, y)

        # update info for nodes
        theta = U(0, 2 * np.pi, NODES)
        costheta = np.cos(theta)
        sintheta = np.sin(theta)

        yield np.dstack((x, y))[0]


def coherence_ref_point(nodes, n_groups, dimensions, pointlist, velocity=(0.1, 1.),
                        g_velocity=0.4, aggregation=0.1):
    """
    Based on the Reference Point Group Mobility model, discussed in the following paper:

        Xiaoyan Hong, Mario Gerla, Guangyu Pei, and Ching-Chuan Chiang. 1999.
        A group mobility model for ad hoc wireless networks. In Proceedings of
        the 2nd ACM international workshop on Modeling, analysis and simulation
        of wireless and mobile systems (MSWiM '99). ACM, New York, NY, USA,
        53-60.

    In this implementation, group trajectories follow a fixed linear path,
    while nodes follow a random walk around the group center.
    The parameter 'aggregation' controls how close the nodes are to the group
    center.

    Required arguments:

        *nr_nodes*:
        list of integers, the number of nodes in each group.

        *dimensions*:
        Tuple of Integers, the x and y dimensions of the simulation area.

    keyword arguments:

        *velocity*:
        Tuple of Doubles, the minimum and maximum values for group velocity.

        *g_velocity*
        Velocity of group vector. Appears to be 5.7 m/s per unit locally.

        *aggregation*:
        Double, parameter (between 0 and 1) used to aggregate the nodes in the
        group. Usually between 0 and 1, the more this value approximates to 1,
        the nodes will be more aggregated and closer to the group center.
        With a value of 0, the nodes are randomly distributed in the simulation
        area. With a value of 1, the nodes are close to the group center.

        *pointlist*
        List of Tuples of integers x,y,z corresponding to points in the model.
    """
    nr_nodes = [0 for _ in range(n_groups)]
    group = 0
    for n in range(len(nodes)):
        nr_nodes[group] += 1
        group += 1
        if n_groups == group:
            group = 0

    try:
        iter(nr_nodes)
    except TypeError:
        nr_nodes = [nr_nodes]

    NODES = np.arange(sum(nr_nodes))

    groups = []
    prev = 0
    for (i, n) in enumerate(nr_nodes):
        groups.append(np.arange(prev, n + prev))
        prev += n

    g_ref = np.empty(sum(nr_nodes), dtype=np.int)
    for (i, g) in enumerate(groups):
        for n in g:
            g_ref[n] = i

    FL_MAX = max(dimensions)
    MIN_V, MAX_V = velocity
    G_VEL = g_velocity

    FL_DISTR = lambda SAMPLES: U(0, FL_MAX, SAMPLES)
    #VEL_DISTR = lambda FD: U(MIN_V, MAX_V, FD)
    MAX_X, MAX_Y = dimensions

    if len(pointlist) > 1:
        current_x, current_y, current_z = pointlist[0]
        next_x, next_y, next_z = pointlist[1]
    else:
        current_x, current_y, current_z = pointlist[0]
        next_x, next_y, next_z = pointlist[0]
    x = U(current_x, current_x + MAX_V, NODES)
    y = U(current_y, current_y + MAX_V, NODES)
    velocity = 1.
    theta = U(0, 2 * np.pi, NODES)
    costheta = np.cos(theta)
    sintheta = np.sin(theta)

    GROUPS = np.arange(len(groups))
    g_x = np.array([current_x])
    g_y = np.array([current_y])

    g_fl = FL_DISTR(GROUPS)
    g_velocity = np.array([G_VEL])
    g_theta = [np.arctan2(next_y - current_y, next_x - current_x)]
    g_costheta = np.cos(g_theta)
    g_sintheta = np.sin(g_theta)
    point_index = 1
    while True:
        #Adjust location of individual point?
        x = x + velocity * costheta
        y = y + velocity * sintheta
        #Adjust location of group?
        g_x = g_x + g_velocity * g_costheta
        g_y = g_y + g_velocity * g_sintheta

        for (i, g) in enumerate(groups):
            # step to group direction + step to group center
            x_g = x[g]
            y_g = y[g]
            c_theta = np.arctan2(g_y[i] - y_g, g_x[i] - x_g)

            x[g] = x_g + g_velocity[i] * g_costheta[i] + aggregation * np.cos(c_theta)
            y[g] = y_g + g_velocity[i] * g_sintheta[i] + aggregation * np.sin(c_theta)

        # update info for nodes
        theta = U(0, 2 * np.pi, NODES)
        costheta = np.cos(theta)
        sintheta = np.sin(theta)

        # update info for arrived groups
        g_fl = g_fl - g_velocity

        g_finished = (abs(g_x - next_x) < 1 and abs(g_y - next_y) < 1)

        if g_x - next_x < 10:
            if g_finished:
                if point_index + 1 >= len(pointlist):
                    g_velocity[0] = 0
                else:
                    point_index += 1
                    current_x = next_x
                    current_y = next_y
                    next_x, next_y, next_z = pointlist[point_index]
                    g_theta = [np.arctan2(next_y - g_y, next_x - g_x)]
                    g_costheta = np.cos(g_theta)
                    g_sintheta = np.sin(g_theta)

        yield np.dstack((x, y))[0]
