__author__ = 'cmantas'
from sys import stderr
from os.path import exists
from os import mkdir
from scp_utils import *
import ntpath
import thread
from lib.persistance_module import env_vars

#choose the IaaS provider
infrastructure = env_vars['iaas']
if infrastructure == 'okeanos':
    from lib import connector_okeanos as iaas
if infrastructure == 'openstack':
    from lib import connector_eucalyptus as iaas


LOGS_DIR = "files/VM_logs"
ATTEMPT_INTERVAL = 2


class VM:
    class Address:
        """
        Helper class that represents an IP address
        """
        def __init__(self, version, ip, in_type):
            self.version = version
            self.ip = ip
            self.type = in_type

        def __str__(self):
            rv = "%s IPv%d: %s" % (self.type, self.version, self.ip)
            return rv

    def __init__(self, name, flavor_id, image_id, create=False, wait=False, log_path=LOGS_DIR):
        """
        VM class constructor
        """
        #set attributes
        self.created = False
        self.name = name
        self.flavor_id = flavor_id
        self.log_path = log_path
        self.image_id = image_id
        self.public_addresses = []
        self.log_path = log_path
        self.addresses = []
        self.id = -1
        if create:
            self.create(wait)

    def load_addresses(self):
        """
        loads the IP interfaces from the IaaS
        :return:
        """
        addr_list = iaas.get_addreses(self.id)
        for a in addr_list:
            addr = self.Address(a['version'], a['ip'], a['type'])
            self.addresses.append(addr)

    def from_dict(self, in_dict):
        """
        creates a VM from dictionary containing 'name' and 'id' reccords
        """
        self.name = in_dict['name']
        self.id = in_dict['id']

    def create(self, wait):
        print ("VM: creating '"+self.name+"'"),
        if wait:
            print "(sync)"
            self.create_sync()
            self.wait_ready()
        else:
            print "(async)"
            thread.start_new_thread(self.create_sync, ())

    def create_sync(self):
        """
        Creates this VM in the underlying IaaS provider
        """
        #start the timer
        timer = Timer()
        timer.start()
        self.id = iaas.create_vm(self.name, self.flavor_id, self.image_id, LOGS_DIR+"/%s.log" % self.name)
        new_status = iaas.get_vm_status(self.id)
        delta = timer.stop()
        print 'VM: IaaS status for "%s" is now %s (took %d sec)' % (self.name, new_status, delta )
        self.created = True
        self.load_addresses()

    def shutdown(self):
        """
        Issues the 'shutdown' command to the IaaS provider
        """
        print 'VM: Shutting down "%s" (id: %d)' % (self.name, self.id)
        return iaas.shutdown_vm(self.id)

    def startup(self):
        """
        boots up an existing VM instance in okeanos
        :return: true if VM exist false if not
        """
        if not self.created: return False;
        print 'VM: starting up "%s" (id: %d)' % (self.name, self.id)
        return iaas.startup_vm(self.id)

    def destroy(self):
        """Issues the 'destory' command to the IaaS provider  """
        print "VM: Destroying %s" % self.name
        iaas.destroy_vm(self.id)

    def __str__(self):
            text = ''
            text += '========== VM '+self.name+" ===========\n"
            text += "ID: "+str(self.id)+'\n'
            text += 'host: %s\n' % self.get_host()
            text += "Addresses (%s):" % len(self.addresses)
            for a in self.addresses:
                text += " [" + str(a) + "],"
            text += "\nCloud Status: %s\n" % self.get_cloud_status()
            return text

    @staticmethod
    def vm_from_dict(in_dict):
        """
        creates a VM instance from a synnefo "server" dict
        :param in_dict: "server" or "server details" dictionary from synnefo
        :return: a VM instance for an existing vm
        """
        vm_id, name, flavor_id, image_id = in_dict['id'], in_dict['name'], in_dict['flavor_id'], in_dict['image_id']
        rv = VM(name, flavor_id, image_id)
        rv.created = True
        rv.id = vm_id
        rv.load_addresses()
        return rv

    @staticmethod
    def from_id(vm_id):
        """ creates a VM instance from the VM id """
        vm_dict = iaas.get_vm_details(vm_id)
        return VM.vm_from_dict(vm_dict)


    def get_cloud_status(self):
        return iaas.get_vm_status(self.id)

    def run_command(self, command, user='root', indent=0, prefix="\t$:  ", silent=False):
        """
        runs a command to this VM if it actually exists
        :param command:
        :param user:
        :return:
        """
        if not self.created:
            stderr.write('this VM does not exist (yet),'
                         ' so you cannot run commands on it')
            return "ERROR"
        if not silent:
            print "VM: [%s] running SSH command \"%s\"" % (self.name, command)
        return run_ssh_command(self.get_public_addr(), user, command, indent, prefix)

    def put_files(self, files, user='root', remote_path='.', recursive=False):
        """
        Puts a file or a list of files to this VM
        """
        put_file_scp(self.get_host(), user, files, remote_path, recursive)

    def run_files(self, files):
        """
        puts a file in the VM and then runs it
        :param files:
        :return:
        """
        self.put_files(files)

        filename = ''
        remote_path = ''
        if not isinstance(files, (list, tuple)):
            head, tail = ntpath.split(files)
            filename = tail or ntpath.basename(head)
            remote_path = "~/scripts/" + filename
        else:
            for f in files:
                head, tail = ntpath.split(f)
                short_fname = (tail or ntpath.basename(head))
                filename += short_fname + ' '
                remote_path += "~/scripts/"+short_fname+"; "
        #generate the command that runs the desired scripts
        command = 'chmod +x %s; ' \
                  'mkdir -p scripts;' \
                  'mv %s ~/scripts/ 2>/dev/null;' \
                  '%s'\
                  % (filename, filename, remote_path)
        return self.run_command(command)

    def wait_ready(self):
        """
        Waits until it is able to run SSH commands on the VM or a timeout is reached
        """
        success = False
        attempts = 0
        if not self.created:
            while not self.created:  sleep(3)
        print "VM: [%s] waiting for SSH deamon (addr: %s)" % (self.name, self.get_public_addr())
        #time to stop trying
        end_time = datetime.now()+timedelta(seconds=ssh_giveup_timeout)
        timer = Timer()
        timer.start()
        #print("VM: Trying ssh, attempt "),
        while not success:
            #if(attempts%5 == 0): print ("%d" % attempts),
            attempts += 1
            if test_ssh(self.get_public_addr(), 'root'):
                success = True
            else:
                if datetime.now() > end_time:
                    break
                sleep(ATTEMPT_INTERVAL)
        if success: print ("VM: %s now ready" % self.name),
        else: print("VM: %s FAIL to be SSH-able" % self.name),
        print ("  (took " + str(timer.stop())+" sec)")
        return success

    def get_public_addr(self):
        """ Returns a publicly accessible IP address !!! for now, only checks for IPv6+fixed !!!"""
        if len(self.addresses) == 0:
            self.load_addresses()
        for i in self.addresses:
            if i.type == "fixed" and i.version == 6:
                return i.ip
        return None

    def get_private_addr(self):
        #find fixed ip
        for i in self.addresses:
            if i.version == 4 and i.type == "fixed":
                return i.ip

    def inject_hostnames(self, hostnames):
        #add some default hostnames
        hostnames["localhost"] = "127.0.0.1"
        hostnames["ip6-localhost ip6-loopback"] = "::1"
        hostnames["ip6-localnet"] = "fe00::0"
        hostnames["ip6-mcastprefix"] = "ff00::0"
        hostnames["ip6-allnodes"] = "ff02::1"
        hostnames["ip6-allrouters"] = "ff02::2"
        text=""
        for host in hostnames.keys():
            text += "\n%s %s" % (hostnames[host], host)
        self.run_command("echo '## AUTO GENERATED #### \n%s' > /etc/hosts; echo %s >/etc/hostname" % (text, self.name), silent=True)


def get_all_vms(check_active=False):
    """
    Creates VM instances for all the VMs of the user available in the IaaS
    """
    vms = []
    vm_ids = iaas.get_all_vm_ids()
    for vm_id in vm_ids:
        vm = VM.vm_from_dict(iaas.get_vm_details(vm_id))
        if check_active and vm.get_cloud_status() != "ACTIVE":
            continue
        else:
            vms.append(vm)
    return vms


if not exists(LOGS_DIR):
    mkdir(LOGS_DIR)


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
        return float(end_time - start_time)/1000

    @staticmethod
    def get_timer():
        timer = Timer()
        timer.start()
        return timer