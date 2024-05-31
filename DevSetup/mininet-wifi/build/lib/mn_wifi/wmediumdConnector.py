"""Helps starting the wmediumd service

authors:    Patrick Grosse (patrick.grosse@uni-muenster.de)
            Ramon Fontes (ramonrf@dca.fee.unicamp.br)"""

import ctypes
import os
import socket
import struct
import subprocess
import tempfile
from sys import version_info as py_version_info
from time import sleep

import pkg_resources
from mininet.log import info, debug


class wmediumd_mode(object):
    mode = 0

    @classmethod
    def set_mode(cls, mode):
        cls.mode = mode


class snr(object):
    def __init__(self):
        wmediumd_mode.set_mode(mode=1)


class error_prob(object):
    def __init__(self):
        wmediumd_mode.set_mode(mode=2)


class interference(object):
    def __init__(self):
        wmediumd_mode.set_mode(mode=3)


class spec_prob(object):
    def __init__(self):
        wmediumd_mode.set_mode(mode=4)


class w_cst:
    "wmediumd constants"

    def __init__(self):
        raise Exception("w_cst cannot be initialized")
        pass

    WRONG_MODE = 0
    SNR_MODE = 1
    ERRPROB_MODE = 2
    INTERFERENCE_MODE = 3
    SPECPROB_MODE = 4

    WSERVER_SHUTDOWN_REQUEST_TYPE = 0
    WSERVER_SNR_UPDATE_REQUEST_TYPE = 1
    WSERVER_SNR_UPDATE_RESPONSE_TYPE = 2
    WSERVER_DEL_BY_MAC_REQUEST_TYPE = 3
    WSERVER_DEL_BY_MAC_RESPONSE_TYPE = 4
    WSERVER_DEL_BY_ID_REQUEST_TYPE = 5
    WSERVER_DEL_BY_ID_RESPONSE_TYPE = 6
    WSERVER_ADD_REQUEST_TYPE = 7
    WSERVER_ADD_RESPONSE_TYPE = 8
    WSERVER_ERRPROB_UPDATE_REQUEST_TYPE = 9
    WSERVER_ERRPROB_UPDATE_RESPONSE_TYPE = 10
    WSERVER_SPECPROB_UPDATE_REQUEST_TYPE = 11
    WSERVER_SPECPROB_UPDATE_RESPONSE_TYPE = 12
    WSERVER_POS_UPDATE_REQUEST_TYPE = 13
    WSERVER_POS_UPDATE_RESPONSE_TYPE = 14
    WSERVER_TXPOWER_UPDATE_REQUEST_TYPE = 15
    WSERVER_TXPOWER_UPDATE_RESPONSE_TYPE = 16
    WSERVER_GAIN_UPDATE_REQUEST_TYPE = 17
    WSERVER_GAIN_UPDATE_RESPONSE_TYPE = 18
    WSERVER_HEIGHT_UPDATE_REQUEST_TYPE = 19
    WSERVER_HEIGHT_UPDATE_RESPONSE_TYPE = 20
    WSERVER_GAUSSIAN_RANDOM_UPDATE_REQUEST_TYPE = 21
    WSERVER_GAUSSIAN_RANDOM_UPDATE_RESPONSE_TYPE = 22
    WSERVER_MEDIUM_UPDATE_REQUEST_TYPE = 23
    WSERVER_MEDIUM_UPDATE_RESPONSE_TYPE = 24

    WUPDATE_SUCCESS = 0
    WUPDATE_INTF_NOTFOUND = 1
    WUPDATE_INTF_DUPLICATE = 2
    WUPDATE_WRONG_MODE = 3

    SOCKET_PATH = '/var/run/wmediumd.sock'
    LOG_PREFIX = 'wmediumd:'


class WmediumdException(Exception):
    pass


class set_interference(object):

    configstr = ''

    def __init__(self, **kwargs):
        self.interference(**kwargs)

    def interference(self, configstr, ppm, pos, txpowers,
                     fading_cof, noise_th, isnodeaps, **kwargs):
        configstr += '\tenable_interference = true;'
        configstr += '\n};\nmodel:\n{\n'
        configstr += '\ttype = "path_loss";\n\tpositions = ('
        first_pos = True
        for mappedpos in pos:
            posX = float(mappedpos.sta_pos[0])
            posY = float(mappedpos.sta_pos[1])
            posZ = float(mappedpos.sta_pos[2])
            if first_pos:
                first_pos = False
            else:
                configstr += ','
            configstr += '\n\t\t(%.1f, %.1f, %.1f)' % (
                posX, posY, posZ)
        configstr += '\n\t);\n\tfading_coefficient = %d;' % fading_cof
        configstr += '\n\tnoise_threshold = %d;' % noise_th
        configstr += '\n\tisnodeaps = ('
        first_isnodeap = True
        for isnodeap in isnodeaps:
            if first_isnodeap:
                configstr += '%s' % isnodeap
                first_isnodeap = False
            else:
                configstr += ', %s' % isnodeap
        configstr += ');\n\ttx_powers = ('
        first_txpower = True
        for mappedtxpower in txpowers:
            txpower = mappedtxpower.sta_txpower
            if first_txpower:
                configstr += '%s' % txpower
                first_txpower = False
            else:
                configstr += ', %s' % txpower
        if ppm.model == 'ITU':
            configstr += ');\n\tmodel_name = "itu";\n\tnFLOORS = %d;' \
                         '\n\tlF = %d;\n\tpL = %d;\n};' % \
                         (ppm.nFloors, ppm.lF, ppm.pL)
        elif ppm.model == 'logDistance':
            configstr += ');\n\tmodel_name = "log_distance";' \
                         '\n\tpath_loss_exp = %.1f;\n\txg = 0.0;\n};' \
                         % ppm.exp
        elif ppm.model == 'twoRayGround':
            configstr += ');\n\tmodel_name = "two_ray_ground";' \
                         '\n\tsL = %d;\n};' % ppm.sL
        elif ppm.model == 'logNormalShadowing':
            configstr += ');\n\tmodel_name = "log_normal_shadowing";' \
                         '\n\tpath_loss_exp = %.1f;\n\tsL = %d;\n};' \
                         % (ppm.exp, ppm.sL)
        else:
            configstr += ');\n\tmodel_name = "free_space";\n\tsL = %d;\n};' \
                         % ppm.sL
        self.configstr = configstr
        return self.configstr


