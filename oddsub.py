#!/usr/bin/env python

import sys
import logging
import zmq
from zmq.eventloop import ioloop, zmqstream
import json
import ast
import sql
import write_utils
import plugins
import ConfigParser
import hostlist

ARGS    = None
logger  = None

class G:
    subscribers = []

def save_msg(msg):
    print "hi"
    blob = json.loads(msg[0])
    for metric, stats in blob.iteritems():
        stats = ast.literal_eval(str(stats))
        if len(stats) > 0:
            sql.insert_row(metric, stats)
        else:
            logger.debug("[%s] reports empty stats" % metric)
            
def handle_incoming( msg):
    #msg is a list (with just one element) of JSON-encoded strings   
    blob = json.loads(msg[0])
    print "-----------------------------"
    print "blob type: %s"%type(blob)
    print "blob keys: %s"%blob.keys()
    print "============================="
    
    
    for name, mod in plugins.found():
        uname = unicode(name)
        if blob.has_key( uname):
            print "Matched %s - about to call save_stats()"%name
            mod.save_stats(blob[uname])

    # TODO: ought to check that there were no unhandled items in msg...

def zmq_init(hosts, port):
    """
    Setup async call back on receiving
    """
    context = zmq.Context()
    for host in hosts:
        socket_sub = context.socket(zmq.SUB)
        socket_sub.setsockopt(zmq.SUBSCRIBE, "")
        pub_endpoint =  "tcp://%s:%s" % (host, port)
        try:
            socket_sub.connect(pub_endpoint)
            stream_sub = zmqstream.ZMQStream(socket_sub)
            stream_sub.on_recv( handle_incoming)
            G.subscribers.append(socket_sub)
            logger.debug("Connected to %s" % pub_endpoint)
        except:
            logger.error("Failed to connect: %s", pub_endpoint)
            sys.exit(1)


    # kick off event loop
    ioloop.IOLoop.instance().start()
    

def main(config_file):
    global logger
    logger = logging.getLogger("app.%s" % __name__)
    
    config = ConfigParser.SafeConfigParser()
    try:
        config.read(config_file)
        hosts = hostlist.expand_hostlist(config.get("global", "pub_hosts"))
        port = int(config.get("global", "pub_port"))
        url = config.get("DB", "url")
        logger.debug( "Hosts: %s" % hosts)
        logger.debug( "Port: %d" % port)
    except Exception, e:
        logger.error("Can't read configuration file")
        logger.error("Reason: %s" % e)
        sys.exit(1)
    
    sql.db_init(url)
    
    # fiand and initialize all plugin modules
    plugins.scan(".")
    plugins.init( config_file, True)
    
    zmq_init(hosts, port)

    # we kick off the event loop with zmq_init()
    # after that, all we have to do is sit tight
    
    #TODO: Intercept Ctrl-C and run plugins.cleanup( True)

if __name__ == "__main__": main()
