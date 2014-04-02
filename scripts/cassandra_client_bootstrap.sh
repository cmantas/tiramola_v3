sed -i 's/host = .*/host = cassandra_client_1/g' /etc/ganglia/gmond.conf
sed -i 's/name = \"cassandra\"/name = \"clients\"/g' /etc/ganglia/gmond.conf
service ganglia-monitor restart;
