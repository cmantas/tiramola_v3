#!/bin/sh

ctool be_seed
ctool full_start
service gmetad restart

#report alive
gmetric -n alive -v 1 -t int32 -u nodes -d 10000