__author__ = 'cmantas'

from lib.persistance_module import env_vars

env_vars['iaas'] = "openstack"

from VM import VM, get_all_vms


for vm in get_all_vms(check_active=True):
    print str(vm)