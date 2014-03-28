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

#install cassandra
apt-get install cassandra -y --force-yes

#add jna.jar
wget http://repo1.maven.org/maven2/net/java/dev/jna/jna/4.0.0/jna-4.0.0.jar -O /usr/share/cassandra/lib/jna.jar

