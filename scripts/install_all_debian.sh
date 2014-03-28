echo "deb http://ftp.gr.debian.org/debian wheezy-backports main" >> /etc/apt/sources.list

#java
apt-get purge openjdk-\* -y
echo "deb http://ppa.launchpad.net/webupd8team/java/ubuntu precise main" | tee -a /etc/apt/sources.list
echo "deb-src http://ppa.launchpad.net/webupd8team/java/ubuntu precise main" | tee -a /etc/apt/sources.list
apt-key adv --keyserver keyserver.ubuntu.com --recv-keys EEA14886
#define cassanra repo
cassandra_repo="deb http://www.apache.org/dist/cassandra/debian 20x main"
echo "Casssandra repo: $cassandra_repo"
echo $cassandra_repo >> /etc/apt/sources.list
#add cassandra repo keys
gpg --keyserver pgp.mit.edu --recv-keys F758CE318D77295D
gpg --export --armor F758CE318D77295D | sudo apt-key add -
gpg --keyserver pgp.mit.edu --recv-keys 2B5C1B00
gpg --export --armor 2B5C1B00 | sudo apt-key add -


apt-get update
apt-get upgrade -y

echo oracle-java7-installer shared/accepted-oracle-license-v1-1 select true | /usr/bin/debconf-set-selections
apt-get install oracle-java7-installer oracle-java7-set-default -y

#install cassandra
apt-get install cassandra -y --force-yes

#ganglia
apt-get install ganglia-monitor gmetad ganglia-webfrontend -y
ln -s /etc/ganglia-webfrontend/apache.conf /etc/apache2/sites-enabled/ganglia.conf #create link in sites-enabled
service apache2 stop && service apache2 start

#YCSB
#download from pithos
wget --no-check-certificate https://pithos.okeanos.grnet.gr/public/qEAz3J3FdxvxhdwoKDZGV -O YCSB.tar.gz
tar -xvf YCSB.tar.gz -C /etc && rm YCSB.tar.gzls
echo "export WORKLOADS=/etc/YCSB/workloads" >> ~/.bashrc
echo "export PATH=$PATH:/etc/YCSB/bin/:" >> ~/.bashrc

#service configuration
apt-get install -y rcconf

#cpufreq
apt-get install cpufrequtils -y
echo 'GOVERNOR="performance"' >/etc/default/cpufrequtils

#dissable swappiness
echo -e "vm.swappiness=0\nvm.vfs_cache_pressure=50" >> /etc/sysctl.conf

#speed up boot
apt-get install insserv readahead -y
echo 'CONCURRENCY=shell' >> /etc/default/rcS
touch /etc/readahead.d/profile-once

#kernel
apt-get -t wheezy-backports install linux-image-3.12-0.bpo.1-amd64 -y
apt-get purge linux-image-3.2.0-4-amd64 && update-grub

#interfaces
echo "auto lo
iface lo inet loopback
auto eth2
iface eth2 inet dhcp
auto eth1
iface eth1 inet dhcp" > /etc/network/interfaces

