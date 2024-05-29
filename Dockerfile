FROM ramonfontes/mininet-wifi:latest

USER root

WORKDIR /wififorge

COPY . .
RUN echo "PWD IS: $PWD"
RUN git config --global --add safe.directory $PWD
RUN git submodule init
RUN git submodule update


RUN apt-get update -y && apt-get upgrade --fix-missing -y --no-install-recommends
RUN apt-get install -y --no-install-recommends \
    curl \
    aircrack-ng \
    john \
    dsniff \
    mininet --allow-downgrades\
    openvswitch-testcontroller \
    openvswitch-switch
#RUN chmod u+x Framework/dependenci es.sh
#RUN ./Framework/dependencies.sh
#RUN apt update -y && apt upgrade -y
RUN ./Framework/mininet-wifi/util/install.sh -Wlnfv
RUN ln /usr/bin/ovs-testcontroller /usr/bin/controller
#CMD python3 Framework/WifiForge.py
