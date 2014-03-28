#http://www.synnefo.org/docs/kamaki/latest/installation.html
sudo add-apt-repository -y ppa:grnet/synnefo


sudo apt-get update

sudo apt-get install -y python-software-properties

#ganglia
apt-get install ganglia-monitor gmetad ganglia-webfrontend -y
ln -s /etc/ganglia-webfrontend/apache.conf /etc/apache2/sites-enabled/ganglia.conf #create link in sites-enabled
service apache2 stop && service apache2 start

#YCSB
#download from pithos
#ganglia v02
wget --no-check-certificate https://pithos.okeanos.grnet.gr/public/bvxcJwNyNbC6d1BQMNOdC1 -O YCSB.tar.gz
tar -xvf YCSB.tar.gz -C /etc && rm YCSB.tar.gz && mv /etc/ycsb-*/ /etc/YCSB
echo "export WORKLOADS=/etc/YCSB/workloads" >> ~/.bashrc
echo "export PATH=$PATH:/etc/YCSB/bin/:" >> ~/.bashrc

#kamaki related
sudo apt-get install -y python-ansicolors
sudo apt-get install -y python-mock
sudo apt-get install -y kamaki

#dissable network manager
#/etc/NetworkManager/NetworkManager.conf -> managed=false
#in /etc/network/interfaces add
#

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
#remove grub-timeout
sed -i -e"s/GRUB_TIMEOUT=.*/GRUB_TIMEOUT=0/" /etc/default/grub && update-grub
