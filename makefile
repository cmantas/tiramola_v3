default:
	tiramola auto_pilot minutes=1001
	#doing nothing
sync:
	rsync -av * torchestrator:~/bin/tiramola
clean:
	tiramola kill_nodes
	tiramola kill_workload 
	tiramola bootstrap_cluster used=8
	tiramola load_data records=10000000
	rm files/logs/measurements.txt &>/dev/null
clean_quick:
	tiramola kill_nodes
	tiramola kill_workload 
	tiramola bootstrap_cluster used=8
	tiramola load_data records=10000
	rm files/logs/measurements.txt &>/dev/null
train:
	rm files/logs/measurements.txt
	tiramola train

experiment1:
	tiramola run_sinusoid target=10000 offset=8000 period=3600
	tiramola auto_pilot minutes=1000
experiment2:
	#6 hours
	tiramola experiment target=8000 offset=6000 period=120 time=360
experiment_test:
	tiramola experiment target=80000 offset=6000 period=60 time=40

