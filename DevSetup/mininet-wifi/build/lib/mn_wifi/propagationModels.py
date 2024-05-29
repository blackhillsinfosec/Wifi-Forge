"""author: Ramon Fontes (ramonrf@dca.fee.unicamp.br)
        
        Implemented propagation models:
            (Indoors):
                Free-Space Propagation Model
                Log-Distance Propagation Model
                International Telecommunication Union (ITU) Propagation Model
            (Outdoors):
                Two-Ray-Ground Propagation Model"""

import math
from random import gauss
from time import sleep


class PropagationModel(object):

    rssi = -62
    model = 'logDistance'  # default propagation model
    exp = 3  # Exponent
    sL = 1  # System Loss
    lF = 0  # Floor penetration loss factor
    pL = 0  # Power Loss Coefficient
    nFloors = 0  # Number of floors
    gRandom = 0  # Gaussian random variable
    variance = 2  # variance
    noise_th = -91
    cca_threshold = -90

    def __init__(self, intf, apintf, dist=0):
        if self.model in dir(self):
            self.__getattribute__(self.model)(intf, apintf, dist)

    @classmethod
    def set_attr(cls, noise_th, cca_th, **kwargs):
        cls.noise_th = noise_th
        cls.cca_threshold = cca_th
        for arg in kwargs:
            setattr(cls, arg, kwargs.get(arg))

    def path_loss(self, intf, dist):
        """Path Loss Model:
        (f) signal frequency transmited(Hz)
        (d) is the distance between the transmitter and the receiver (m)
        (c) speed of light in vacuum (m)
        (L) System loss"""
        f = intf.freq * 10 ** 9  # Convert Ghz to Hz
        c = 299792458.0
        L = self.sL

        if dist == 0: dist = 0.1

        lambda_ = c / f  # lambda: wavelength (m)
        denominator = lambda_ ** 2
        numerator = (4 * math.pi * dist) ** 2 * L
        pl = 10 * math.log10(numerator / denominator)

        return int(pl)

    def friis(self, intf, ap_intf, dist):
        """Friis Propagation Loss Model:
        (f) signal frequency transmited(Hz)
        (d) is the distance between the transmitter and the receiver (m)
        (c) speed of light in vacuum (m)
        (L) System loss"""
        gr = intf.antennaGain
        pt = ap_intf.txpower
        gt = ap_intf.antennaGain
        gains = pt + gt + gr

        pl = self.path_loss(intf, dist)
        self.rssi = gains - pl

        return self.rssi

    def twoRayGround(self,  intf, ap_intf, dist):
        """Two Ray Ground Propagation Loss Model (does not give a good result for
        a short distance)"""
        gr = int(intf.antennaGain)
        hr = float(intf.antennaHeight)
        pt = int(ap_intf.txpower)
        gt = int(ap_intf.antennaGain)
        ht = float(ap_intf.antennaHeight)
        gains = pt + gt + gr
        c = 299792458.0  # speed of light in vacuum
        f = intf.band * 1000000  # frequency in Hz

        if dist == 0: dist = 0.1
        denominator = (c / f) / 1000
        dCross = (4 * math.pi * ht * hr) / denominator
        if dist < dCross:
            self.rssi = self.friis(intf, ap_intf, dist)
        else:
            numerator = (pt * gt * gr * ht ** 2 * hr ** 2)
            denominator = dist ** 4
            pldb = int(numerator / denominator)
            self.rssi = gains - pldb
        return self.rssi

    def logDistance(self, intf, ap_intf, dist):
        """Log Distance Propagation Loss Model:
        ref_d (m): The distance at which the reference loss is
        calculated
        exponent: The exponent of the Path Loss propagation model, where 2
        is for propagation in free space
        (dist) is the distance between the transmitter and the receiver (m)"""
        gr = intf.antennaGain
        pt = ap_intf.txpower
        gt = ap_intf.antennaGain
        gains = pt + gt + gr
        ref_d = 1

        pl = self.path_loss(intf, ref_d)
        if dist == 0: dist = 0.1

        pldb = 10 * self.exp * math.log10(dist / ref_d)
        self.rssi = gains - (int(pl) + int(pldb))

        return self.rssi

    def logNormalShadowing(self, intf, ap_intf, dist):
        """Log-Normal Shadowing Propagation Loss Model:
        ref_d (m): The distance at which the reference loss is
        calculated
        exponent: The exponent of the Path Loss propagation model, where 2
        is for propagation in free space
        (d) is the distance between the transmitter and the receiver (m)
        gRandom is a Gaussian random variable"""
        gr = intf.antennaGain
        pt = ap_intf.txpower
        gt = ap_intf.antennaGain
        gRandom = self.gRandom
        gains = pt + gt + gr
        ref_d = 1

        pl = self.path_loss(intf, ref_d)
        if dist == 0: dist = 0.1

        pldb = 10 * self.exp * math.log10(dist / ref_d) + gRandom
        self.rssi = gains - (int(pl) + int(pldb))

        return self.rssi

    def ITU(self, intf, ap_intf, dist):
        """International Telecommunication Union (ITU) Propagation Loss Model:"""
        gr = intf.antennaGain
        pt = ap_intf.txpower
        gt = ap_intf.antennaGain
        f = ap_intf.freq * 10 ** 3
        nFloors = self.nFloors  # Number of Floors
        gains = pt + gt + gr
        pL = self.pL
        lF = self.lF  # Floor penetration loss factor
        N = 28  # Power Loss Coefficient

        """Power Loss Coefficient Based on the Paper 
        Site-Specific Validation of ITU Indoor Path Loss Model at 2.4 GHz 
        from Theofilos Chrysikos, Giannis Georgopoulos and Stavros Kotsopoulos"""
        if dist == 0: dist = 0.1
        if dist > 16: N = 38
        if pL != 0: N = pL

        pldb = 20 * math.log10(f) + N * math.log10(dist) + lF * nFloors - 28
        self.rssi = gains - int(pldb)

        return self.rssi

    def young(self, intf, ap_intf, dist):
        "Young Propagation Loss Model"
        gr = intf.antennaGain
        hr = intf.antennaHeight
        gt = ap_intf.antennaGain
        ht = ap_intf.antennaHeight
        cf = 0.01075  # clutter factor

        if dist == 0: dist = 0.1
        self.rssi = int(dist ** 4 / (gt * gr) * (ht * hr) ** 2 * cf)

        return self.rssi


