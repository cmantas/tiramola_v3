__author__ = 'cmantas'
from time import sleep
from multiprocessing import Process


def func_sleep():
    print "sleeping"
    sleep(3)
    print "end sleeping"




# def __main__():

print "hello"

t = Process(target=func_sleep)
t.start()
t.join(1.0)
t.terminate()
print "thread joined alive: " + str(t.is_alive())