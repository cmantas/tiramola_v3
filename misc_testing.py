__author__ = 'cmantas'
from time import sleep

from os import listdir, mkdir
from os.path import isfile, join, exists
from shutil import move





def my_print(c):
    print "myprint"

dir_path = "experiments"
print list_files(dir_path)

print watch(dir_path, my_print)
print "done"



