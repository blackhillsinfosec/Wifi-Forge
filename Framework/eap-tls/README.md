Example that shows EAP-TLS authentication.

EAP-TLS is a certificate based authentication method. You can read about it here

https://tools.ietf.org/html/rfc5216

To run this example, please go to the CA subdirectory and generate certificates
using the gencerts.sh script.

Then run as follows

sudo -E python eap-tls-auth.py

Try the following experiments

       mininet-wifi> sta1 ping sta2 

If the ping succeeded you're in good shape.

Examine the /tmp/debug1.txt and /tmp/debug2.txt to check out the debug logs of wpa\_supplicant

Examine /tmp/hostapd.txt to check out the debug logs of the hostapd daemon

cat /var/log/syslog | grep hostap to check out the syslog for hostapd.


