#!/bin/sh
tiramola bootstrap_cluster used=16
tiramola load_data records=3000000
tiramola run_sinusoid target=11000 offset=0 period=6000
tiramola monitor time=300 &>test_degradation.out &

#sleep to see original throughput
sleep 2400

# remove some nodes
tiramola remove_nodes count=2
#sleep to see troughput
sleep 120
#remove some more
tiramola remove_nodes count=2
#sleep to see troughput
sleep 120
#remove some more
tiramola remove_nodes count=2
#sleep to see troughput
sleep 120
#remove some more
tiramola remove_nodes count=2

#stay 5min in the bottom state
sleep 300

tiramola add_nodes count=3
sleep 120

tiramola add_nodes count=3
sleep 120

tiramola add_nodes count=2

#wait at top state
sleep 7200


tiramola kill_workload
