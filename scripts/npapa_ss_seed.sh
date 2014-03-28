#!/bin/bash 
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
apt-get update -y
#apt-get install -y openjdk-6-jre

currentNodeIP=`ifconfig eth0 | grep "inet addr" | awk -F: '{print $2}' | awk '{print $1}'`

#install ganglia
apt-get install ganglia-monitor gmetad ganglia-webfrontend -y

#sed -i "s/deaf = no/deaf = yes/g" /etc/ganglia/gmond.conf
sed -i "s/host_dmax = 0/host_dmax = 86400/g" /etc/ganglia/gmond.conf
sed -i "s/send_metadata_interval = 0/send_metadata_interval = 10/g" /etc/ganglia/gmond.conf
sed -i "s/name = \"unspecified\"/name = \"Cassandra\"/g" /etc/ganglia/gmond.conf
sed -i "0,/mcast_join/s/mcast_join = 239.2.11.71/host = $currentNodeIP/g" /etc/ganglia/gmond.conf
sed -i '/mcast_join/d' /etc/ganglia/gmond.conf
sed -i '/bind/d' /etc/ganglia/gmond.conf
service ganglia-monitor restart

sed -i "s/data_source \"my cluster\" localhost/data_source \"Cassandra\" $currentNodeIP/g" /etc/ganglia/gmetad.conf

cp /etc/ganglia-webfrontend/apache.conf /etc/apache2/sites-enabled/

service ganglia-monitor restart
service gmetad restart
service apache2 restart

mkdir /local
#mount /dev/sdc /local
cd /local/

#download cassandra
wget http://archive.apache.org/dist/cassandra/1.2.6/apache-cassandra-1.2.6-bin.tar.gz
tar xfz apache-cassandra-1.2.6-bin.tar.gz

master=$currentNodeIP
#ss-set hostname $currentNodeIP

#configure cassandra

# cassandra-env change
sed -i 's/# JVM_OPTS="$JVM_OPTS -Djava.rmi.server.hostname=<public name>"/JVM_OPTS="$JVM_OPTS -Djava.rmi.server.hostname='$currentNodeIP'"/g' /local/apache-cassandra-1.2.6/conf/cassandra-env.sh

# cassandra.yaml change
#sed -i "s/initial_token:/initial_token: -9223372036854775808/g" /local/apache-cassandra-1.2.6/conf/cassandra.yaml
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

wget https://github.com/downloads/brianfrankcooper/YCSB/ycsb-0.1.4.tar.gz
tar xfz ycsb-0.1.4.tar.gz

#mkdir /local/usertable
#mkdir /local/usertable/fields
#cd /local/useratble/fields
#time wget ftp://tank.cslab.ntua.gr/usertable/fields/*
#cd /local/

#apt-get install curlftpfs
#mkdir /mnt/my_ftp
#curlftpfs anonymous:anonymous@tank.cslab.ntua.gr /mnt/my_ftp/

multiplicity=$(ss-get CassandraNode.1:multiplicity)
echo "multiplicity=$multiplicity"

for i in `seq 1 $multiplicity`
do
   echo "Waiting node $i"
   ss-get --timeout 3600 CassandraNode.$i:ready
done

echo -e "create keyspace usertable \n   with placement_strategy = 'org.apache.cassandra.locator.SimpleStrategy' \n   and strategy_options = {replication_factor:1}; \nuse usertable; \ncreate column family data; \nshow keyspaces;\n" > schema.cql

./apache-cassandra-1.2.6/bin/cassandra-cli -h $master -p 9160 -f schema.cql

#./apache-cassandra-1.2.6/bin/sstableloader -d $master /local/usertable/fields
./ycsb-0.1.4/bin/ycsb load cassandra-10 -threads 20 -P ycsb-0.1.4/workloads/workloada -p hosts=$master -p recordcount=1000000 -s

ss-set loaded true
./apache-cassandra-1.2.6/bin/nodetool -host $master status
