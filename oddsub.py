#!/usr/bin/env python

import sys
import signal
import logging
import argparse
import zmq
import ConfigParser
import time
from zmq.eventloop import ioloop, zmqstream
import json
import ast

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


def db_init():
    pass

def save_msg(msg):

    blob = json.loads(msg[0])
    for metric, stats in blob.iteritems():
        metric = str(metric)
        stats = ast.literal_eval(str(stats))
        for target, val in stats.iteritems():
            print target



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

def main(G):
    global logger, ARGS

    logger = logging.getLogger("main.%s" % __name__)

    zmq_init(G.hosts, ARGS.port)

    # we kick off the event loop with zmq_init()
    # after that, all we have to do is sit tight

if __name__ == "__main__": main()
