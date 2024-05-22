from mn_wifi.cli import CLI
from mn_wifi.net import Mininet_wifi
import os
'''
Estbalish an environment for learning ARP spoofing
See original script here: https://hackmd.io/@ramonfontes/cracking_wep
'''
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

def create_arp_spoof():
    net = Mininet_wifi()

    print("[+] Creating nodes...\n")
    ap1 = net.addAccessPoint('ap1', ssid='new-ssid', mode='g',
                             channel='1', position='10,10,0',
                             failMode="standalone")
    sta1 = net.addStation('sta1', position='10,20,0')
    sta2 = net.addStation('sta2', position='10,30,0')

    print("[+] Configuring wifi nodes...\n")
    net.configureWifiNodes()

    print("[+] Starting network...\n")
    net.build()
    net.addNAT().configDefault()
    ap1.start([])
    
    sta2.cmd('echo 1 > /proc/sys/net/ipv4/ip_forward')


    os.system("clear")
    print_banner()
    print("\n")
    print('                          +-_-_-_- ARP Spoof started Sucessfully -_-_-_-+')
    print('                             Type "xterm a" and press enter to begin')
    print('                            Type exit when the simulation is completed\n')
    CLI(net)
    net.stop()
