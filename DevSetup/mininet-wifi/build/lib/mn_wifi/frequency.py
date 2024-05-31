# @author: Ramon Fontes (ramon.fontes@imd.ufrn.br)

class Frequency(object):

    freq = None

    def __init__(self, mode, channel):
        freq = 'get_freq_2ghz'
        if mode == 'ax5' or mode == 'a' or mode == 'n' or mode == 'ac':
            freq = 'get_freq_5ghz'
        elif mode == 'ax':
            freq = 'get_freq_6ghz'
        if freq in dir(self):
            self.__getattribute__(freq)(channel)

    def get_freq(self, channel, chan_list, freq_list):
        if int(channel) in chan_list:
            idx = chan_list.index(int(channel))
            return freq_list[idx]

    def get_freq_1ghz(self, channel):
        "Gets frequency based on channel number"
        chan_list = [4]
        freq_list = [906500]
        self.freq = self.get_freq(channel, chan_list, freq_list)
        return self.freq

    def get_freq_2ghz(self, channel):
        "Gets frequency based on channel number"
        chan_list = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
        freq_list = [2.412, 2.417, 2.422, 2.427, 2.432, 2.437, 2.442, 2.447, 2.452, 2.457, 2.462]
        self.freq = self.get_freq(channel, chan_list, freq_list)
        return self.freq

    def get_freq_5ghz(self, channel):
        "Gets frequency based on channel number"
        chan_list = [36, 40, 44, 48, 52, 56, 60, 64, 100, 104, 108, 112, 116, 120, 124, 128, 132,
                     136, 140, 149, 153, 157, 161, 165, 169, 171, 172, 173, 174, 175, 176,
                     177, 178, 179, 180, 181, 182, 183, 184, 185]
        freq_list = [5.18, 5.2, 5.22, 5.24, 5.26, 5.28, 5.30, 5.32, 5.50, 5.52, 5.54, 5.56, 5.58, 5.6, 5.62,
                     5.64, 5.66, 5.68, 5.7, 5.745, 5.765, 5.785, 5.805, 5.825, 5.845, 5.855, 5.86, 5.865, 5.87,
                     5.875, 5.88, 5.885, 5.89, 5.895, 5.9, 5.905, 5.91, 5.915, 5.92, 5.925]
        self.freq = self.get_freq(channel, chan_list, freq_list)
        return self.freq

    def get_freq_6ghz(self, channel):
        "Gets frequency based on channel number"
        chan_list = [1, 5, 9, 13, 17, 21, 25, 29, 33, 37, 41, 45, 49, 53, 57, 61, 65, 69, 73, 77, 81,
                     85, 89, 93, 97, 101, 105, 109, 113, 117, 121, 125, 129, 133, 137, 141, 145, 149,
                     153, 157, 161, 165, 169, 173, 177, 181, 185, 189, 193, 197, 201, 205, 209, 213,
                     217, 221, 225, 229, 233]
        freq_list = [5.955, 5.975, 5.995, 6.015, 6.035, 6.055, 6.095, 6.115, 6.135, 6.155, 6.175, 6.195, 6.215, 6.235,
                     6.255, 6.275, 6.295, 6.315, 6.335, 6.375, 6.415, 6.435, 6.455, 6.475, 6.495, 6.515, 6.535, 6.555,
                     6.575, 6.595, 6.615, 6.635, 6.655, 6.675, 6.695, 6.715, 6.735, 6.755, 6.775, 6.795, 6.815, 6.835,
                     6.855, 6.875, 6.895, 6.915, 6.935, 6.955, 6.975, 6.995, 7.015, 7.035, 7.055, 7.075, 7.095, 7.115]
        self.freq = self.get_freq(channel, chan_list, freq_list)
        return self.freq

    def get_freq_60ghz(self, channel):
        "Gets frequency based on channel number"
        chan_list = [1, 2, 3, 4]
        freq_list = [58.320, 60.480, 62.640, 64.800]
        self.freq = self.get_freq(channel, chan_list, freq_list)
        return self.freq