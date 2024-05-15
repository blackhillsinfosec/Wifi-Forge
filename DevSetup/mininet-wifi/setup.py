#!/usr/bin/env python

"Setuptools params"

from setuptools import setup
from os.path import join

# Get version number from source tree
import sys
sys.path.append( '.' )
from mn_wifi.net import VERSION

scripts = [ join( 'bin', filename ) for filename in [ 'mn' ] ]

modname = distname = 'mininet-wifi'

setup(
    name=distname,
    version=VERSION,
    description='Process-based SDN emulator',
    author='Bob Lantz; and Ramon Fontes',
    author_email='rlantz@cs.stanford.edu; ramonrf@dca.fee.unicamp.br',
    packages=['mn_wifi', 'mn_wifi.sixLoWPAN', 'mn_wifi.wwan', 'mn_wifi.data', 'mn_wifi.examples',
              'mn_wifi.examples.eap-tls', 'mn_wifi.examples.eap-tls.CA', 'mn_wifi.examples.p4',
              'mn_wifi.sumo', 'mn_wifi.sumo.sumolib', 'mn_wifi.sumo.traci',
              'mn_wifi.sumo.data', 'mn_wifi.sumo.sumolib.net', 'mn_wifi.sumo.sumolib.output',
              'mn_wifi.sumo.sumolib.shapes', 'util'],
    package_data={'util' : ['m'], 'mn_wifi.sumo.data': ['*.xml', '*.sumocfg'],
                  'mn_wifi.data': ['signal_table_ieee80211ax',
                                   'signal_table_ieee80211n_gi20',
                                   'signal_table_ieee80211n_gi40',
                                   'signal_table_ieee80211n_sgi20',
                                   'signal_table_ieee80211n_sgi40'],
                  'mn_wifi.examples.eap-tls': ['eap_users'],
                  'mn_wifi.examples.eap-tls.CA': ['*.sh'],
                  'mn_wifi.examples.p4': ['*.json']},
    long_description="""
        Mininet-WiFi is a network emulator which uses lightweight
        virtualization to create virtual networks for rapid
        prototyping of Software-Defined Wireless Network (SDWN) designs
        using OpenFlow.
        """,
    classifiers=[
          "License :: OSI Approved :: BSD License",
          "Programming Language :: Python",
          "Development Status :: 5 - Production/Stable",
          "Intended Audience :: Developers",
          "Topic :: System :: Emulators",
    ],
    keywords='networking emulator protocol Internet OpenFlow SDN',
    license='BSD',
    install_requires=[
        'setuptools', 'matplotlib'
    ],
    scripts=scripts,
)
