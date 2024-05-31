FROM ubuntu:24.04 as base

USER root

COPY xhost /usr/bin

WORKDIR /wififorge

COPY . .

RUN apt-get update -y && apt-get upgrade --fix-missing -y --no-install-recommends
RUN apt install -y \
     git \
     sudo \
     python3-pip \
     curl \
     wget \
     aircrack-ng \
     dsniff \
     mininet --allow-downgrades \
     iputils-ping

RUN git config --global --add safe.directory $PWD
RUN git submodule init
RUN git submodule update

RUN python3 -m pip config set global.break-system-packages true

RUN chmod +x ./Framework/dependencies.sh
RUN ./Framework/dependencies.sh 

RUN ./Framework/mininet-wifi/util/install.sh -Wlnfv
RUN sudo make -C Framework/mininet-wifi install
RUN service openvswitch-switch start