import os
import threading
from threading import Thread as thread

from mininet.log import info
from mn_wifi.mobility import Mobility
from mn_wifi.sumo.sumolib.sumolib import checkBinary
from mn_wifi.sumo.traci import main as traci, _vehicle


class sumo(Mobility):

    vehCmds = None

    def __init__(self, cars, aps, **kwargs):
        Mobility.thread_ = thread(name='vanet', target=self.configureApp,
                                  args=(cars, aps), kwargs=dict(kwargs,))
        Mobility.thread_.daemon = True
        Mobility.thread_._keep_alive = True
        Mobility.thread_.start()

    @classmethod
    def getVehCmd(cls):
        return cls.vehCmds

    def configureApp(self, cars, aps, config_file='',
                     clients=1, port=8813, exec_order=0, extra_params=None):
        if extra_params is None:
            extra_params = []

        try:
            Mobility.cars = cars
            Mobility.aps = aps
            Mobility.mobileNodes = cars
            self.start(cars, config_file, clients, port,
                       exec_order, extra_params)
        except:
            info("*** Connection with SUMO has been closed\n")

    def setWifiParameters(self):
        thread = threading.Thread(name='wifiParameters', target=self.parameters)
        thread.start()

    def start(self, cars, config_file, clients, port,
              exec_order, extra_params):
        sumoBinary = checkBinary('sumo-gui')
        if config_file == '':
            sumoConfig = os.path.join(os.path.dirname(__file__), "data/map.sumocfg")
        else:
            sumoConfig = config_file

        command = ' {} -c {} --num-clients {} --remote-port {} ' \
                  '--time-to-teleport -1'.format(sumoBinary, sumoConfig, clients, port)
        for param in extra_params:
            command = command + " " + param
        command += " &"
        os.system(command)
        traci.init(port)
        traci.setOrder(exec_order)

        self.setWifiParameters()

        vehCmds = _vehicle.VehicleDomain()
        vehCmds._connection = traci.getConnection(label="default")

        while True:
            traci.simulationStep()
            for vehID1 in vehCmds.getIDList():
                x1 = vehCmds.getPosition(vehID1)[0]
                y1 = vehCmds.getPosition(vehID1)[1]

                vehID = int(vehID1.replace('.0',''))
                if vehID < len(cars):
                    cars[vehID].position = x1, y1, 0
                    cars[vehID].set_pos_wmediumd(cars[vehID].position)

                    if hasattr(cars[vehID], 'sumo'):
                        if cars[vehID].sumo:
                            args = [cars[vehID].sumoargs]
                            cars[vehID].sumo(vehID, vehCmds, *args)
                            del cars[vehID].sumo

