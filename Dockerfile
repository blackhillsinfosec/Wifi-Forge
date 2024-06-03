FROM kalilinux/kali-rolling

USER root

COPY xhost /usr/bin/

WORKDIR /wififorge

COPY . .

RUN apt-get update -y && apt-get upgrade --fix-missing -y --no-install-recommends
RUN apt install -y \
     git \
     sudo \
     python3-pip \
     curl \
     wget \
     mininet --allow-downgrades \
     iputils-ping

RUN git config --global --add safe.directory $PWD
RUN git submodule init
RUN git submodule update

RUN git config --global --add safe.directory $PWD/Framework/mininet-wifi/hostapd

RUN python3 -m pip config set global.break-system-packages true


RUN ./Framework/mininet-wifi/util/install.sh -Wlnfv
RUN sudo make -C Framework/mininet-wifi install

