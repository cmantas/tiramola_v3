sudo apt-get purge openjdk-\* -y
sudo mkdir -p /usr/local/java
wget --no-cookies --no-check-certificate --header "Cookie: gpw_e24=http%3A%2F%2Fwww.oracle.com%2F" "http://download.oracle.com/otn-pub/java/jdk/7u45-b18/jdk-7u45-linux-x64.tar.gz" -O java.tar.gz
sudo tar xvzf java.tar.gz -C /usr/local/java
mv /usr/local/java/jdk* /usr/local/java/jdk
#add path vars to etc profile
sudo echo '
JAVA_HOME=/usr/local/java/jdk
PATH=$PATH:$HOME/bin:$JAVA_HOME/bin
export JAVA_HOME
export PATH
' >> /etc/profile
#update alternatives
sudo update-alternatives --install "/usr/bin/java" "java" "/usr/local/java/jdk/bin/java" 1
sudo update-alternatives --install "/usr/bin/javac" "javac" "/usr/local/java/jdk/bin/javac" 1
sudo update-alternatives --install "/usr/bin/javaws" "javaws" "/usr/local/java/jdk/bin/javaws" 1
#reload etc/prfile
. /etc/profile
