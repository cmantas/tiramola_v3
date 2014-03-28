__author__ = 'cmantas'


import socket, struct, sys

multicast_group = '224.3.29.71'
server_address = ('', 10000)

# Create the socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Bind to the server address
sock.bind(server_address)

# Tell the operating system to add the socket to the multicast group
# on all interfaces.
group = socket.inet_aton(multicast_group)
mreq = struct.pack('4sL', group, socket.INADDR_ANY)
sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

print "Multicast Server Running"
# Receive/respond loop
while True:
    print '\nwaiting to receive message'
    data, address = sock.recvfrom(1024)

    print data + ' requestr from %s' % str(address)


    print 'responding to' + str(address)

    if data=="DISCOVER":

        sock.sendto('ACK', address)
