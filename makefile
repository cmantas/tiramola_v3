default:
	#doing nothing
sync:
	rsync -av * torchestrator:~/bin/tiramola
experiment1:
	tiramola load_data records=10000000
	run_sinusoid target=1000 offset=8000 period=7200
	tiramola auto_pilot
