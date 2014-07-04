#!/bin/sh
killall java

echo '

############  KILLED  ##############' >> ycsb_run.log
#report not alive
gmetric -n alive -v 0 -t int32 -u nodes -d 10000