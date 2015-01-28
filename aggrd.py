#!/usr/bin/env python

import sys
import signal
import logging
import argparse
import zmq
import ConfigParser
import time
from zmq.eventloop import ioloop, zmqstream

try:
    from oddmon import hostlist
except ImportError:
    import hostlist

# Globals
logger  = None
ARGS    = None


class G:
    subscribers = []
    config = None
    hosts = None

def parse_args():
    parser = argparse.ArgumentParser(description="MOND program")
    parser.add_argument("-v", "--verbose", default=False, action="store_true", help="verbose output")
    parser.add_argument("-r", "--refreshdb", default=False, action="store_true", help="Recreate database")

    myargs = parser.parse_args()
    return myargs


def sig_handler(signal, frame):

    print "\tUser cancelled ... cleaning up"
    sys.exit(0)


def db_init():
    pass

def save_msg(msg):
    logger.debug("Saving \n %s" % msg)

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
            stream_sub.on_recv(save_msg)
            G.subscribers.append(socket_sub)
            logger.debug("Connected to %s" % pub_endpoint)
        except:
            logger.error("Failed to connect: %s", pub_endpoint)
            sys.exit(1)


    # kick off event loop
    ioloop.IOLoop.instance().start()

def main():
    global logger, ARGS

    signal.signal(signal.SIGINT, sig_handler)
    logger = logging.getLogger("aggrd")
    ARGS = parse_args()
    if ARGS.verbose:
        logging.basicConfig(level=logging.DEBUG,
            format="%(asctime)s - %(name)s - %(levelname)s\t - %(message)s")
    else:
        logging.basicConfig(level=logging.INFO,
            format="%(name)s - %(message)s")

    G.config = ConfigParser.SafeConfigParser()
    G.config.read("oddmon.conf")
    G.hosts = hostlist.expand_hostlist(G.config.get("global", "pub_hosts"))
    pub_port = G.config.get("global", "pub_port")
    zmq_init(G.hosts, pub_port)

if __name__ == "__main__": main()
