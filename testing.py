__author__ = 'cmantas'

import lib.connector_eucalyptus as iaas

ids = iaas.get_all_vm_ids()


test_image_id = "ami-0000000a"
test_flavor_id = "m1.small"
vm_id = iaas.create_vm("christos", test_flavor_id, test_image_id, "/dev/null")

print "vm created"
import time
time.sleep(40)

iaas.shutdown_vm(vm_id)
print "shut down"
time.sleep(30)
iaas.startup_vm(vm_id)
print "startup"
