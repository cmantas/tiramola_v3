echo 'data_source "clients" cassandra_client_1' >> /etc/ganglia/gmetad.conf
sed -i 's/data_source "cassandra" .*/ data_source "cassandra" cassandra_seednode/g ' /etc/ganglia/gmetad.conf
ctool be_seed
ctool full_start
service gmetad restart

