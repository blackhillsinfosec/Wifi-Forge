# Use python:3.9 as base
FROM python:3.9

# Create a work directory for mininetwifi project
WORKDIR /app/mininet-wifi

# Install dependencies for mininet wifi over debian which is the base OS for python:3.9 image
RUN apt update 
RUN apt install -y sudo git make help2man pyflakes3 python3-pep8 tcpdump wpan-tools
RUN pip install six numpy matplotlib

# Copy project into the image
COPY . . 

# Fix install script outdated dependencies names solved by this dockerfile.
RUN sed -i 's/pyflakes//g' util/install.sh && sed -i 's/pep8//g' util/install.sh

# Run the installation script
RUN util/install.sh -Wlnfv 

# Set the dafault init to use bash shell
CMD [ "/bin/bash" ]