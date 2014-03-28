from VM import *
from lib.persistance_module import env_vars, get_script_text

server_name = "test_node"
flavor_id = 1;
image_id = env_vars['cassandra_base_image']

# for vm in get_all_vms():
#     script_text = get_script_text("test")
#     script_text += get_script_text("test")
#     print vm.run_command(script_text)

client_count = 2
record_count = 2000
step = record_count/client_count
start = 0
script_text = get_script_text("ycsb_load") %(str(record_count), str(step), str(start))
start += step
print script_text