default:
	tiramola auto_pilot minutes=1001
	#doing nothing
sync:
	git commit -am "sync"; git push; ssh torchestrator "cd tiramola_v3; git pull"

pull_measurements:
	rsync -avz --delete torchestrator:/root/tiramola_v3/files/measurements/* files/measurements/	
push_measurements:
	rsync -avz --delete files/measurements/* torchestrator:/root/tiramola_v3/files/measurements 	
clean:
	tiramola kill_nodes
	tiramola kill_workload 
	tiramola bootstrap_cluster used=8
	tiramola load_data records=10000000
clean_quick:
	tiramola kill_nodes
	tiramola kill_workload 
	tiramola bootstrap_cluster used=8
	tiramola load_data records=10000
train:
	tiramola train

experiment1:
	tiramola experiment target=8000 offset=6000 period=60 time=180 name=experiment1
experiment2:
	#6 hours
	tiramola experiment target=8000 offset=6000 period=120 time=360 name=experiment2
experiment3:
	tiramola experiment target=6000 offset=4000 period=60 time=120 name=experiment3
