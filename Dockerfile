FROM ubuntu:24.04 as base

USER root

WORKDIR /wififorge

COPY . .
COPY xhost /usr/bin
RUN apt-get update -y && apt-get upgrade --fix-missing -y --no-install-recommends
RUN apt install -y git
RUN apt install -y sudo
RUN apt install -y python3-pip
RUN echo $PWD
RUN git config --global --add safe.directory $PWD
RUN git submodule init
RUN git submodule update

RUN python3 -m pip config set global.break-system-packages true


RUN apt-get install -y --no-install-recommends \
     curl \
#    aircrack-ng \
#    john \
#    dsniff \
     mininet --allow-downgrades \
     iputils-ping
#    openvswitch-testcontroller \
#    openvswitch-switch

RUN ./Framework/mininet-wifi/util/install.sh -Wlnfv
#RUN ln /usr/bin/ovs-testcontroller /usr/bin/controller
RUN sudo make -C Framework/mininet-wifi install
RUN sudo /usr/share/openvswitch/scripts/ovs-ctl start
#CMD python3 Framework/WifiForge.py
