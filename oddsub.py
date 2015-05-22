#!/usr/bin/env python

import sys
import logging
import zmq
from zmq.eventloop import ioloop, zmqstream
import json
import ast
import sql
import splunk_utils

ARGS    = None
logger  = None

class G:
    subscribers = []

def save_msg(msg):

    blob = json.loads(msg[0])
    for metric, stats in blob.iteritems():
        stats = ast.literal_eval(str(stats))
        if len(stats) > 0:
            sql.insert_row(metric, stats)
        else:
            logger.debug("[%s] reports empty stats" % metric)

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
            #stream_sub.on_recv(save_msg)
            stream_sub.on_recv(splunk_utils.push_to_splunk)
            G.subscribers.append(socket_sub)
            logger.debug("Connected to %s" % pub_endpoint)
        except:
            logger.error("Failed to connect: %s", pub_endpoint)
            sys.exit(1)


    # kick off event loop
    ioloop.IOLoop.instance().start()
    

def main(hosts, port, url, username, password, splunk_port, splunk_host):
    global logger
    logger = logging.getLogger("app.%s" % __name__)
    sql.db_init(url)
    splunk_utils.connect_to_splunk(username, password, splunk_port, splunk_host)
    zmq_init(hosts, port)

    # we kick off the event loop with zmq_init()
    # after that, all we have to do is sit tight

if __name__ == "__main__": main()
