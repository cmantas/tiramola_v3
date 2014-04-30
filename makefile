default:
	#doing nothing
sync:
	rsync -av * torchestrator:~/bin/tiramola
clean:
	tiramola kill_nodes
	tiramola kill_workload &
	tiramola bootstrap_cluster used=8
	tiramola load_data records=10000000
	rm files/logs/measurements.txt; rm files/logs/discarded-measurements.txt
train:
	rm files/logs/measurements.txt
	tiramola train

experiment1:
	tiramola run_sinusoid target=10000 offset=8000 period=3600
	tiramola auto_pilot
experiment2:
	tiramola run_sinusoid target=10000 offset=8000 period=7200
	tiramola auto_pilot
