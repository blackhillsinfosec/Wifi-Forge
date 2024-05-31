FROM ubuntu:24.04 as base

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
     aircrack-ng \
     dsniff \
     mininet --allow-downgrades \
     iputils-ping

RUN git config --global --add safe.directory $PWD
RUN git config --global --add safe.directory $PWD/Framework/john
RUN git submodule init
RUN git submodule update

RUN git config --global --add safe.directory $PWD/Framework/mininet-wifi/hostapd

RUN python3 -m pip config set global.break-system-packages true


RUN chmod +x ./Framework/dependencies.sh
RUN ./Framework/dependencies.sh 

RUN ./Framework/mininet-wifi/util/install.sh -Wlnfv
RUN sudo make -C Framework/mininet-wifi install

#setup john
RUN apt install libssl-dev
RUN ./Framework/john/src/configure
RUN make -C Framework/john/src -s clean && make -C Framework/john/src -sj4

CMD /wififorge# printf "nameserver 8.8.8.8\noptions edns0 trust-ad\nsearch home\n" > /etc/resolv.conf;service openvswitch-switch start
