#comment all src sources
sed -i.bak s/deb-src/#deb-src/g /etc/apt/sources.list
sudo apt-get purge openjdk-\* -y
add-apt-repository ppa:webupd8team/java -y
apt-get update
echo oracle-java7-installer shared/accepted-oracle-license-v1-1 select true | sudo /usr/bin/debconf-set-selections
apt-get install oracle-java7-installer -y