ppm = PropagationModel


class SetSignalRange(object):

    range = 0

    def __init__(self, intf):
        "Calculate the signal range given the propagation model"
        if ppm.model in dir(self):
            self.__getattribute__(ppm.model)(intf)

    def friis(self, intf):
        """Path Loss Model:
        (f) signal frequency transmited(Hz)
        (c) speed of light in vacuum (m)
        (L) System loss"""
        # Convert Ghz to Hz
        f = intf.freq * 10 ** 9
        txpower = int(intf.txpower)
        gain = int(intf.antennaGain)
        gains = txpower + (gain * 2)
        c = 299792458.0
        L = ppm.sL

        lambda_ = c / f  # lambda: wavelength (m)
        denominator = lambda_ ** 2
        self.range = math.pow(10, ((-ppm.noise_th + gains +
                               10 * math.log10(denominator)) /
                              10 - math.log10((4 * math.pi) ** 2 * L)) / 2)
        return self.range

    def path_loss(self, intf, dist):
        """Path Loss Model:
        (f) signal frequency transmited(Hz)
        (d) is the distance between the transmitter and the receiver (m)
        (c) speed of light in vacuum (m)
        (L) System loss"""
        f = intf.freq * 10 ** 9  # Convert Ghz to Hz
        c = 299792458.0
        lambda_ = c / f  # lambda: wavelength (m)
        denominator = lambda_ ** 2
        numerator = (4 * math.pi * dist) ** 2 * ppm.sL
        pl = 10 * math.log10(numerator / denominator)
        return pl

    def twoRayGround(self, intf):
        """Two Ray Ground Propagation Loss Model (does not give a good result for
        a short distance)"""
        gt = int(intf.antennaGain)
        ht = float(intf.antennaHeight)
        pt = int(intf.txpower)
        c = 299792458.0  # speed of light in vacuum
        f = intf.band * 1000000  # frequency in Hz
        gains = pt + gt

        denominator = (c / f) / 1000
        dCross = (4 * math.pi * ht * ht) / denominator
        numerator = (pt * gt * gt * ht ** 2 * ht ** 2)
        self.range = (numerator / (gains - ppm.noise_th)/ppm.sL) * dCross
        return self.range

    def logDistance(self, intf):
        """Log Distance Propagation Loss Model:
        ref_d (m): The distance at which the reference loss is
        calculated
        exponent: The exponent of the Path Loss propagation model, where 2 is
        for propagation in free space
        (dist) is the distance between the transmitter and the receiver (m)"""
        txpower = int(intf.txpower)
        gain = int(intf.antennaGain)
        gains = txpower + (gain * 2)
        ref_d = 1

        pl = self.path_loss(intf, ref_d)
        self.range = math.pow(10, ((-ppm.noise_th - pl + gains) /
                                   (10 * ppm.exp))) * ref_d
        return self.range
    
    def logNormalShadowing(self, intf):
        """Log-Normal Shadowing Propagation Loss Model"""
        from mn_wifi.wmediumdConnector import WmediumdGRandom, w_server, \
            wmediumd_mode

        ref_d = 1
        txpower = int(intf.txpower)
        gain = int(intf.antennaGain)
        gains = txpower + (gain * 2)
        mean = 0
        variance = ppm.variance
        gRandom = round(gauss(mean, variance), 2)
        ppm.gRandom = gRandom

        if wmediumd_mode == 3:
            sleep(0.002)  # noticed problem when there are multiple threads
            w_server.update_gaussian_random(
                WmediumdGRandom(intf.wmIface, gRandom))

        pl = self.path_loss(intf, ref_d) - gRandom
        numerator = -ppm.noise_th - pl + gains
        denominator = 10 * ppm.exp

        self.range = math.pow(10, (numerator / denominator)) * ref_d
        return self.range

    def ITU(self, intf):
        """International Telecommunication Union (ITU) Propagation Loss Model:"""
        f = intf.freq * 10 ** 3
        txpower = int(intf.txpower)
        gain = int(intf.antennaGain)
        gains = txpower + (gain * 2)
        N = 28  # Power Loss Coefficient
        lF = ppm.lF  # Floor penetration loss factor
        nFloors = ppm.nFloors  # Number of Floors

        self.range = math.pow(10, ((-ppm.noise_th + gains -
                                    20 * math.log10(f) - lF * nFloors + 28)/N))
        return self.range


