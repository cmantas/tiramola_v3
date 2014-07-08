__author__ = 'cmantas'

#!/usr/bin/python
# -*- coding: utf-8 -*-

import sqlite3 as lite
import sys, json
from datetime import datetime

ENV_VARS_FILE = 'files/env_vars.json'
OPENSTACK_NAMES_FILE = 'files/openstack_names.json'
SCRIPTS_FILE = 'files/scripts.json'

db_file = "files/persistance.db"

env_vars = {}


def reload_env_vars():
    global env_vars
    env_vars.update(json.loads(open(ENV_VARS_FILE, 'r').read()))


#load the env vars from file
env_vars = json.loads(open(ENV_VARS_FILE, 'r').read())

#load the openstack names from file
openstack_names = json.loads(open(OPENSTACK_NAMES_FILE, 'r').read())




def get_credentials(user):
    """
    retreives the authentication url and authentication  token for the given user
    :param user: the user name of for whom the credentials will be loaded
    :return: url, token
    """
    url = env_vars["auth_url"]
    token = env_vars[user+"_token"]
    return url, token


def store_openstack_name(vm_id, name):
    """
    adds the name to the dictionary and writes it to the output file
    :param vm_id:
    :param name:
    :return:
    """
    openstack_names[vm_id] = name
    with open(OPENSTACK_NAMES_FILE, 'w') as outfile:
        json.dump(openstack_names, outfile, indent=3)


def get_script_text(cluster, node_type, script_type):
    scripts = json.loads(open(SCRIPTS_FILE, 'r').read())
    try:
        filename = scripts[cluster+"_"+node_type+"_"+script_type]
        file = open(filename, 'r')
        return file.read()+"\n"
    except KeyError:
        return ""

