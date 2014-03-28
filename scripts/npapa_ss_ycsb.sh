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

cd /opt/
wget https://github.com/downloads/brianfrankcooper/YCSB/ycsb-0.1.4.tar.gz
tar xfz ycsb-0.1.4.tar.gz
cd ycsb-0.1.4

master=$(ss-get --timeout 360 seedNodeHostname)
ss-get --timeout 100000 seedNodeDataLoaded

bin/ycsb run cassandra-10 -P workloads/workloada  -threads 20 -p maxexecutiontime=100000000 -p hosts=$master -p operationcount=10000000 -p recordcount=1000 -s