class WStarter(object):

    wmd_logfile = None
    wmd_config_name = None

    def __init__(self, **kwargs):
        self.default_auto_errprob = 1.0
        self.default_auto_snr = -10
        self.is_managed = True
        self.is_initialized = False
        self.is_connected = False
        self.wmd_process = None

        self.start(**kwargs)

    def start(self, **kwargs):
        """Start the wmediumd daemon"""

        parameters = ['-l', '0', '-s']
        kwargs['parameters'] = parameters

        if wmediumd_mode.mode == 4:
            raise Exception("Wrong wmediumd mode given")
        wm = subprocess.call(['which', 'wmediumd'],
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        if wm == 0:
            self.is_initialized = True
            self.initialize(**kwargs)
            w_server.connect()
        else:
            info('*** Wmediumd is being used, but it is not installed.\n' \
                 '*** Please install Wmediumd with sudo util/install.sh -l.\n')
            exit(1)

    def initialize(self, **kwargs):
        """
        Start wmediumd, this method should be called right after
        Mininet.configureNodes()

        Notice: The stations can reach each other before this method is
        called and some scripts may use some kind of a cache (eg. iw station
        dump)
        ppm: propagation model class
        """
        if not self.is_initialized:
            raise WmediumdException("Use Wstarter.initialize first "
                                    "to set the required data")

        if self.is_connected:
            raise WmediumdException("Wstarter is already connected")

        mappedintf = {}
        mappedlinks = {}
        if wmediumd_mode.mode != w_cst.INTERFERENCE_MODE:
            # Map all links using the interface id and check for missing
            # interfaces in the  intfrefs list
            for link in kwargs['links']:
                link_id = link.sta1intf.id() + '/' + link.sta2intf.id()
                mappedlinks[link_id] = link
                found1 = False
                found2 = False
                for intfref in kwargs['intfrefs']:
                    if link.sta1intf.get_station_name() == \
                            intfref.get_station_name():
                        if link.sta1intf.get_station_name() == \
                                intfref.get_station_name():
                            found1 = True
                    if link.sta2intf.get_station_name() == \
                            intfref.get_station_name():
                        if link.sta2intf.get_station_name() == \
                                intfref.get_station_name():
                            found2 = True
                if not found1:
                    raise WmediumdException('%s is not part of the managed '
                                            'interfaces'
                                            % link.sta1intf.id())
                    pass
                if not found2:
                    raise WmediumdException('%s is not part of the managed '
                                            'interfaces'
                                            % link.sta2intf.id())

        if wmediumd_mode.mode is not w_cst.SPECPROB_MODE:
            """if wmediumd_mode.mode is not w_cst.INTERFERENCE_MODE:
                for intfref1 in kwargs['intfrefs']:
                    for intfref2 in kwargs['intfrefs']:
                        if intfref1 is not intfref2:
                            link_id = intfref1.id() + '/' + \
                                      intfref2.id()
                            if wmediumd_mode.mode == \
                                    w_cst.ERRPROB_MODE:
                                mappedlinks.setdefault(
                                    link_id, ERRPROBLink(
                                        intfref1, intfref2,
                                        self.default_auto_errprob))
                            else:
                                mappedlinks.setdefault(
                                    link_id, SNRLink(
                                        intfref1, intfref2,
                                        self.default_auto_snr))"""

            # Create wmediumd config
            wmd_config = tempfile.NamedTemporaryFile(
                prefix='mn_wmd_config_', suffix='.cfg', delete=False)
            WStarter.wmd_config_name = wmd_config.name
            debug("Name of wmediumd config: %s\n" % WStarter.wmd_config_name)
            configstr = 'ifaces:\n{\n\tids = [\n'
            intfref_id = 0
            for intfref in kwargs['intfrefs']:
                if intfref_id != 0:
                    configstr += ', \n'
                grepped_mac = intfref.get_mac()
                configstr += '\t\t"%s"' % grepped_mac
                mappedintf[intfref.id()] = intfref_id
                intfref_id += 1
            configstr += '\n\t];\n'
            if "mediums" in kwargs and kwargs['mediums']:
                configstr += '\tmedium_array = ' + str(kwargs['mediums']).replace("[","(").replace("]",")") + ';\n'
            if wmediumd_mode.mode is w_cst.INTERFERENCE_MODE:
                kwargs['configstr'] = configstr
                configstr = set_interference(**kwargs).configstr
            else:
                configstr += '};\nmodel:\n{\n\ttype = "'
                if wmediumd_mode.mode == w_cst.ERRPROB_MODE:
                    configstr += 'prob'
                else:
                    configstr += 'snr'
                configstr += '";\n\tdefault_prob = 1.0;\n\tlinks = ('
                first_link = True
                for mappedlink in mappedlinks.values():
                    id1 = mappedlink.sta1intf.id()
                    id2 = mappedlink.sta2intf.id()
                    if first_link:
                        first_link = False
                    else:
                        configstr += ','
                    if wmediumd_mode.mode == w_cst.ERRPROB_MODE:
                        configstr += '\n\t\t(%d, %d, %f)' % (
                            mappedintf[id1], mappedintf[id2],
                            mappedlink.errprob)
                    else:
                        configstr += '\n\t\t(%d, %d, %d)' % (
                            mappedintf[id1], mappedintf[id2],
                            mappedlink.snr)
                configstr += '\n\t);\n};'
            wmd_config.write(configstr.encode())
            wmd_config.close()
        # Start wmediumd using the created config
        cmdline = ['wmediumd']
        if wmediumd_mode.mode is w_cst.SPECPROB_MODE:
            cmdline.append("-d")
        else:
            cmdline.append("-c")
            cmdline.append(WStarter.wmd_config_name)
            if wmediumd_mode.mode is w_cst.SNR_MODE \
                    or wmediumd_mode.mode is w_cst.INTERFERENCE_MODE:
                cmdline.append("-x")
                per_data_file = \
                    pkg_resources.resource_filename(
                        'mn_wifi', 'data/signal_table_ieee80211')
                cmdline.append(per_data_file)
        cmdline[1:1] = kwargs['parameters']
        WStarter.wmd_logfile = tempfile.NamedTemporaryFile(prefix='mn_wmd_log_',
                                                           suffix='.log',
                                                           delete=True)
        debug("Name of wmediumd log: %s\n" % WStarter.wmd_logfile.name)
        #if self.is_managed:
        #    cmdline[0:0] = ["nohup"]

        self.wmd_process = subprocess.Popen(cmdline, shell=False,
                                            stdout=WStarter.wmd_logfile,
                                            stderr=subprocess.STDOUT,
                                            preexec_fn=os.setpgrp)
        self.is_connected = True


class w_pos(object):
    def __init__(self, staintf, sta_pos):
        """
        Describes the pos of a station

        :param sta_pos: Instance of WmediumdPosRef

        :type sta_pos: WmediumdPosRef
        """
        self.staintf = staintf
        self.sta_pos = sta_pos


class w_txpower(object):
    def __init__(self, staintf, sta_txpower):
        """
        Describes the Transmission Power of a station
        :param sta_txpower: Instance of TXPowerRef
        :type sta_txpower: TXPowerRef
        """
        self.staintf = staintf
        self.sta_txpower = sta_txpower


class w_gain(object):
    'Gain'
    def __init__(self, staintf, sta_gain):
        """
        Describes the Antenna Gain of a station
        :param sta_gain: Instance of GainRef
        :type sta_gain: GainRef
        """
        self.staintf = staintf
        self.sta_gain = sta_gain


class w_medium(object):
    'Medium Selection'

    def __init__(self, staintf, sta_medium_id):
        """
        Describes the Medium Selection of a station
        :param sta_medium_id: Instance of MediumIdRef
        :type sta_medium_id: MediumIdRef
        """
        self.staintf = staintf
        self.sta_medium_id = sta_medium_id


class WmediumdGRandom(object):
    'Gaussing Random'

    def __init__(self, staintf, sta_gaussian_random):
        """
        Describes the Gaussian Random of a node

        :param sta_gaussian_random: Instance of WmediumdGRandomRef

        :type sta_gaussian_random: WmediumdGRandomRef
        """
        self.staintf = staintf
        self.sta_gaussian_random = sta_gaussian_random


class w_height(object):
    'Antenna Height'
    def __init__(self, staintf, sta_height):
        """
        Describes the Antenna Height of a station
        :param sta_height: Instance of HeightRef
        :type sta_height: HeightRef
        """
        self.staintf = staintf
        self.sta_height = sta_height


class SNRLink(object):
    'SNR Link'
    def __init__(self, sta1intf, sta2intf, snr=10):
        """
        Describes a link between two interfaces using the SNR

        :param sta1intf: Instance of WmediumdIntfRef
        :param sta2intf: Instance of WmediumdIntfRef
        :param snr: Signal Noise Ratio as int

        :type sta1intf: WmediumdIntfRef
        :type sta2intf: WmediumdIntfRef
        :type snr: int
        """
        self.sta1intf = sta1intf
        self.sta2intf = sta2intf
        self.snr = snr


class ERRPROBLink(object):
    'ERRPROBLink'
    def __init__(self, sta1intf, sta2intf, errprob=0.2):
        """
        Describes a link between two interfaces using the error probability

        :param sta1intf: Instance of WmediumdIntfRef
        :param sta2intf: Instance of WmediumdIntfRef
        :param errprob: The error probability in the range [0.0;1.0]

        :type sta1intf: WmediumdIntfRef
        :type sta2intf: WmediumdIntfRef
        :type errprob: float
        """
        self.sta1intf = sta1intf
        self.sta2intf = sta2intf
        self.errprob = errprob


class WmediumdSPECPROBLink(object):
    'SPECPROB Link'
    def __init__(self, sta1intf, sta2intf, errprobs):
        """
        Describes a link between two interfaces using a matrix of error
        probabilities

        :param sta1intf: Instance of WmediumdIntfRef
        :param sta2intf: Instance of WmediumdIntfRef
        :param errprobs: The error probabilities in the range [0.0;1.0],
        the two dimensional array has as first
            dimension the packet size index and as the second the data
            rate index: errprobs[size_idx][rate_idx]

        :type sta1intf: WmediumdIntfRef
        :type sta2intf: WmediumdIntfRef
        :type errprobs: float[][]
        """
        self.sta1intf = sta1intf
        self.sta2intf = sta2intf
        self.errprobs = errprobs


class WmediumdIntfRef:
    'Intf Ref'
    def __init__(self, staname, intfname, intfmac):
        """
        An unambiguous reference to an interface of a station

        :param staname: Station name
        :param intfname: Interface name
        :param intfmac: Interface MAC address

        :type staname: str
        :type intfname: str
        :type intfmac: str
        """
        self.__staname = staname
        self.__intfname = intfname
        self.__intfmac = intfmac

    def get_station_name(self):
        """
        Get the name of the station
        :rtype: str
        """
        return self.__staname

    def get_intf_name(self):
        """
        Get the interface name
        :rtype: str
        """
        return self.__intfname

    def get_mac(self):
        """
        Get the MAC address of the interface
        :rtype: str
        """
        return self.__intfmac

    def id(self):
        """
        Id used in dicts
        :rtype: str
        """
        return self.get_station_name() + "." + self.get_intf_name()


class DynamicIntfRef(WmediumdIntfRef):
    'Intf Ref'
    def __init__(self, sta, intf=None):
        """
        An unambiguous reference to an interface of a station

        :param sta: Mininet-Wifi station
        :param intf: Mininet interface or name of Mininet interface.
        If None, the default interface will be used

        :type sta: Station
        :type intf: Union [Intf, str, None]
        """
        WmediumdIntfRef.__init__(self, "", "", "")
        self.__sta = sta
        self.__intf = intf

    def get_station_name(self):
        return self.__sta.name

    def get_intf_name(self):
        return self.__intf

    def get_mac(self):
        intf_name = self.get_intf_name()
        index = 0
        found = False
        for wlan_intf in self.__sta.wintfs.values():
            if wlan_intf.name == str(intf_name):
                found = True
                break
            index += 1
        if found:
            return self.__sta.wintfs[index].mac


class w_server(object):
    'Server Conn'
    __mac_struct_fmt = '6s'

    __base_struct_fmt = 'B'
    __base_struct = struct.Struct('!' + __base_struct_fmt)

    __snr_update_request_fmt = __base_struct_fmt + __mac_struct_fmt + __mac_struct_fmt + 'i'
    __snr_update_response_fmt = __base_struct_fmt + __snr_update_request_fmt + 'B'
    __snr_update_request_struct = struct.Struct('!' + __snr_update_request_fmt)
    __snr_update_response_struct = struct.Struct('!' + __snr_update_response_fmt)

    __pos_update_request_fmt = __base_struct_fmt + __mac_struct_fmt + 'f' + 'f' + 'f'
    __pos_update_response_fmt = __base_struct_fmt + __pos_update_request_fmt + 'B'
    __pos_update_request_struct = struct.Struct('!' + __pos_update_request_fmt)
    __pos_update_response_struct = struct.Struct('!' + __pos_update_response_fmt)

    __txpower_update_request_fmt = __base_struct_fmt + __mac_struct_fmt + 'i'
    __txpower_update_response_fmt = __base_struct_fmt + __txpower_update_request_fmt + 'B'
    __txpower_update_request_struct = struct.Struct('!' + __txpower_update_request_fmt)
    __txpower_update_response_struct = struct.Struct('!' + __txpower_update_response_fmt)

    __gain_update_request_fmt = __base_struct_fmt + __mac_struct_fmt + 'i'
    __gain_update_response_fmt = __base_struct_fmt + __gain_update_request_fmt + 'B'
    __gain_update_request_struct = struct.Struct('!' + __gain_update_request_fmt)
    __gain_update_response_struct = struct.Struct('!' + __gain_update_response_fmt)

    __gaussian_random_update_request_fmt = __base_struct_fmt + __mac_struct_fmt + 'f'
    __gaussian_random_update_response_fmt = __base_struct_fmt + __gaussian_random_update_request_fmt + 'B'
    __gaussian_random_update_request_struct = struct.Struct('!' + __gaussian_random_update_request_fmt)
    __gaussian_random_update_response_struct = struct.Struct('!' + __gaussian_random_update_response_fmt)

    __height_update_request_fmt = __base_struct_fmt + __mac_struct_fmt + 'i'
    __height_update_response_fmt = __base_struct_fmt + __height_update_request_fmt + 'B'
    __height_update_request_struct = struct.Struct('!' + __height_update_request_fmt)
    __height_update_response_struct = struct.Struct('!' + __height_update_response_fmt)

    __errprob_update_request_fmt = __base_struct_fmt + __mac_struct_fmt + __mac_struct_fmt + 'i'
    __errprob_update_response_fmt = __base_struct_fmt + __errprob_update_request_fmt + 'B'
    __errprob_update_request_struct = struct.Struct('!' + __errprob_update_request_fmt)
    __errprob_update_response_struct = struct.Struct('!' + __errprob_update_response_fmt)

    __specprob_update_request_fmt = __base_struct_fmt + __mac_struct_fmt + __mac_struct_fmt + '144i'
    __specprob_update_response_fmt = __base_struct_fmt + __mac_struct_fmt + __mac_struct_fmt + 'B'
    __specprob_update_request_struct = struct.Struct('!' + __specprob_update_request_fmt)
    __specprob_update_response_struct = struct.Struct('!' + __specprob_update_response_fmt)

    __station_del_by_mac_request_fmt = __base_struct_fmt + __mac_struct_fmt
    __station_del_by_mac_response_fmt = __base_struct_fmt + __station_del_by_mac_request_fmt + 'B'
    __station_del_by_mac_request_struct = struct.Struct('!' + __station_del_by_mac_request_fmt)
    __station_del_by_mac_response_struct = struct.Struct('!' + __station_del_by_mac_response_fmt)

    __station_del_by_id_request_fmt = __base_struct_fmt + 'i'
    __station_del_by_id_response_fmt = __base_struct_fmt + __station_del_by_id_request_fmt + 'B'
    __station_del_by_id_request_struct = struct.Struct('!' + __station_del_by_id_request_fmt)
    __station_del_by_id_response_struct = struct.Struct('!' + __station_del_by_id_response_fmt)

    __station_add_request_fmt = __base_struct_fmt + __mac_struct_fmt
    __station_add_response_fmt = __base_struct_fmt + __station_add_request_fmt + 'iB'
    __station_add_request_struct = struct.Struct('!' + __station_add_request_fmt)
    __station_add_response_struct = struct.Struct('!' + __station_add_response_fmt)

    __medium_update_request_fmt = __base_struct_fmt + __mac_struct_fmt + 'i'
    __medium_update_response_fmt = __base_struct_fmt + __medium_update_request_fmt + 'B'
    __medium_update_request_struct = struct.Struct('!' + __medium_update_request_fmt)
    __medium_update_response_struct = struct.Struct('!' + __medium_update_response_fmt)

    sock = None
    connected = False

    @classmethod
    def connect(cls, uds_address=w_cst.SOCKET_PATH):
        # type: (str) -> None
        """
        Connect to the wmediumd server
        :param uds_address: The UNIX domain socket
        """
        if cls.connected:
            raise WmediumdException("Already connected to wmediumd server")
        cls.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        info('*** Connecting to wmediumd server %s\n' % uds_address)
        sleep(1)
        cls.sock.connect(uds_address)
        cls.connected = True

    @classmethod
    def disconnect(cls):
        # type: () -> None
        """
        Disconnect from the wmediumd server
        """
        if cls.sock:
            try:
                WStarter.wmd_logfile.close()
            except OSError:
                pass
            try:
                os.remove(WStarter.wmd_config_name)
            except OSError:
                pass

            cls.sock.close()
            cls.connected = False

    @classmethod
    def register_interface(cls, mac):
        # type: (str) -> int
        """
        Register a new interface at wmediumd
        :param mac The mac address of the interface
        :return The wmediumd station index

        :type mac: str
        :rtype int
        """
        #info("\n{} Registering interface with mac {}".format(w_cst.LOG_PREFIX, mac))
        sleep(1)
        ret, sta_id = w_server.send_add(mac)
        if ret != w_cst.WUPDATE_SUCCESS:
            raise WmediumdException("Received error code from wmediumd: code {}".format(ret))
        return sta_id

    @classmethod
    def unregister_interface(cls, mac):
        # type: (str) -> None
        """
        Unregister a station at wmediumd
        :param mac The mac address of the interface

        :type mac: str
        """
        info("\n%s Unregistering interface with mac %s"
             % (w_cst.LOG_PREFIX, mac))
        ret = w_server.send_del_by_mac(mac)
        if ret != w_cst.WUPDATE_SUCCESS:
            raise WmediumdException("Received error code from wmediumd: "
                                    "code %d" % ret)

    @classmethod
    def update_link_snr(cls, link):
        # type: (SNRLink) -> None
        """
        Update the SNR of a connection at wmediumd
        :param link The link to update
        :type link: WmediumdLink
        """
        ret = w_server.send_snr_update(link)
        if ret != w_cst.WUPDATE_SUCCESS:
           raise WmediumdException("Received error code from wmediumd: "
                                   "code %d" % ret)

    @classmethod
    def update_pos(cls, pos):
        # type: (w_pos) -> None
        """
        Update the Pos of a connection at wmediumd
        :param pos The pos to update
        :type pos: w_pos
        """
        ret = w_server.send_pos_update(pos)
        if ret != w_cst.WUPDATE_SUCCESS:
            raise WmediumdException("Received error code from wmediumd: "
                                    "code %d" % ret)

    @classmethod
    def update_txpower(cls, txpower):
        # type: (w_txpower) -> None
        """
        Update the w_txpower of a connection at wmediumd
        :param txpower The txpower to update

        :type txpower: w_txpower
        """
        ret = w_server.send_txpower_update(txpower)
        if ret != w_cst.WUPDATE_SUCCESS:
            raise WmediumdException("Received error code from wmediumd: "
                                    "code %d" % ret)

    @classmethod
    def update_gain(cls, gain):
        # type: (gain) -> None
        """
        Update the Antenna Gain of a connection at wmediumd
        :param gain The gain to update
        :type gain: Gain
        """
        ret = w_server.send_gain_update(gain)
        if ret != w_cst.WUPDATE_SUCCESS:
            raise WmediumdException("Received error code from wmediumd: "
                                    "code %d" % ret)

    @classmethod
    def update_gaussian_random(cls, gRandom):
        # type: (WmediumdGRandom) -> None
        """
        Update the Gaussian Random of a connection at wmediumd
        :param gRandom The gRandom to update
        :type gRandom: WmediumdGRandom
        """
        ret = w_server.send_gaussian_random_update(gRandom)
        if ret != w_cst.WUPDATE_SUCCESS:
            raise WmediumdException("Received error code from wmediumd: "
                                    "code %d" % ret)

    @classmethod
    def update_height(cls, height):
        # type: (height) -> None
        """
        Update the Antenna Height of a connection at wmediumd
        :param height The height to update
        :type height: Height
        """
        ret = w_server.send_height_update(height)
        if ret != w_cst.WUPDATE_SUCCESS:
            raise WmediumdException("Received error code from wmediumd: "
                                    "code %d" % ret)

    @classmethod
    def update_link_errprob(cls, link):
        # type: (ERRPROBLink) -> None
        """
        Update the ERRPROB of a connection at wmediumd
        :param link The link to update
        :type link: WmediumdLink
        """
        ret = w_server.send_errprob_update(link)
        if ret != w_cst.WUPDATE_SUCCESS:
            raise WmediumdException("Received error code from wmediumd: "
                                    "code %d" % ret)

    @classmethod
    def update_link_specprob(cls, link):
        # type: (WmediumdSPECPROBLink) -> None
        """
        Update the SPECPROB of a connection at wmediumd
        :param link The link to update
        :type link: WmediumdLink
        """
        ret = w_server.send_specprob_update(link)
        if ret != w_cst.WUPDATE_SUCCESS:
            raise WmediumdException("Received error code from wmediumd: "
                                    "code %d" % ret)

    @classmethod
    def update_medium(cls, medium):
        # type: (w_medium) -> None
        """
        Update the Medium of a connection at wmediumd
        :param medium The medium to update
        :type medium: w_medium
        """
        ret = w_server.send_medium_update(medium)
        if ret != w_cst.WUPDATE_SUCCESS:
            raise WmediumdException("Received error code from wmediumd: "
                                    "code %d" % ret)

    @classmethod
    def send_snr_update(cls, link):
        # type: (SNRLink) -> int
        """
        Send an update to the wmediumd server
        :param link: The SNRLink to update
        :return: A WUPDATE_* constant
        """
        #debug("%s Updating SNR from interface %s to interface %s to "
        #      "value %d\n" % (w_cst.LOG_PREFIX,
        #                      link.sta1intf.get_mac(),
        #                      link.sta2intf.get_mac(), link.snr))
        cls.sock.send(cls.__create_snr_update_request(link))
        return cls.__parse_response(
            w_cst.WSERVER_SNR_UPDATE_RESPONSE_TYPE,
            cls.__snr_update_response_struct)[-1]

    @classmethod
    def send_pos_update(cls, pos):
        # type: (w_pos) -> int
        """
        Send an update to the wmediumd server
        :param pos: The w_pos to update
        :return: A WUPDATE_* constant
        """
        posX = pos.sta_pos[0]
        posY = pos.sta_pos[1]
        posZ = pos.sta_pos[2]
        #debug("%s Updating Pos of %s to x=%s, y=%s, z=%s\n" % (
        #    w_cst.LOG_PREFIX, pos.staintf.get_mac(),
        #    posX, posY, posZ))
        cls.sock.send(cls.__create_pos_update_request(pos, posX, posY, posZ))
        return cls.__parse_response(
            w_cst.WSERVER_POS_UPDATE_RESPONSE_TYPE,
            cls.__pos_update_response_struct)[-1]

    @classmethod
    def send_txpower_update(cls, txpower):
        # type: (w_txpower) -> int
        """
        Send an update to the wmediumd server
        :param txpower: The w_txpower to update
        :return: A WUPDATE_* constant
        """
        #txpower_ = txpower.sta_txpower
        #debug("%s Updating TxPower of %s to %d\n" % (
        #    w_cst.LOG_PREFIX, txpower.staintf.get_mac(),
        #    txpower_))
        cls.sock.send(cls.__create_txpower_update_request(txpower))
        return cls.__parse_response(
            w_cst.WSERVER_TXPOWER_UPDATE_RESPONSE_TYPE,
            cls.__txpower_update_response_struct)[-1]

    @classmethod
    def send_gain_update(cls, gain):
        # type: (gain) -> int
        """
        Send an update to the wmediumd server
        :param gain: The Gain to update
        :return: A WUPDATE_* constant
        """
        #gain_ = gain.sta_gain
        #debug("%s Updating Antenna Gain of %s to %d\n" % (
        #    w_cst.LOG_PREFIX, gain.staintf.get_mac(),
        #    gain_))
        cls.sock.send(cls.__create_gain_update_request(gain))
        return cls.__parse_response(
            w_cst.WSERVER_GAIN_UPDATE_RESPONSE_TYPE,
            cls.__gain_update_response_struct)[-1]

    @classmethod
    def send_gaussian_random_update(cls, gRandom):
        # type: (WmediumdGRandom) -> int
        """
        Send an update to the wmediumd server
        :param gRandom: The WmediumdGRandom to update
        :return: A WUPDATE_* constant
        """
        #gRandom_ = gRandom.sta_gaussian_random
        #debug("%s Updating Gaussian Random of %s to %s\n" % (
        #    w_cst.LOG_PREFIX, gRandom.staintf.get_mac(),
        #    gRandom_))
        cls.sock.send(cls.__create_gaussian_random_update_request(gRandom))
        return cls.__parse_response(
            w_cst.WSERVER_GAUSSIAN_RANDOM_UPDATE_RESPONSE_TYPE,
            cls.__gaussian_random_update_response_struct)[-1]

    @classmethod
    def send_height_update(cls, height):
        # type: (height) -> int
        """
        Send an update to the wmediumd server
        :param height: The Height to update
        :return: A WUPDATE_* constant
        """
        #height_ = height.sta_height
        #debug("%s Updating Antenna Height of %s to %d\n" % (
        #    w_cst.LOG_PREFIX, height.staintf.get_mac(),
        #    height_))
        cls.sock.send(cls.__create_height_update_request(height))
        return cls.__parse_response(
            w_cst.WSERVER_HEIGHT_UPDATE_RESPONSE_TYPE,
            cls.__height_update_response_struct)[-1]

    @classmethod
    def send_errprob_update(cls, link):
        # type: (ERRPROBLink) -> int
        """
        Send an update to the wmediumd server
        :param link: The ERRPROBLink to update
        :return: A WUPDATE_* constant
        """
        #debug("\n%s Updating ERRPROB from interface %s to interface %s "
        #      "to value %f" % (
        #          w_cst.LOG_PREFIX, link.sta1intf.get_mac(),
        #          link.sta2intf.get_mac(),
        #          link.errprob))
        cls.sock.send(cls.__create_errprob_update_request(link))
        return cls.__parse_response(
            w_cst.WSERVER_ERRPROB_UPDATE_RESPONSE_TYPE,
            cls.__errprob_update_response_struct)[-1]

    @classmethod
    def send_specprob_update(cls, link):
        # type: (WmediumdSPECPROBLink) -> int
        """
        Send an update to the wmediumd server
        :param link: The WmediumdSPECPROBLink to update
        :return: A WUPDATE_* constant
        """
        #debug("\n%s Updating SPECPROB from interface %s to interface %s" % (
        #    w_cst.LOG_PREFIX, link.sta1intf.get_mac(),
        #    link.sta2intf.get_mac()))
        cls.sock.send(cls.__create_specprob_update_request(link))
        return cls.__parse_response(
            w_cst.WSERVER_SPECPROB_UPDATE_RESPONSE_TYPE,
            cls.__specprob_update_response_struct)[-1]

    @classmethod
    def send_del_by_mac(cls, mac):
        # type: (str) -> int
        """
        Send an update to the wmediumd server
        :param mac: The mac address of the interface to be deleted
        :return: A WUPDATE_* constant
        """
        cls.sock.send(cls.__create_station_del_by_mac_request(mac))
        return cls.__parse_response(
            w_cst.WSERVER_DEL_BY_MAC_RESPONSE_TYPE,
            cls.__station_del_by_mac_response_struct)[-1]

    @classmethod
    def send_del_by_id(cls, sta_id):
        # type: (int) -> int
        """
        Send an update to the wmediumd server
        :param sta_id: The wmediumd index of the station
        :return: A WUPDATE_* constant
        """
        cls.sock.send(cls.__create_station_del_by_id_request(sta_id))
        return cls.__parse_response(
            w_cst.WSERVER_DEL_BY_ID_RESPONSE_TYPE,
            cls.__station_del_by_id_response_struct)[-1]

    @classmethod
    def send_add(cls, mac):
        # type: (str) -> (int, int)
        """
        Send an update to the wmediumd server
        :param mac: The mac address of the new interface
        :return: A WUPDATE_* constant and on success at the second pos
        the index
        """
        cls.sock.send(cls.__create_station_add_request(mac))
        resp = cls.__parse_response(
            w_cst.WSERVER_ADD_RESPONSE_TYPE,
            cls.__station_add_response_struct)
        return resp[-1], resp[-2]

    @classmethod
    def send_medium_update(cls, medium):
        # type: (w_medium) -> int
        """
        Send an update to the wmediumd server
        :param medium: The Medium to update
        :return: A WUPDATE_* constant
        """
        medium_ = medium.sta_medium_id
        debug("%s Updating Medium ID of %s to %d\n" % (
           w_cst.LOG_PREFIX, medium.staintf.get_mac(),
           medium_))
        cls.sock.send(cls.__create_medium_update_request(medium))
        return cls.__parse_response(
            w_cst.WSERVER_MEDIUM_UPDATE_REQUEST_TYPE,
            cls.__medium_update_response_struct)[-1]

    @classmethod
    def __create_snr_update_request(cls, link):
        "snr update request"
        # type: (SNRLink) -> str
        msgtype = w_cst.WSERVER_SNR_UPDATE_REQUEST_TYPE
        if py_version_info < (3, 0):
            mac_from = link.sta1intf.get_mac().replace(':', '').decode('hex')
            mac_to = link.sta2intf.get_mac().replace(':', '').decode('hex')
        else:
            mac_from = bytes.fromhex(link.sta1intf.get_mac().replace(':', ''))
            mac_to = bytes.fromhex(link.sta2intf.get_mac().replace(':', ''))
        snr = int(link.snr)
        return cls.__snr_update_request_struct.pack(msgtype, mac_from,
                                                    mac_to, snr)

    @classmethod
    def __create_pos_update_request(cls, pos, posX, posY, posZ):
        "pos update request"
        # type: (pos) -> str
        msgtype = w_cst.WSERVER_POS_UPDATE_REQUEST_TYPE
        if py_version_info < (3, 0):
            mac = pos.staintf.get_mac().replace(':', '').decode('hex')
        else:
            mac = bytes.fromhex(pos.staintf.get_mac().replace(':', ''))
        return cls.__pos_update_request_struct.pack(msgtype, mac,
                                                    posX, posY, posZ)

    @classmethod
    def __create_txpower_update_request(cls, txpower):
        "tx power update request"
        # type: (w_txpower) -> str
        msgtype = w_cst.WSERVER_TXPOWER_UPDATE_REQUEST_TYPE
        if py_version_info < (3, 0):
            mac = txpower.staintf.get_mac().replace(':', '').decode('hex')
        else:
            mac = bytes.fromhex((txpower.staintf.get_mac().replace(':', '')))
        txpower_ = txpower.sta_txpower
        return cls.__txpower_update_request_struct.pack(msgtype, mac, txpower_)

    @classmethod
    def __create_gain_update_request(cls, gain):
        "antenna gain update request"
        # type: (gain) -> str
        msgtype = w_cst.WSERVER_GAIN_UPDATE_REQUEST_TYPE
        if py_version_info < (3, 0):
            mac = gain.staintf.get_mac().replace(':', '').decode('hex')
        else:
            mac = bytes.fromhex((gain.staintf.get_mac().replace(':', '')))
        gain_ = gain.sta_gain
        return cls.__gain_update_request_struct.pack(msgtype, mac, gain_)

    @classmethod
    def __create_gaussian_random_update_request(cls, gRandom):
        "gaussian random update request"
        # type: (WmediumdGRandom) -> str
        msgtype = w_cst.WSERVER_GAUSSIAN_RANDOM_UPDATE_REQUEST_TYPE
        if py_version_info < (3, 0):
            mac = gRandom.staintf.get_mac().replace(':', '').decode('hex')
        else:
            mac = bytes.fromhex((gRandom.staintf.get_mac().replace(':', '')))
        gRandom_ = gRandom.sta_gaussian_random
        return cls.__gaussian_random_update_request_struct.pack(msgtype, mac,
                                                                gRandom_)

    @classmethod
    def __create_height_update_request(cls, height):
        "height update request"
        # type: (height) -> str
        msgtype = w_cst.WSERVER_HEIGHT_UPDATE_REQUEST_TYPE
        if py_version_info < (3, 0):
            mac = height.staintf.get_mac().replace(':', '').decode('hex')
        else:
            mac = bytes.fromhex((height.staintf.get_mac().replace(':', '')))
        height_ = height.sta_height
        return cls.__height_update_request_struct.pack(msgtype, mac, height_)

    @classmethod
    def __create_errprob_update_request(cls, link):
        "error prob update request"
        # type: (ERRPROBLink) -> str
        msgtype = w_cst.WSERVER_ERRPROB_UPDATE_REQUEST_TYPE
        if py_version_info < (3, 0):
            mac_from = link.sta1intf.get_mac().replace(':', '').decode('hex')
            mac_to = link.sta2intf.get_mac().replace(':', '').decode('hex')
        else:
            mac_from = bytes.fromhex((link.sta1intf.get_mac().replace(':', '')))
            mac_to = bytes.fromhex((link.sta2intf.get_mac().replace(':', '')))
        errprob = cls.__conv_float_to_fixed_point(link.errprob)
        return cls.__errprob_update_request_struct.pack(msgtype, mac_from, mac_to,
                                                        errprob)

    @classmethod
    def __create_specprob_update_request(cls, link):
        "specprob update request"
        # type: (WmediumdSPECPROBLink) -> str
        msgtype = w_cst.WSERVER_SPECPROB_UPDATE_REQUEST_TYPE
        if py_version_info < (3, 0):
            mac_from = link.sta1int.get_mac().replace(':', '').decode('hex')
            mac_to = link.sta2intf.get_mac().replace(':', '').decode('hex')
        else:
            mac_from = bytes.fromhex((link.sta1intf.get_mac().replace(':', '')))
            mac_to = bytes.fromhex((link.sta2intf.get_mac().replace(':', '')))
        fixed_points = [None] * 144
        for size_idx in range(0, 12):
            for rate_idx in range(0, 12):
                fixed_points[size_idx * 12 + rate_idx] = \
                    cls.__conv_float_to_fixed_point(
                        link.errprobs[size_idx][rate_idx])
        return cls.__specprob_update_request_struct.pack(msgtype, mac_from,
                                                         mac_to, *fixed_points)

    @classmethod
    def __create_station_del_by_mac_request(cls, mac):
        "del station by mac"
        # type: (str) -> str
        msgtype = w_cst.WSERVER_DEL_BY_MAC_REQUEST_TYPE
        macparsed = mac.replace(':', '').decode('hex')
        return cls.__station_del_by_mac_request_struct.pack(msgtype, macparsed)

    @classmethod
    def __create_station_del_by_id_request(cls, sta_id):
        "del station by id"
        # type: (int) -> str
        msgtype = w_cst.WSERVER_DEL_BY_ID_REQUEST_TYPE
        return cls.__station_del_by_id_request_struct.pack(msgtype, sta_id)

    @classmethod
    def __create_station_add_request(cls, mac):
        "add station"
        # type: (str) -> str
        msgtype = w_cst.WSERVER_ADD_REQUEST_TYPE
        if py_version_info < (3, 0):
            macparsed = mac.replace(':', '').decode('hex')
        else:
            macparsed = bytes.fromhex(mac.replace(':', ''))
        return cls.__station_add_request_struct.pack(msgtype, macparsed)

    @classmethod
    def __create_medium_update_request(cls, medium):
        "medium update request"
        # type: (w_medium) -> str
        msgtype = w_cst.WSERVER_MEDIUM_UPDATE_REQUEST_TYPE
        if py_version_info < (3, 0):
            mac = medium.staintf.get_mac().replace(':', '').decode('hex')
        else:
            mac = bytes.fromhex((medium.staintf.get_mac().replace(':', '')))
        mediumid_ = medium.sta_medium_id
        return cls.__medium_update_request_struct.pack(msgtype, mac, mediumid_)

    @classmethod
    def __parse_response(cls, expected_type, resp_struct):
        "parse response"
        # type: (int, struct.Struct) -> tuple
        recvd_data = cls.sock.recv(resp_struct.size)
        # recvd_type = cls.__base_struct.unpack(recvd_data[0])[0]
        # if recvd_type != expected_type:
        #    raise WmediumdException(
        #        "Received response of unknown type %d, expected %d" % (recvd_type,
        # expected_type))
        return resp_struct.unpack(recvd_data)

    @classmethod
    def __conv_float_to_fixed_point(cls, d):
        shift_amount = 31
        one_shifted = ctypes.c_int32(1 << 31).value
        beforecomma = int(d)
        aftercomma = int(((d - beforecomma) * one_shifted))
        return ctypes.c_int32(beforecomma << shift_amount).value + aftercomma
