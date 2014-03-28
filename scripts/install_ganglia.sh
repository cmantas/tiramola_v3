
#ganglia
apt-get install ganglia-monitor gmetad ganglia-webfrontend -y
#create link in sites-enabled
ln -s /etc/ganglia-webfrontend/apache.conf /etc/apache2/sites-enabled/ganglia.conf 
#replace cluster name with your own CHANGE THE NAME#
sed -i 's/name = "unspecified"/name = "myname"/g' /etc/ganglia/gmond.conf
service apache2 stop && service apache2 start
