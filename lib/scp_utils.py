__author__ = 'cmantas'

#python ssh lib
import paramiko
import string
import sys
from socket import error as socketError
sys.path.append('lib/scp.py')
from lib.scp import SCPClient
from datetime import datetime, timedelta
from persistance_module import env_vars
from time import time

ssh_timeout = 10
ssh_giveup_timeout = env_vars['ssh_giveup_timeout']
priv_key_path = 'keys/just_a_key'
private_key = paramiko.RSAKey.from_private_key_file(priv_key_path)



def reindent(s, numSpaces, prefix=''):
    s = string.split(s, '\n')
    s = [(numSpaces * ' ') +prefix+ string.lstrip(line) for line in s]
    s = string.join(s, '\n')
    return s


def run_ssh_command(host, user, command, indent=1, prefix="$: ", logger=None):
    """
    runs a command via ssh to the specified host
    :param host:
    :param user:
    :param command:
    :return:
    """
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    if not logger is None:
        logger.debug("Connecting to SSH")
    timer = Timer.get_timer()
    ssh.connect(host, username=user, timeout=ssh_timeout, pkey=private_key, allow_agent=False, look_for_keys=False)
    if not logger is None:
        logger.debug("connected in %d sec. Running SSH command" % timer.stop())
    timer.start()
    ### EXECUTE THE COMMAND  ###
    stdin, stdout, stderr = ssh.exec_command(command)
    ret = ''
    for line in stdout:
        ret += line
    for line in stderr:
        ret += line
    # close the ssh connection
    ssh.close()
    if not logger is None:
        logger.debug("SSH command took %d sec" % timer.stop())
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
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, username=user, timeout=ssh_giveup_timeout, pkey=private_key)
    scpc=SCPClient(ssh.get_transport())
    scpc.put(files, remote_path, recursive)
    ssh.close()


def test_ssh(host, user, logger=None):
    end_time = datetime.now()+timedelta(seconds=ssh_giveup_timeout)
    try:
        rv = run_ssh_command(host, user, 'echo success', logger=logger)
        return True
    except socketError:
        return False
    # except:
    #     print "error in connecting ssh:", sys.exc_info()[0]
    return False


class Timer():
    """
    Helper class that gives the ablility to measure time between events
    """
    def __init__(self):
        self.started = False
        self.start_time = 0

    def start(self):
        assert self.started is False, " Timer already started"
        self.started = True
        self.start_time = int(round(time() * 1000))

    def stop(self):
        end_time = int(round(time() * 1000))
        assert self.started is True, " Timer had not been started"
        start_time = self.start_time
        self.start_time = 0
        self.started = False
        return float(end_time - start_time)/1000

    @staticmethod
    def get_timer():
        timer = Timer()
        timer.start()
        return timer