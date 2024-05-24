# WI-Fi Forge

![Pasted image 20240516111408](https://github.com/her3ticAVI/MiniNet-Framework/assets/95513994/211da053-38ad-4f92-9cf3-920570dca8b3)

## About Wifi-Forge

Wi-Fi Forge provides a safe environment for learning WiFi hacking via [Mininet-Wifi](https://github.com/intrig-unicamp/mininet-wifi/tree/master?tab=readme-ov-file) and [Mininet](https://github.com/mininet/mininet), which creates software defined networks within a single host machine. Wi-Fi Forge provides pre-built labs that can be setup and completed with minimal overhead all from a single laptop without any additional hardware.

#### Disclaimer/Notes

- Mininet and Wifi Forge only runs on Ubuntu operating systems. 
- It is suggested to run Wifi Forge on Ubuntu version 14.04 or greater. 
- The Wifi Forge installation script may disrupt normal operating system use, it is suggested to use a fresh install or virtual machine

## Set-Up Guide

Clone the repository
```
git clone https://github.com/her3ticAVI/MiniNet-Framework
cd MiniNet-Framework/Framework
sudo python3 WifiForge.pyRED = "\033[91m"
GREEN = "\033[92m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
RESET = "\033[0m"

# BANNER CALL
def print_banner():
    os.system("clear")
    print("""                             ,                     ,                                                 
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
   ;       ;@         ,;.    ;#t      ,;.          ;#t                                  ;;           """)

```

##Labs

Wi-Fi Forge provides pre-built labs that cover the following:

- WPA 4 Way Handshakes
- Cracking Wifi Key Encryption
- The tool eaphammer
- WPS Pixie Dust Attacks
- WEP wifi attakcs
- The ARP Spoof tool and downgrading ssl
- The aircrack-ng tool suite
- John the Ripper "JOHN"

## Links and Further Reading 

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
