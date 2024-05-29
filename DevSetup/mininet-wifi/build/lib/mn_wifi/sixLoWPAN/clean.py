"""
Mininet-WiFi: A simple networking testbed for Wireless OpenFlow/SDWN!
author: Ramon Fontes (ramonrf@dca.fee.unicamp.br)
"""

from mn_wifi.sixLoWPAN.module import module


class Cleanup(object):
    "Wrapper for cleanup()"

    @classmethod
    def cleanup_6lowpan(cls):
        """Clean up junk which might be left over from old runs;
           do fast stuff before slow dp and link removal!"""
        module.stop()


cleanup = Cleanup.cleanup_6lowpan