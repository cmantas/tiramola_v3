#!/bin/bash


source conf.sh
iptables --table nat  --flush
iptables --delete-chain
iptables --table nat --append POSTROUTING --out-interface eth1 -j MASQUERADE
iptables --append FORWARD --in-interface eth1 -j ACCEPT
#iptables --append FORWARD --in-interface eth2 -j ACCEPT
#iptables -L
#iptables -L
#iptables -t nat -L
echo 1 > /proc/sys/net/ipv4/ip_forward 


iptables -t nat -A PREROUTING -j DNAT -p tcp --dport 50070 --to 192.168.0.3	# use this to get a graphical interface from endpoint

for i in `seq 1 $NUMBER_OF_VMS`; do
		echo "Applying default gw for server$i"
		ssh server$i "route add default gw 192.168.0.2";
done

