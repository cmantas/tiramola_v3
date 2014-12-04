__author__ = 'cmantas'

from lib.persistance_module import env_vars
from lib.scp_utils import *

env_vars['iaas'] = "openstack"
#env_vars['priv_key_path'] = "/home/cmantas/.ssh/website"

from VM import VM, get_all_vms


for vm in get_all_vms(check_active=True):
    print str(vm)
