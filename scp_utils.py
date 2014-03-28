__author__ = 'cmantas'

#python ssh lib
import paramiko
import string
import sys
from socket import error as socketError
sys.path.append('lib/scp.py')
from lib.scp import SCPClient
from datetime import datetime, timedelta
from time import sleep, time

ssh_timeout = 10
ssh_giveup_timeout = 600

priv_key_path = 'keys/just_a_key'

ssh = paramiko.SSHClient()
private_key = paramiko.RSAKey.from_private_key_file(priv_key_path)
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())


def reindent(s, numSpaces, prefix=''):
    s = string.split(s, '\n')
    s = [(numSpaces * ' ') +prefix+ string.lstrip(line) for line in s]
    s = string.join(s, '\n')
    return s


def run_ssh_command(host, user, command, indent=1, prefix="$: "):
    """
    runs a command via ssh to the specified host
    :param host:
    :param user:
    :param command:
    :return:
    """
    ssh.connect(host, username=user, timeout=ssh_timeout, pkey=private_key)
    #print 'connected  to %s' % host
    stdin, stdout, stderr = ssh.exec_command(command)
    ret = ''
    for line in stdout:
        ret += line
    for line in stderr:
        ret += line
    return reindent(ret, indent, prefix=prefix)


def put_file_scp (host, user, files, remote_path='.', recursive=False):
    """
    puts the specified file to the specified host
    :param host:
    :param user:
    :param files:
    :param remote_path:
    :param recursive:
    :return:
    """
    ssh.connect(host, username=user, timeout=ssh_giveup_timeout, pkey=private_key)
    scpc=SCPClient(ssh.get_transport())
    scpc.put(files, remote_path, recursive)


def test_ssh(host, user):
    end_time = datetime.now()+timedelta(seconds=ssh_giveup_timeout)
    try:
        rv = run_ssh_command(host, user, 'echo success')
        return True
    except socketError:
        return False
    except:
        print "error in connecting ssh:", sys.exc_info()[0]
    return False
