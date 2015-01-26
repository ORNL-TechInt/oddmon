#!/usr/bin/env python

import sys
import signal
import logging
import argparse
import zmq
import hostlist
import ConfigParser

# Globals
logger  = None
ARGS    = None


class G:
    sockets = []

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

def zmq_init(hosts, port):
    context = zmq.Context()
    for host in hosts:
        socket = context.socket(zmq.SUB)
        pub_endpoint =  "tcp://%s:%s" % (host, port)
        logger.debug("Connecting to %s" % pub_endpoint)
        socket.connect(pub_endpoint)

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

    hosts = hostlist.expand_hostlist(G.config.get("global", "pub_hosts"))
    pub_port = G.config.get("global", "pub_port")
    zmq_init(hosts, pub_port)

if __name__ == "__main__": main()
