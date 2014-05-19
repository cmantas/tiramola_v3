from kamaki.clients import ClientError
from kamaki.clients.astakos import AstakosClient
from kamaki.clients.astakos import getLogger
from kamaki.clients.cyclades import CycladesClient, CycladesNetworkClient
#http://www.synnefo.org/docs/kamaki/latest/developers/code.html#the-client-api-ref
from sys import stderr
from os.path import abspath
from base64 import b64encode
from lib.persistance_module import *
from logging import ERROR
from Node import Node

from lib.persistance_module import env_vars, get_script_text

from VM import *

t = Timer.get_timer()
vms = get_all_vms()
print t.stop()

t = Timer.get_timer()
vms = get_all_vms(True)
print t.stop()

