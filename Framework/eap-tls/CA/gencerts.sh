
# generate CACRT
openssl req -nodes -new -x509 -sha256 -newkey rsa:4096 -keyout ca.key -out ca.crt -outform PEM -days 3560 -subj "/C=US/ST=Maryland/L=Gaithersburg/O=NIST/OU=ITL/CN=cacert" 

# generate client key and cert
openssl genrsa -out client.key 2048
openssl req -new -key client.key -outform PEM -out client.csr -subj "/C=US/ST=Maryland/L=Gaithersburg/O=NIST/OU=ITL/CN=client" 
openssl x509 -req -in client.csr -CA ca.crt -CAkey ca.key -outform PEM -CAcreateserial -out client.crt

# generate server key and cert
openssl genrsa -out server.key 2048
openssl req -new -key server.key -outform PEM -out server.csr -subj "/C=US/ST=Maryland/L=Gaithersburg/O=NIST/OU=ITL/CN=server" 
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -outform PEM -CAcreateserial -out server.crt