class GetPowerGivenRange(object):
    "Get tx power when the signal range is set"
    txpower = 0

    def __init__(self, intf):
        "Calculate txpower given the signal range"
        if ppm.model in dir(self):
            self.__getattribute__(ppm.model)(intf)

    def friis(self, intf):
        """Path Loss Model:
        distance is the range of the transmitter (m)
        (f) signal frequency transmited(Hz)
        (c) speed of light in vacuum (m)
        (L) System loss"""
        # Convert Ghz to Hz
        dist = intf.range
        f = intf.freq * 10 ** 9
        gain = intf.antennaGain
        c = 299792458.0
        lambda_ = c / f  # lambda: wavelength (m)
        denominator = lambda_ ** 2

        self.txpower = 10 * (
            math.log10((4 * math.pi) ** 2 * ppm.sL * dist ** 2)) + ppm.noise_th \
                       - 10 * math.log10(denominator) - (gain * 2)
        if self.txpower < 0: self.txpower = 1

        return self.txpower

    def path_loss(self, intf, dist):
        """Path Loss Model:
        (f) signal frequency transmited(Hz)
        (d) is the distance between the transmitter and the receiver (m)
        (c) speed of light in vacuum (m)
        (L) System loss"""
        f = intf.freq * 10 ** 9  # Convert Ghz to Hz
        c = 299792458.0
        lambda_ = c / f  # lambda: wavelength (m)
        denominator = lambda_ ** 2
        numerator = (4 * math.pi * dist) ** 2 * ppm.sL
        pl = 10 * math.log10(numerator / denominator)

        return pl

    def twoRayGround(self, intf):
        """Two Ray Ground Propagation Loss Model (does not give a good result for
        a short distance)"""
        # dist = intf.range
        gt = intf.antennaGain
        ht = intf.antennaHeight
        pt = intf.txpower
        c = 299792458.0  # speed of light in vacuum
        f = intf.band * 1000000  # frequency in Hz
        gains = pt + gt

        dCross = ((4 * math.pi * ht) / (c / f)) * ppm.sL
        self.txpower = (dCross * (gains-intf.rssi))/(gt * ht ** 2)
        if self.txpower < 0: self.txpower = 1

        return self.txpower

    def logDistance(self, intf):
        """Log Distance Propagation Loss Model:
        ref_d (m): The distance at which the reference loss is
        calculated
        exponent: The exponent of the Path Loss propagation model, where 2 is
        for propagation in free space
        distance is the range of the transmitter (m)"""
        dist = intf.range
        gain = intf.antennaGain
        g_fixed = (gain * 2)
        ref_d = 1
        pl = self.path_loss(intf, ref_d)
        numerator = math.pow(dist / ref_d, 10 * ppm.exp) * 10 ** pl
        denominator = 10 ** - ppm.noise_th

        self.txpower = int(math.ceil(math.log10(numerator / denominator) - g_fixed))
        if self.txpower < 0: self.txpower = 1

        return self.txpower

    def logNormalShadowing(self, intf):
        """Log-Normal Shadowing Propagation Loss Model
        distance is the range of the transmitter (m)"""
        from mn_wifi.wmediumdConnector import WmediumdGRandom, w_server, \
            wmediumd_mode

        mean = 0
        ref_d = 1
        dist = intf.range
        gain = intf.antennaGain
        variance = ppm.variance
        gRandom = round(gauss(mean, variance), 2)
        ppm.gRandom = gRandom

        if wmediumd_mode == 3:
            sleep(0.001)  # notice problem when there are many threads
            w_server.update_gaussian_random(WmediumdGRandom(
                intf.wmIface, gRandom))

        pl = self.path_loss(intf, ref_d) - gRandom

        self.txpower = 10 * ppm.exp * math.log10(dist / ref_d) + \
                       ppm.noise_th + pl - (gain * 2)
        if self.txpower < 0: self.txpower = 1

        return self.txpower

    def ITU(self, intf):
        """International Telecommunication Union (ITU) Propagation Loss Model:
        distance is the range of the transmitter (m)"""
        dist = intf.range
        f = intf.freq * 10 ** 3
        gain = intf.antennaGain
        lF = ppm.lF  # Floor penetration loss factor
        nFloors = ppm.nFloors  # Number of Floors
        N = 28  # Power Loss Coefficient

        self.txpower = N * math.log10(dist) + ppm.noise_th + \
                       20 * math.log10(f) + lF * nFloors - 28 - (gain * 2)
        if self.txpower < 0: self.txpower = 1

        return self.txpower
