import sys
import logging.handlers as handlers
import logging
import shutil
import socket
import fileinput, paramiko,  datetime
from lib.persistance_module import env_vars
import xml.parsers.expat
#import CassandraCluster as cluster_manager
from os.path import isfile
from time import sleep

LOG_FILENAME = 'files/logs/Coordinator.log'

class GParser:

    def __init__(self):
        self.inhost =0
        self.inmetric = 0
        self.allmetrics = {}
        self.currhostname = ""

    def parse(self, ganglia_file):
        """
        parses an xml ganglia file
        :param ganglia_file:
        :return: a dictionary of all ganlia metrics and their values
        """
        p = xml.parsers.expat.ParserCreate()
        p.StartElementHandler = self.start_element
        p.EndElementHandler = self.end_element
        p.ParseFile(ganglia_file)

        if self.allmetrics == {}: raise Exception('Host/value not found')
        return self.allmetrics

    def start_element(self, name, attrs):

        # edo xtizo to diplo dictionary. vazo nodes kai gia kathe node vazo polla metrics.
        #print attrs
        if name == "HOST":
            #if attrs["NAME"]==self.host:
            self.allmetrics[attrs["NAME"]]={}
            # edo ftiaxno ena adeio tuple me key to onoma tou node kai value ena adeio dictionary object.
            self.inhost=1
            self.currhostname = attrs["NAME"]
            #print "molis mpika sto node me dns " , self.currhostname

        elif self.inhost==1 and name == "METRIC": # and attrs["NAME"]==self.metric:
            #print "attrname: " , attrs["NAME"] , " attr value: " , attrs["VAL"]
            self.allmetrics[self.currhostname][attrs["NAME"]] = attrs["VAL"]

    def end_element(self, name):
            if name == "HOST" and self.inhost==1:
                self.inhost = 0
                self.currhostname = ""


class MonitorVms:
    def __init__(self, cluster):
        """
        :param cluster: a dictionary of hostname-->IP
        :return:
        """
        self.cluster = cluster

        self.ganglia_host = cluster["cassandra_seednode"]
        self.ganglia_port = 8649

        ## Install logger

        self.my_logger = logging.getLogger('MonitorVms')
        self.my_logger.setLevel(logging.DEBUG)
        handler = handlers.RotatingFileHandler(LOG_FILENAME, maxBytes=2*1024*1024, backupCount=5)
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
        handler.setFormatter(formatter)
        self.my_logger.addHandler(handler)

        self.allmetrics={}
        self.parser = GParser()
        # initialize parser object. in the refreshMetrics function call the .parse of the
        # parser to update the dictionary object.
        print str(self.refreshMetrics())

    def refreshMetrics(self):
        """
        runs periodically and refreshes the metrics
        :return:
        """

        print "connetcting to %s %s" % (self.ganglia_host, self.ganglia_port)
        for res in socket.getaddrinfo(self.ganglia_host, self.ganglia_port, socket.AF_UNSPEC, socket.SOCK_STREAM):
            af, socktype, proto, canonname, sa = res
            try:
                self.soc = socket.socket(af, socktype, proto)
            except socket.error as msg:
                s = None
                continue
            try:
                self.soc.connect(sa)
            except socket.error as msg:
                self.soc.close()
                self.soc = None
                continue
            break
        if self.soc is None:
            print 'could not open socket'
            sys.exit(1)
        self.allmetrics = None
        f = self.soc.makefile("r")
        self.allmetrics = self.parser.parse(f)
        f.close()
        f = None
        self.soc.close()
        #self.my_logger.debug("REFRESHMETRICS allmetrics: "+str(self.allmetrics))
        return self.allmetrics





def usage():
    print """Usage: check_ganglia \
-h|--host= -m|--metric= -w|--warning= \
-c|--critical= [-s|--server=] [-p|--port=] """
    sys.exit(3)

if __name__ == "__main__":
##############################################################
#    ganglia_host = 'clusterhead'
#    ganglia_port = 8649
#    host = 'clusterhead'
#    metric = 'swap_free'
#    warning = None
#    critical = None


#    try:
#        options, args = getopt.getopt(sys.argv[1:],
#          "h:m:w:c:s:p:",
#          ["host=", "metric=", "warning=", "critical=", "server=", "port="],
#          )
#    except getopt.GetoptError, err:
#        print "check_gmond:", str(err)
#        usage()
#        sys.exit(3)
#
#    for o, a in options:
#        if o in ("-h", "--host"):
#            host = a
#        elif o in ("-m", "--metric"):
#            metric = a
#        elif o in ("-w", "--warning"):
#            warning = float(a)
#        elif o in ("-c", "--critical"):
#            critical = float(a)
#        elif o in ("-p", "--port"):
#            ganglia_port = int(a)
#        elif o in ("-s", "--server"):
#            ganglia_host = a
#
#    if critical == None or warning == None or metric == None or host == None:
#        usage()
#

    #monVms = MonitorVms(cluster_manager.get_hosts())
    monVms = MonitorVms({"cassandra_seednode": "83.212.121.246"})


    sleep(5)
    allmetrics=monVms.refreshMetrics()
    print "allmetrics length ", len(allmetrics)


#    try:
#        print "ganglia host " + ganglia_host
#        print 'host ' + host
#        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#        s.connect((ganglia_host,ganglia_port))
##        file = s.makefile("r")
##        print file.read()
#        parser = GParser(host, metric)
##        print "outside function" , s.makefile("r")
#        value = parser.parse(s.makefile("r"))
#
#        s.close()
#    except Exception, err:
#        print "CHECKGANGLIA UNKNOWN: Error while getting value \"%s\"" % (err)
#        sys.exit(3)
#
#    if value >= critical:
#        print "CHECKGANGLIA CRITICAL: %s is %.2f" % (metric, value)
#        sys.exit(2)
#    elif value >= warning:
#        print "CHECKGANGLIA WARNING: %s is %.2f" % (metric, value)
#        sys.exit(1)
#    else:
#        print "CHECKGANGLIA OK: %s is %.2f" % (metric, value)
#        sys.exit(0)