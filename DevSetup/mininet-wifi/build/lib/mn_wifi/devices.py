"""Mininet-WiFi: A simple networking testbed for Wireless OpenFlow/SDWN!
   author: Ramon Fontes (ramonrf@dca.fee.unicamp.br)"""


class DeviceRate(object):
    "Data Rate for specific equipments"

    rate = 0

    def __init__(self, intf):
        model = intf.node.params['model']
        self.__getattribute__(model)(intf)

    def DI524(self, intf):
        """D-Link AirPlus G DI-524
           from http://www.dlink.com/-/media/Consumer_Products/
           DI/DI%20524/Manual/DI_524_Manual_EN_UK.pdf
        rate: maximum supported bandwidth (mbps)"""
        modes = ['n', 'g', 'b']
        rates = [130, 54, 11]
        self.rate = rates[modes.index(intf.mode)]
        return self.rate

    def TLWR740N(self, intf):
        """TL-WR740N
           from http://www.tp-link.com.br/products/details/
           cat-9_TL-WR740N.html#specificationsf
        mode: interface mode
        rate: maximum supported bandwidth (mbps)"""
        modes = ['n', 'g', 'b']
        rates = [130, 54, 11]
        self.rate = rates[modes.index(intf.mode)]
        return self.rate

    def WRT120N(self, intf):
        """CISCO WRT120N
           from http://downloads.linksys.com/downloads/datasheet/
           WRT120N_V10_DS_B-WEB.pdf
        mode: interface mode
        rate: maximum supported bandwidth (mbps)"""
        modes = ['n', 'g', 'b']
        rates = [150, 54, 11]
        self.rate = rates[modes.index(intf.mode)]
        return self.rate


class CustomRange(object):

    range = 0

    def __init__(self, intf):
        self.customSignalRange(intf)

    def customSignalRange(self, intf):
        """Custom Signal Range
        mode: interface mode
        range: signal range (m)"""
        modes = ['a', 'g', 'b', 'n', 'ac']
        ranges = [33, 33, 50, 70, 100]
        self.range = ranges[modes.index(intf.mode)]
        return self.range


class DeviceRange (object):
    "Range for specific equipments"

    range = 100

    def __init__(self, node):
        self.__getattribute__(node.params['model'])()

    def DI524(self):
        """ D-Link AirPlus G DI-524
            from http://www.dlink.com/-/media/Consumer_Products/DI/
            DI%20524/Manual/DI_524_Manual_EN_UK.pdf
            indoor = 100
            outdoor = 200
        range: signal range (m)"""

        self.range = 100
        return self.range

    def TLWR740N(self):
        """TL-WR740N
            NO REFERENCE!
        range: signal range (m)"""

        self.range = 50
        return self.range

    def WRT120N(self):
        """CISCO WRT120N
            NO REFERENCE!
        range: signal range (m)"""

        self.range = 50
        return self.range


class DeviceTxPower (object):
    "TX Power for specific equipments"

    txpower = 0

    def __init__(self, intf):
        "get txpower"
        model = intf.node.params['model']
        self.__getattribute__(model)(intf)

    def DI524(self, **kwargs):
        """D-Link AirPlus G DI-524
            from http://www.dlink.com/-/media/Consumer_Products/DI/
            DI%20524/Manual/DI_524_Manual_EN_UK.pdf
        txPower = transmission power (dBm)"""
        self.txpower = 14
        return self.txpower

    def TLWR740N(self, intf):
        """TL-WR740N
            No REFERENCE!
        txPower = transmission power (dBm)"""
        self.txpower = 20
        return self.txpower

    def WRT120N(self, intf):
        """CISCO WRT120N
           from http://downloads.linksys.com/downloads/datasheet/
           WRT120N_V10_DS_B-WEB.pdf"""
        modes = ['b', 'g', 'n']
        txpowers = [21, 18, 16]
        self.txpower = txpowers[modes.index(intf.mode)]
        return self.txpower
