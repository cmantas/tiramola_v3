#!/bin/bash 
apt-get update
apt-get install wget -y
wget http://javadl.sun.com/webapps/download/AutoDL?BundleId=78697 -O jre.tar.gz
tar xfz jre.tar.gz
jre=`ls | grep jre1.7`
echo $jre
mkdir /usr/lib/jvm
mv $jre /usr/lib/jvm/
rm /etc/alternatives/java
ln -s /usr/lib/jvm/$jre/bin/java /etc/alternatives/java
ln -s /usr/lib/jvm/$jre/bin/java /usr/bin/java

export JAVA_HOME=/usr/lib/jvm/$jre
echo export JAVA_HOME=/usr/lib/jvm/$jre >> /root/.bashrc

export DEBIAN_FRONTEND=noninteractive; 
$apt-get update -y
#apt-get install -y openjdk-6-jre

#install ganglia
apt-get install ganglia-monitor -y

mkdir /local
#mount /dev/sdc /local
cd /local/

#download cassandra
wget http://archive.apache.org/dist/cassandra/1.2.6/apache-cassandra-1.2.6-bin.tar.gz
tar xfz apache-cassandra-1.2.6-bin.tar.gz

currentNodeIP=`ifconfig eth0 | grep "inet addr" | awk -F: '{print $2}' | awk '{print $1}'`
master=$(ss-get --timeout 360 seedNodeHostname)

sed -i "s/deaf = no/deaf = yes/g" /etc/ganglia/gmond.conf
sed -i "s/host_dmax = 0/host_dmax = 86400/g" /etc/ganglia/gmond.conf
sed -i "s/send_metadata_interval = 0/send_metadata_interval = 10/g" /etc/ganglia/gmond.conf
sed -i "s/name = \"unspecified\"/name = \"Cassandra\"/g" /etc/ganglia/gmond.conf
sed -i "0,/mcast_join/s/mcast_join = 239.2.11.71/host = $master/g" /etc/ganglia/gmond.conf
service ganglia-monitor restart

ss-get --timeout 360 seedNodeReady


multiplicity=$(ss-get CassandraNode.1:multiplicity)
echo "multiplicity=$multiplicity"

#configure cassandra
# cassandra-env change
sed -i 's/# JVM_OPTS="$JVM_OPTS -Djava.rmi.server.hostname=<public name>"/JVM_OPTS="$JVM_OPTS -Djava.rmi.server.hostname='$currentNodeIP'"/g' /local/apache-cassandra-1.2.6/conf/cassandra-env.sh

# cassandra.yaml change
# set token
index=$(ss-get index)
echo "index=$index"
pscript="print ((2**64 / ($multiplicity+1)) * $index) - 2**63"
echo $pscript

token=`python -c "$pscript"`
echo "token=$token"

#sed -i "s/initial_token:/initial_token: $token/g" /local/apache-cassandra-1.2.6/conf/cassandra.yaml
sed -i "s/initial_token:/#initial_token: /g" /local/apache-cassandra-1.2.6/conf/cassandra.yaml
sed -i "s/# num_tokens:/num_tokens: /g" /local/apache-cassandra-1.2.6/conf/cassandra.yaml
sed -i 's/seeds: "127.0.0.1"/seeds: "'$master'"/g' /local/apache-cassandra-1.2.6/conf/cassandra.yaml
sed -i 's/listen_address: localhost/listen_address: '$currentNodeIP'/g' /local/apache-cassandra-1.2.6/conf/cassandra.yaml
sed -i 's/rpc_address: localhost/rpc_address: '$currentNodeIP'/g' /local/apache-cassandra-1.2.6/conf/cassandra.yaml
sed -i 's/var\/lib\/cassandra/local\/cassandra\/data/g' /local/apache-cassandra-1.2.6/conf/cassandra.yaml

#start cassandra
apache-cassandra-1.2.6/bin/cassandra 
sleep 60
ss-set ready true
