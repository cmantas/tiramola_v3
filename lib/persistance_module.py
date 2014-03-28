__author__ = 'cmantas'

#!/usr/bin/python
# -*- coding: utf-8 -*-

import sqlite3 as lite
import sys, json
from datetime import datetime

ENV_VARS_FILE = 'files/env_vars.json'
OPENSTACK_NAMES_FILE = 'files/openstack_names.json'

db_file = "files/persistance.db"


#load the env vars from file
env_vars = json.loads(open(ENV_VARS_FILE, 'r').read())

#load the openstack names from file
openstack_names = json.loads(open(OPENSTACK_NAMES_FILE, 'r').read())


def executescript(script):
    try:
        con = lite.connect(db_file)
        cur = con.cursor()
        cur.executescript(script)
        con.commit()
    except lite.Error, e:
        if con: con.rollback()
        print "Error %s:" % e.args[0]
    finally:
        try:
            con
            con.close()
        except NameError:
            pass

# INIT the tables
#executescript("CREATE TABLE IF NOT EXISTS ROLES(VMID INTEGER PRIMARY KEY, Role TEXT)")


def execute_query(query):
    try:
        con = lite.connect(db_file)
        cur = con.cursor()
        cur.execute(query)
        rows = cur.fetchall()
        return rows
    except lite.Error, e:
        if con: con.rollback()
        print "Error %s:" % e.args[0]
        return None
    finally:
        if con: con.close()


def execute_lookup(query):
    for r in execute_query(query): return r


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


def get_script_text(name):
    filename = env_vars[name]
    file = open(filename, 'r')
    return file.read()+"\n"

