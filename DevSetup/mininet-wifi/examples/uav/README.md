# Example of Drones integration using CoppeliaSim

First of all you have to install **CoppeliaSim** with the command below:

```
sudo ./examples/uav/install.sh
```

## Running the network topology

Start the network ad hoc scenario with the command below:

```
sudo python examples/uav/uav.py
```

The script above will start Mininet-WiFi and the simulation in CoppeliaSim. In parallel, it will start a remote API capturing the drones' position in the simulation. The Mininet-WiFi Graph is used to observe the nodes' position as well as the signal range.

---
**NOTE**

If there is an error to connect to CoppeliaSim socket, run:
		
```
sudo pkill -9 -f python
```

If CoppeliaSim continue runing after finishing mininet-wifi execution, run:

```
sudo pkill -9 -f coppeliaSim
```
---

By [Fabricio Rodriguez](https://github.com/ecwolf)