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

def create_wifi_WEP_attack():
    "Create a network."
    net = Mininet_wifi(controller=Controller)

    print('Creating stations...')
    sta1 = net.addStation('sta1', passwd='1234567891a', encrypt='wep')
    sta2 = net.addStation('sta2', passwd='123456789a', encrypt='wep')
    
    print('Creating the Access Point...')
    ap1 = net.addAccessPoint('ap1', ssid="simplewifi", mode="g", channel="1", passwd='123456789a', encrypt='wep', failMode="standalone", datapath='user')
    c1 = net.addController('c1')
    net.configureWifiNodes()

    print('Adding stations...')
    net.addLink(sta1, ap1)
    net.addLink(sta2, ap1)

    net.build()
    c1.start()
    ap1.start([c1])

    os.system("clear")
    print_banner()
    print("\n")
    print('                    +-_-_-_- WEP 4 Way Hand-shake started Sucessfully -_-_-_-+')
    print('                             Type "xterm a" and press enter to begin')
    print('                            Type exit when the simulation is completed\n')

    CLI(net)

    net.stop()
