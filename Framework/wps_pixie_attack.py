from mininet.term import makeTerm
from mininet.net import Mininet
from mininet.node import Controller
from mininet.cli import CLI
from mn_wifi.net import Mininet_wifi
import os

def print_banner():
    os.system("clear")
    banner = """                             ,                     ,
                            Et                    Et           :                                    
                            E#t                   E#t         t#,                                 ,;
                     t      E##t     t            E##t       ;##W.   j.               .Gt       f#i 
            ;        Ej     E#W#t    Ej           E#W#t     :#L:WE   EW,             j#W:     .E#t  
          .DL        E#,    E#tfL.   E#,          E#tfL.   .KG  ,#D  E##j          ;K#f      i#W,   
  f.     :K#L     LWLE#t    E#t      E#t          E#t      EE    ;#f E###D.      .G#D.      L#D.    
  EW:   ;W##L   .E#f E#t ,ffW#Dffj.  E#t       ,ffW#Dffj. f#.     t#iE#jG#W;    j#K;      :K#Wfff;  
  E#t  t#KE#L  ,W#;  E#t  ;LW#ELLLf. E#t        ;LW#ELLLf.:#G     GK E#t t##f ,K#f   ,GD; i##WLLLLt 
  E#t f#D.L#L t#K:   E#t    E#t      E#t          E#t      ;#L   LW. E#t  :K#E:j#Wi   E#t  .E#L     
  E#jG#f  L#LL#G     E#t    E#t      E#t          E#t       t#f f#:  E#KDDDD###i.G#D: E#t    f#E:   
  E###;   L###j      E#t    E#t      E#t          E#t        f#D#;   E#f,t#Wi,,,  ,K#fK#t     ,WW;  
  E#K:    L#W;       E#t    E#t      E#t          E#t         G#t    E#t  ;#W:      j###t      .D#; 
  EG      LE.        E#t    E#t      E#t          E#t          t     DWi   ,KK:      .G#t        tt 
  ;       ;@         ,;.    ;#t      ,;.          ;#t                                  ;;           """
    print(banner)

def create_wifi_WPS_Pixie_attack():
    net = Mininet_wifi()

    print("*** Creating nodes\n")
    sta1 = net.addStation('sta1', encrypt='wpa2')
    sta2 = net.addStation('sta2', encrypt='wpa2')
    ap1 = net.addAccessPoint('ap1', ssid="secure_wifi", mode="g", channel="1",
                             passwd='123456789a', encrypt='wpa2',
                             failMode="standalone", datapath='user', wps_state='2',
                             config_methods='label display push_button keypad')

    print("Configuring nodes...\n")
    net.configureNodes()

    print("Associating Stations...\n")
    net.addLink(sta1, ap1)
    net.addLink(sta2, ap1)

    print("Starting network...")
    net.build()
    ap1.start([])


    ap1.cmd('hostapd_cli -i ap1-wlan1 wps_ap_pin set 12345670')
    sta1.cmd('iw dev sta1-wlan0 interface add mon0 type monitor')
    sta1.cmd('ip link set mon0 up')
    makeTerm(sta1)  #reaver -i mon0 -b 02:00:00:00:02:00 -vv

    os.system("clear")
    print_banner()
    print("\n")
    print('                    +-_-_-_- WEP 4 Way Hand-shake started Sucessfully -_-_-_-+')
    print('                             Type "xterm a" and press enter to begin')
    print('                            Type exit when the simulation is completed\n')

    CLI(net)

    net.stop()
