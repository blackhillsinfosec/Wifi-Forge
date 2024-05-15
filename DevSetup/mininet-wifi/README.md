![](https://github.com/ramonfontes/miscellaneous/blob/master/mininet-wifi/mininet-wifi-logo.png)

### About Mininet-WiFi
Mininet-WiFi is a fork of Mininet (http://mininet.org/) which allows the using of both WiFi Stations and Access Points. Mininet-WiFi only add wifi features and you can work with it like you were working with Mininet.   

[![Build Status](https://travis-ci.org/intrig-unicamp/mininet-wifi.svg?branch=master)](https://travis-ci.org/intrig-unicamp/mininet-wifi)

### Things to keep in mind when working with Mininet-WiFi   
* You can use any wireless network tools (e.g. iw, iwconfig, wpa_supplicant, etc)    
* Please consider computer network troubleshooting steps to solve issues before making questions in the mailing list (e.g. is the station associated with ap? Is the OpenFlow rule working correctly? etc)   
* Do you need help? Be careful with questions in the mailing list and please providing as much information you can.

### Mailing List  
[https://groups.google.com/forum/#!forum/mininet-wifi-discuss](https://groups.google.com/forum/#!forum/mininet-wifi-discuss) 

### Use Cases Catalogue   
Please, let us know if you are doing research with Mininet-WiFi. A list of citations on Mininet-WiFi is available [here](https://docs.google.com/spreadsheets/d/1laEhejMg6th-Urgc-_RqBi2H6m308Rnh9uJpKZavEio/edit?usp=sharing).     

## Installation  
**We highly recommend using Ubuntu version 16.04 or higher. Some new hostapd features might not work on Ubuntu 14.04.**  
step 1: $ sudo apt-get install git  
step 2: $ git clone https://github.com/intrig-unicamp/mininet-wifi  
step 3: $ cd mininet-wifi  
step 4: $ sudo util/install.sh -Wlnfv  
#### install.sh options:   
-W: wireless dependencies   
-n: mininet-wifi dependencies    
-f: OpenFlow   
-v: OpenvSwitch   
-l: wmediumd   
_optional_:  
-P: P4 dependencies    
-6: wpan tools

#### Docker
**This is recommended if you are using a different linux distribution from the ones supported by the installation script.** 

If you prefer to use Mininet-WiFi with Docker you should follow the steps described below:

1. Building the docker image:
    ```sh
    docker build -t mn-wifi:v1 .
    ```

2. Running the container: Mininet-WiFi relies on Kernel modules from the host, requires elevated privilege, and the host network interface:

    ```sh
    docker run -it --rm --privileged --env="DISPLAY" --env="QT_X11_NO_MITSHM=1" -v /tmp/.X11-unix:/tmp/.X11-unix:rw --net host -v /sys/:/sys -v /lib/modules:/lib/modules -v /sys/kernel/debug:/sys/kernel/debug -v /var/run/netns:/var/run/netns mn-wifi:v1
    ```

### Building Topologies with GUI

![](https://github.com/ramonfontes/vnd/blob/master/miniedit.png)

I'm a beginner, I do not know Python and I would like to create a customized topology with a GUI. In this case, [MiniEdit](https://github.com/intrig-unicamp/mininet-wifi/blob/master/examples/miniedit.py) can serve as support since it provides a GUI to generate Python scripts. 


### Development
For instructions about easier development check [this helper file](doc/dev_help.md).

## Pre-configured Virtual Machine    
For your convenience, we provide pre-built VM images including Mininet-WiFi and other useful software. The VM images are in .ova format and should be usable with any modern x64 virtualization system.   
  
[[4.6GB Size] - Lubuntu 20.04 x64](https://drive.google.com/file/d/1R8n4thPwV2krFa6WNP0Eh05ZHZEdhw4W/view?usp=sharing) - Mininet-WiFi (_pass: wifi_)     
[[6.7GB Size] - Lubuntu 20.04 x64](https://drive.google.com/file/d/1oozRqFO2KjjxW0Ob47d6Re4i6ay1wdwg/view?usp=sharing) - Mininet-WiFi with P4 (_pass: wifi_)     

   
## Note
Mininet-WiFi should work fine in any Ubuntu distribution from 14.04, but in some cases (only if you have problems when start it) you have to stop _Network Manager_ with either `sudo systemctl stop network-manager` or `sudo service network-manager stop`.    

## Book  
We are glad to announce that the Mininet-WiFi book has been published!   
  
Here is the pointer to the book:   

Printed and e-Book version: https://mininet-wifi.github.io/book/ - Available in English and Portuguese   

Github repository with all use cases presented in the book:   
https://github.com/ramonfontes/mn-wifi-book-pt   

### Team
Ramon dos Reis Fontes (ramon.fontes@imd.ufrn.br)  
Christian Rodolfo Esteve Rothenberg (chesteve@dca.fee.unicamp.br)  

We are members of [INTRIG (Information & Networking Technologies Research & Innovation Group)](http://intrig.dca.fee.unicamp.br) at University of Campinas - Unicamp, SP, Brazil.

