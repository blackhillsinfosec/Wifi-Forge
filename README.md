<div style="text-align: center;">
  <img src="https://github.com/her3ticAVI/MiniNet-Framework/blob/main/images/wifi.png" alt="Wi-Fi Forge Banner">
</div>

# Wi-Fi Forge

Wi-Fi Forge provides a safe and legal environment for learning WiFi hacking. Based on the open source [Mininet-Wifi](https://github.com/intrig-unicamp/mininet-wifi/tree/master?tab=readme-ov-file), this project automatically sets up the networks and tools needed to run a variety of WiFi exploitation labs, removing the need for the overhead and hardware normally required to perform these attacks. 

## Disclaimer/Notes

- The installation script will only run on Ubuntu, Debian, or Fedora systems. 
- It is suggested to run Wifi Forge on Ubuntu version 14.04 or greater. 
- The Wifi Forge installation script may disrupt normal operating system use, it is suggested to use a fresh install, virtual machine, or build using the provided dockerfile (see Set-Up Guide/Docker)

## Set-Up Guide

### Docker (recommended)

#### Install from release

1. Download from releases
2. Load the image
  ```bash
  sudo docker load < wififorge.tar
  ```
3. Start a new container
  ```bash
  sudo docker run --privileged=true -it --env="DISPLAY" --env="QT_X11_NO_MITSHM=1" -v /tmp/.X11-unix:/tmp/.X11-unix:rw -v /sys/:/sys -v /lib/modules/:/lib/modules/ --name mininet-wifi --network=host --hostname mininet-wifi wififorge /bin/bash
  ```
4. Within docker, initiate the controller to simulate APs
```bash
RUN service openvswitch-switch start
```
5. Run wififorge.py
```bash
sudo python3 Framework/WifiForge.py
```
#### Build from Dockerfile

1. Install Docker
```bash
sudo snap install docker
```

2. Clone the repository
```bash
git clone https://github.com/her3ticAVI/MiniNet-Framework
```

3. Run the Dockerfile (may take up to 10 minutes)
```bash
sudo docker build -t wififorge .
```

4. Start a new container (command should automatically initiate a docker shell)
```bash
sudo docker run --privileged=true -it --env="DISPLAY" --env="QT_X11_NO_MITSHM=1" -v /tmp/.X11-unix:/tmp/.X11-unix:rw -v /sys/:/sys -v /lib/modules/:/lib/modules/ --name mininet-wifi --network=host --hostname mininet-wifi wififorge /bin/bash
```

5. Within docker, initiate the controller to simulate APs
```bash
RUN service openvswitch-switch start
```

6. Within docker, run WifiForge.py
```bash
sudo python3 Framework/WifiForge.py
```
### Build from Source


NOTE: While the setup script is generally stable, running the auto installer directly on  your machine may disrupt your operating system in a way that renders it unusable. 

1. Clone the repository
```bash
git clone https://github.com/her3ticAVI/MiniNet-Framework
```

2. Run Wi-Fi Forge to perform first time setup (may take up to 10 minutes)
```bash
cd MiniNet-Framework/Framework
sudo python3 WifiForge.py
```

## Labs and Featured Tools

Wi-Fi Forge provides pre-built labs that cover the following:

- ARP spoofing
- Evil twin 
- WEP cracking
- WPA2 cracking
- WPS exploitation 

## Links and Further Reading 

- https://mininet-wifi.github.io/ 
- [https://www.hackingarticles.in/wireless-penetration-testing-pmkid-attack/](https://www.hackingarticles.in/wireless-penetration-testing-pmkid-attack/)
- [https://en.wikipedia.org/wiki/IEEE_802.11i-2004](https://en.wikipedia.org/wiki/IEEE_802.11i-2004)
- [https://www.wildwesthackinfest.com](https://www.wildwesthackinfest.com)
- [https://nmap.org/](https://nmap.org/)
- [https://en.wikipedia.org/wiki/Situation_awareness](https://en.wikipedia.org/wiki/Situation_awareness)
- [https://www.educba.com/linux-network-manager/](https://www.educba.com/linux-network-manager/)
- [https://www.aircrack-ng.org/](https://www.aircrack-ng.org/)
- [https://www.aircrack-ng.org/doku.php?id=airodump-ng](https://www.aircrack-ng.org/doku.php?id=airodump-ng)
- [https://www.aircrack-ng.org/doku.php?id=cracking_wpa](https://www.aircrack-ng.org/doku.php?id=cracking_wpa)
- [https://charlesreid1.com/wiki/Aircrack_and_John_the_Ripper](https://charlesreid1.com/wiki/Aircrack_and_John_the_Ripper)


