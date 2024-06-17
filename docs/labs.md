# Contents
[WPA 2](#WPA-2)

[WEP](#WEP)

[WPS Pixie Dust Attack](#WPS-Pixie-Dust-Attack)

[Evil Twin Attack](#Evil-Twin-Attack)

[Wifiphisher](#Wifiphisher)

[ARPspoof](#ARPspoof)

# WPA 2

To begin the WPA 2 lab, select it from the menu; the following should appear on your screen:
![image](https://github.com/her3ticAVI/Wifi-Forge/assets/95513994/46051586-09de-40a9-9497-9be1d5353392)

The network of this lab consists of an attacker machine "a," from which we will launch our attacks from, and our victim machine. 
This lab will require two terminal windows; type the following command to open a couple of sesions on the attacking machine:
```
xterm a a
```
![image](https://github.com/her3ticAVI/Wifi-Forge/assets/95513994/5530e622-ba36-41e8-afd8-6dc0ba0195e3)

We are going to run a series of commands that will allow us to perform what is called a deauthentication attack. A deauthentication attack is a type of DoS (Denial of Service) attack that blocks the communication between a client and an AP (Access Point) in EEE 802.11 wireless networks by taking advantage of the deauthentication frames.  

 - DoS (Denial of Service) - an attempt to make a computer or network service unavailable to its users by flooding it with a bunch of illegitimate requests.   

 - WLAN (Wireless Local Area Network) - Uses radio waves to transmit data between devices and an Access Point, thus providing a wireless network.   

 - Access Point – A device that creates a WLAN.  It serves as a bridge between wired and wireless network segments.   

 - EEE 802.11 - A set of standards for a WLAN.  Defines all the protocols for wireless communication between different wireless devices.   

 - deauthentication frames – A type of management frame used to terminate a connection between a device and an AP. They signal to the device that the current session is ending.

Type the following in one of the attacker xterm windows:
```
iwconfig
```
![image](https://github.com/her3ticAVI/Wifi-Forge/assets/95513994/a45dc87a-fdbf-4605-a7a7-abf084571618)

Look at a-wlan0. Note that the mode is currently set to managed. We need to switch it to monitor. 
 - Managed Mode - the default mode your wireless uses when connected to an access point. A device in managed mode is primarily concered with its own traffic.
 - Monitor Mode - in monitor mode, a network device can access traffic outside generated by access points and other hosts.

For this lab, a-wlan0 needs to be in monitor mode to access traffic from the AP and other hosts connected to it. Set a-wlan0 to monitor mode using the following command: 
```
airmon-ng start a-wlan0
```
If successful, you should see output similar to the one pictured below:
![image](https://github.com/her3ticAVI/Wifi-Forge/assets/95513994/a34c52c5-167b-4154-9940-5cd90c94817a)
Note the words "mac80211 monitor mode vif enabled" near the bottom of the output. 

We can further verify that the network card is in monitor mode by running iwconfig again. 
![image](https://github.com/her3ticAVI/Wifi-Forge/assets/95513994/859890a4-28f3-4440-b899-86e562f38be6)

Now that the network card is in monitor mode, we can begin our attack!
Within one of the xterm sessions, run:
```
airodump-ng a-wlan0mon
```
This command will scan for network traffic arriving on a-wlan0mon. After a little while, you should see output similar to the following: 
![image](https://github.com/her3ticAVI/Wifi-Forge/assets/95513994/fd544cfa-c25b-43bf-ba3c-51ed28e23bfa)

Here, we see an access point with BSSID 02:00:00:00:04:00 and two hosts with BSSIDs 02 and 03. Remember these station IDs as they will be needed later. 

Leave airodump-ng running and run the next set of commands from your other session. 

```
airodump-ng -c6  - -bssid 02:00:00:00:04:00 a-wlan0mon -w attack 
```
 - -c6 restricts the capture to channel 6 (see the CH column in the output of the previous command)
 - -bssid 02:00:00:00:04:00 specifies the basic service set identifier (BSSID), which provides a unique identifier of a wireless AP in a WiFi network. A MAC address is typically used to represent this value.
 - a-wlan0mon specifies what interface we want to use
 - -w attack specifies what we want to name the output files that will contain the data captured from this command. In this case, the files will be prepended with the name "attack."

output should appear similar to the following screenshot. It may take a few minutes for data to appear. 
![image](https://github.com/her3ticAVI/Wifi-Forge/assets/95513994/503d72f5-8d16-4812-87f0-4e4ccc6e02db)

Switch over to your other xterm session and kill the currently running process with Ctrl + C. 
In the same xterm terminal, type the following:

```
aireplay-ng --deauth 150 -a 02:00:00:00:04:00 -c 02:00:00:00:03:00 a-wlan0mon 
```
  - aireplay-ng is a tool for injecting frames into wireless networks
  - --deauth 150 sends a 150 deauthentication frames to kick a host off the network
  - -a 02:00:00:00:04:00 specifies the BSSID of the AP we are targeting
  - -c 02:00:00:00:03:00 specifies the MAC address of the client we are attacking
  - a-wlan0mon specifies the interface we are using for this attack

You should see the following output: 
![image](https://github.com/her3ticAVI/Wifi-Forge/assets/95513994/e2f45c75-d0dd-4e21-9250-50ac573a66b7)

On the other terminal, the number under the Frames column should start to increase dramatically. 
Wait until the words "WPA handshake: 02:00:00:00:04:00" appear on the top of the terminal window as seen below: 
![image](https://github.com/her3ticAVI/Wifi-Forge/assets/95513994/e4c47eca-80b1-41c6-b1a8-582f52b7adb4)

Once this message is visible, terminate the process with Ctrl + C and run ls to view the capture files that airmon created. The file we will use for this attack will be title atack-01.cap.
We will use a modified rockyou.txt wordlist to crack password for this network. 

 - rockyou - This is a widely used wordlist that includes millions of password combinations.  Fun fact, the website “RockYou” was hacked in 2009, and led to millions of people's passwords being leaked.  The rockyou wordlist is the entire collection of these passwords.

On either of your xterm sessions, run the following command: 

```
aircrack-ng attack-01.cap –w rockyou.txt 
```
- aircrack-ng: Used to crack WEP, WPA, and WPA2-PSK keys
- attack-01.cap: contains the packets collected during our deauth attack
- -w rockyou.txt: spceifies the wordlist to crack 

***Note: rockyou.txt is a *very* very* *very* long wordlist. For this lab, we're using a shorter version to save time***

After a little while, aircrack will crack the password. 
![image](https://github.com/her3ticAVI/Wifi-Forge/assets/95513994/75b862be-21f2-4617-b980-477fdcfa9533)

*THIS COMPLETES THE LAB*

# WEP 
To begin the WEP lab, select it from the menu; the following should appear on your screen:
![image](https://github.com/her3ticAVI/Wifi-Forge/assets/95513994/3955aeac-1bbf-4c0a-adf6-86f1adfc923d)

The network of this lab consists of an attacker machine "a," from which we will launch our attacks from, and our victim machines. 
This lab will require a terminal window for each machine. Type the following to start a session on each:

```
xterm a host1 host2
```
Position the windows so that all three can be seen at once.

For this lab, we'll be generating traffic between two stations using iperf and capturing the generated traffic with airmon and cracking the network key from this traffic with aircrack.
- Iperf: network performance measurement tool
- aircrack-ng: a combination of tools used to assess and enhance WiFi network security. It is primarily used to crack WEP and WPA/WPA2-PSK

To start, run iwconfig in your attacker terminal.
![image](https://github.com/her3ticAVI/Wifi-Forge/assets/95513994/244f2f15-266d-4793-8bf3-3f40fd517e65)

Look at a-wlan0. Note that the mode is currently set to managed. We need to switch it to monitor. 
 - Managed Mode - the default mode your wireless uses when connected to an access point. A device in managed mode is primarily concered with its own traffic.
 - Monitor Mode - in monitor mode, a network device can access traffic outside generated by access points and other hosts.

For this lab, a-wlan0 needs to be in monitor mode to access traffic from the AP and other hosts connected to it. Set a-wlan0 to monitor mode using the following command: 
```
airmon-ng start a-wlan0
```
If successful, you should see output similar to the one pictured below:
![image](https://github.com/her3ticAVI/Wifi-Forge/assets/95513994/a34c52c5-167b-4154-9940-5cd90c94817a)
Note the words "mac80211 monitor mode vif enabled" near the bottom of the output. 

We can further verify that the network card is in monitor mode by running iwconfig again. 
![image](https://github.com/her3ticAVI/Wifi-Forge/assets/95513994/e8988060-3a03-4364-85db-03b14296e6cb)


Now that the network card is in monitor mode, we can begin our attack!
Within your attacker terminal session, run:
```
airodump-ng a-wlan0mon
```
This enables airmon-ng to capture any WiFi traffic it can find, providing information on signal strength, encryption, and more.
At first, the table provided by airmon-ng will be blank.
![image](https://github.com/her3ticAVI/Wifi-Forge/assets/95513994/7be95b66-13f6-47a7-a15e-8810be50bb69)

Allow the process to run until it detects our AP
![image](https://github.com/her3ticAVI/Wifi-Forge/assets/95513994/3ec987d4-9653-4c65-8763-8ed9468cf2c9)

Note the BSSID and channel before killing the process with Ctrl + C.
Run the following command:
```
airodump-ng –c6 -–bssid 02:00:00:00:03:00 a-wlan0mon –w attack 
```
- -c6 restricts the capture to channel 6 (see the CH column in the output of the previous command)
- -bssid 02:00:00:00:03:00 specifies the BSSID (Basic service set identifier) of a device in a Wifi network. This value is usually represented by a MAC address.
- -w attack specifies what we want to name the output files that will contain the data captured from this command. In this case, the files will be prepended with the name "attack."

As the command runs, information regarding hosts connected to the network should appear.   
![image](https://github.com/her3ticAVI/Wifi-Forge/assets/95513994/04a05074-dff4-4842-b622-2f5002c9244f)

We now need to generate traffic on the victim hosts. In a real environment, traffic should not be hard to come by. However, because this is a simulated environment, we need to generate traffic ourselves. 
On host1 run:
```
ifconfig
```
Note the IP address of host1-wlan0
![image](https://github.com/her3ticAVI/Wifi-Forge/assets/95513994/80699bab-7973-485b-a250-011fed8b6b35)

Still on host1, run the following command:
```
iperf -s
```
This enables host1 to listen on port 5001 for traffic. 
![image](https://github.com/her3ticAVI/Wifi-Forge/assets/95513994/4498e3fc-857c-465d-9f76-0138bb1cd083)

On host2, run:
```
iperf -c 10.0.0.2 -u -b 100M -t 60
```
- -c specifies the client mode and IP address of the machine we want to connect to
- -u tells iperf to use UDP (user datagram protocol).
- -b 100M specifies the rate at which to send the data. In this case, 100 Megabytes per second
- -t 60 specifies a run time of 60 seconds
  
host2 will start sending traffic to host1. 
![image](https://github.com/her3ticAVI/Wifi-Forge/assets/95513994/f401c559-5c29-4bc2-b20f-592b6a98150d)
 
Wait until 25,000 data packets have been sent, at which point the host1 and host2 windows can be closed.

On the attacker xterm session, kill the process with Ctrl+c. List the files in the directory using ls and look for attack-01.cap. 
Run the following command:
```
aircrack-ng ./attack-01.cap
```
Aircrack will quickly crack the key using the data obtained from the network capture. 
![image](https://github.com/her3ticAVI/Wifi-Forge/assets/95513994/b98c3268-22ec-4dc0-ab0a-b674803b4ad9)

*THIS COMPLETES THE LAB*

# WPS Pixie Dust Attack

***Note: if wifite fails to detect the network, exit the lab and close all xterm windows before restarting***

To begin the WPS lab, select it from the menu; the following should appear on your screen:
![image](https://github.com/her3ticAVI/Wifi-Forge/assets/95513994/a3757ea5-4912-42d4-9198-a1f4da094c3c)

The network of this lab consists of an attacker machine "a," from which we will launch our attacks from, and our victim machine. 
If an xterm session doesn't automatically open, run the following command to open one:
```
xterm a
```
![image](https://github.com/her3ticAVI/Wifi-Forge/assets/95513994/5530e622-ba36-41e8-afd8-6dc0ba0195e3)

Wi-Fi protected setup is a feature on some routers that allows a user to connect to an AP without manually entering the network key within a certain timeframe of pushing the WPS button. 
While this feature is convienent for quickly connecting to a network, it also comes with vulnerabilities that easily allow an attacker into the network. 

To demonstrate, we will use wifite.

Now run wifite -wps, it may take a while to locate the network. 
![image](https://github.com/her3ticAVI/Wifi-Forge/assets/95513994/3a1330f5-45a7-4291-b1ce-9f06727f6af7)

When the network has been located (ESSID secure_wifi in this case) press Ctrl + C to continue. 

A prompt will appear requesting specification on which network to use. Only one network should be present; input 1 to select it. 
![image](https://github.com/her3ticAVI/Wifi-Forge/assets/95513994/f87718a5-6827-46ac-b259-d14dcb3a439b)

wifite will attempt a series of WPS attacks and eventually reveal the pin. 
![image](https://github.com/her3ticAVI/Wifi-Forge/assets/95513994/10f011e3-dc9a-4a60-a031-a6470e53f8d5)

*THIS COMPLETES THE LAB*

# Evil Twin Attack

To begin the Evil Twin lab, select it from the menu; the following should appear on your screen: 
![image](https://github.com/her3ticAVI/Wifi-Forge/assets/95513994/62db1ed9-f7ac-428e-a02f-971c568d984d)

The network of this lab consists of an attacker machine "a," from which we will launch our attacks from, and our victim machine. 
Run the following command within the mininet-wifi CLI to start an xterm session on the attacker machine.
```
xterm a
```

Within the xterm session, cd into the framework directory and run eaphammer:
```
./eaphammer -e CORP-SECURE --creds --interface a-wlan0
```
- eaphammer is a toolkit for performing targeted evil twin attacks against WPA2-Enterprise networks.
- -e CORP-SECURE specifies the essid to imitate. In this case, the network is CORP-SECURE
- --creds specifies that we want to capture credentials
- --interface a-wlan0 specifies the interface to launch the attack from

Note that in the current state of WifiForge, eaphammer and its output are simulated due to the limitations of the environment.

Running the command should provide the following output: 
![image](https://github.com/her3ticAVI/Wifi-Forge/assets/95513994/812a125f-9fbb-4aa0-9bd3-f313bf084666)

Successful initialization is indicated by the following: 
![image](https://github.com/her3ticAVI/Wifi-Forge/assets/95513994/8ad85a5b-7867-4f79-a782-7cdb101d4071)

If the tool works correctly, the following information should appear at the bottom of the output after a length of time. 
![image](https://github.com/her3ticAVI/Wifi-Forge/assets/95513994/22aebb4e-229c-4f21-8b7f-0cd1e479f3f4)

This output indicates that a host connected to our evil twin, from which eaphammer collected the victim's hashes. 
A hash is a computation designed to scramble something into something else **less decipherable.* Eaphammer provides two 
hashes, one for hashcat and another for jtr (john the ripper). A copy of these hashes are saved in the Framework/loot directory. 

![image](https://github.com/her3ticAVI/Wifi-Forge/assets/95513994/a4d25b82-285d-4db3-a231-8e4050138711)

After obtaining the hashes, it's time to attempt to crack them using john the ripper. 
John can crack hashes using a wordlist or a mask. Cracking a password from a mask allows us to guess a password from some information we might already know. 
For example, in this scenario, say know that a commonly used password in our target network is Badpass[some number], 
we can then use john to guess other users’ passwords with the following commands:
```
Echo 'johnnie.doyle@lab.local$NETNTLM$65c09d9d0f121f7d$5eb76975d83fee344ededca6fb86e8b04fde87c3cde150ff' > johnnie.hash 

john --format=netntlm johnnie.hash --mask='Badpass?d' --min-length=7 --max-length=13 --pot=/opt/wifilabs/johnnie.pot 
```

If successful, the password will appear in gold as in the screenshot below: 
![image](https://github.com/her3ticAVI/Wifi-Forge/assets/95513994/8afc79ac-09ec-4c16-9353-f96e7280e511)

*THIS COMPLETES THE LAB*

# Wifiphisher 

To begin the Wifiphisher lab, select it from the menu; the following should appear on your screen:
![image](https://github.com/her3ticAVI/Wifi-Forge/assets/95513994/927db2e9-31e2-42dd-8611-8b01b6610e38)


The network of this lab consists of an attacker machine "a," from which we will launch our attacks from, and our victim machine. 
Start an xterm session on both the attacker and host machines using the following command: 
```
xterm a host1
```
Within the xterm terminal, use the command "ip a" to view the IPs of the interfaces:
![image](https://github.com/her3ticAVI/Wifi-Forge/assets/95513994/a6b34730-5115-4e44-a9cf-11d987657db3)

Type wifiphisher -h to view the help menu

![image](https://github.com/her3ticAVI/Wifi-Forge/assets/95513994/0bacbfe2-4100-425d-b2f7-1d3b18dab615)

The next command will use wifiphisher to create a lookalike corporate network to entice wireless client connections.
Once connected, the wifi_connect template will reidrect all requests to a phishing page. The phishing page is
designed to look like a Windows wireless network connection manager. 
```
Wifiphisher –e CORP-RETAIL –p wifi_connect –kB
```
- -e CORP-RETAIL specifies the ESSID we want to immitate
- -p wifi_connect specifies the attack we want to use
- -kB tells wifiphisher to advertise a list of ESSIDs

The following should appear on your screen after running the command: 
![image](https://github.com/her3ticAVI/Wifi-Forge/assets/95513994/219cbb89-9b24-4c3d-865b-ed0eef5104bd)

After a few seconds, the following screen, called the operator's console, should appear. 
![image](https://github.com/her3ticAVI/Wifi-Forge/assets/95513994/889c01d0-a5de-405b-8b64-8a10ddb89496)

The goal of this attack aims to trick a device into connecting to one of these fake networks, 
either because a user believes the network to be legitimate, or because the machine itself believes
the network is one it's connected to before and automatically connects to it. 

Switch over to host1 and play the part of the victim using the following command: 
```
iwlist host1-wlan0 scan
```
A handful of networks should appear. All of these networks are fake networks generated by eaphammer. 
If you run the command again, you might find the list has changed or that more networks have shown up.
![image](https://github.com/her3ticAVI/Wifi-Forge/assets/95513994/93d7fcb9-5aa9-4174-9e1d-04e7b984d44b)

You should also see the ESSID we specified in the wifiphisher command
![image](https://github.com/her3ticAVI/Wifi-Forge/assets/95513994/287db902-f0b3-4330-bfb6-ebacebf61742)

Simulate a victim connecting to this network using the following command: 
```
iwconfig host1-wlan0 essid CORP-RETAIL
```

The following output should appear on the operator's console upon a successful connection
![image](https://github.com/her3ticAVI/Wifi-Forge/assets/95513994/7b72f013-baae-482c-a087-64f1b834ac82)

Within host1, use the browser script in the framework directory to start a chrome browser with a windows user agent
```
./browser windows
```
A chrome browser should appear, type 10.0.0.1 (or the IP of the wifiphisher interface) to access the captive portal
that would normally automatically appear when a victim connects. Note how the landing page looks like a windows OS
network login tab. However, it's all fake! 
![image](https://github.com/her3ticAVI/Wifi-Forge/assets/95513994/7ab9812f-fc41-4709-bf6e-eb1368eb9ecb)

Input a password (don't use your real passwords, of course!) and check the operator's console:
![image](https://github.com/her3ticAVI/Wifi-Forge/assets/95513994/208d0c55-179c-4d3b-b08e-489508a39e7a)

Wifiphisher uses a different landing page for Linux and iOS clients. 
To view this landing page, close chrome, and start a new session with the following command:
```
./browser linux
```

Navigating to 10.0.0.1 (or the IP of the wifiphisher interface) provides a landing page with a different look.
![image](https://github.com/her3ticAVI/Wifi-Forge/assets/95513994/0699e602-7494-4fa4-b814-482ac607e0f9)

*THIS COMPLETES THE LAB*

# ARPspoof 

To begin the ARPspoof lab, select it from the menu; the following should appear on your screen:
![image](https://github.com/her3ticAVI/Wifi-Forge/assets/95513994/927db2e9-31e2-42dd-8611-8b01b6610e38)


The network of this lab consists of an attacker machine "a," from which we will launch our attacks from, and our victim machine. 
Start two xterm sessions on the attacker machine and one on the victim using the following command: 
```
xterm a a host1
```

From host1's xterm session, ping google.com.
```
ping -c1 google.com
```
Check host1's ARP table
```
arp -a
```

The entry in the ARP table corresponds to the network's router
![image](https://github.com/her3ticAVI/Wifi-Forge/assets/95513994/8f0f14d8-4037-4dbf-bc4f-028e9a730b73)

ARPspoof is a tool that allows us to trick a victim into routing its traffic through us before the router. 
Run the following command on the attacking machine: 
```
arpspoof -i a-wlan0 -t 10.0.0.2 -r 10.0.0.4
```
- -i a-wlan0 specifies the interface the launch the attack from
- -t 10.0.0.2 specifies the IP of the victim (in this case host1)
- -r 10.0.0.4 specifies the target network's AP (check the IP of the router by typing "ip a" in an ap1 xterm session)
![image](https://github.com/her3ticAVI/Wifi-Forge/assets/95513994/4be28ece-bd5d-4b6a-8798-0b70c51327b1)


On host1, check the ARP table again
```
arp -a
```
Notice that the IP of our attacker machine now shows up in the arp table.  
![image](https://github.com/her3ticAVI/Wifi-Forge/assets/95513994/f1e26857-5a05-4582-8ca6-509cfa69514c)

We can now observe the network traffic coming and going to host1 from our attacking machine. 
On the attacking machine, run 
```
tcpdump -i a-wlano
```
- tcpdump is a traffic analysis tool that displays the traffic coming and going from an interface
- -i a-wlan0 specifies that tcpdump should use the interface that has host1's traffic running through it

on host1, ping google.com again and observe the tcpdump on the attacker machine.
![image](https://github.com/her3ticAVI/Wifi-Forge/assets/95513994/5deb6f77-3853-4452-b1d4-1ffb6d861c21)

*THIS COMPLETES THE LAB*