#!/usr/bin/python
__author__ = 'cmantas'


import sys


assert len(sys.argv)>2, "too few args"

command = sys.argv[1]
params = sys.argv[2:]

if (command=="create"):
    print "create with params: " + str(params)


def create(params):
    if params[0]=="vm":
        assert len(params)