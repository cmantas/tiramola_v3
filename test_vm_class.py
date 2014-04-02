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

server_name = "test_node"
flavor_id = 1;
image_id = env_vars['cassandra_base_image']




node = Node("testing", "test", 0, create=True, wait=True, IPv4=True)

print node