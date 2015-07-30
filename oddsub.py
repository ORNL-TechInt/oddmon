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
import metric_ost_job_stats
import pika

ARGS    = None
logger  = None

class G:
    subscribers = []
    channel = None
    parameters = None
    connection = None
    queue = None

def save_msg(msg):
    blob = json.loads(msg[0])
    for metric, stats in blob.iteritems():
        stats = ast.literal_eval(str(stats))
        if len(stats) > 0:
            sql.insert_row(metric, stats)
        else:
            logger.debug("[%s] reports empty stats" % metric)
            
def handle_incoming( msg):
    #msg is a list (with just one element) of JSON-encoded strings   
    blob = json.loads(msg)
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

def on_connected(connection):
    """Called when we are fully connected to RabbitMQ"""
    # Open a channel
    connection.channel(on_channel_open)

def on_channel_open(new_channel):
    """Called when our channel has opened"""
    global channel
    channel = new_channel
    channel.queue_declare(queue="oddmon", durable=True, exclusive=False, auto_delete=False, callback=on_queue_declared)

def on_queue_declared(frame):
    """Called when RabbitMQ has told us our Queue has been declared, frame is the response from RabbitMQ"""
    channel.basic_consume(handle_delivery, queue=G.queue)

def handle_delivery(channel, method, header, body):
    """Called when we receive a message from RabbitMQ"""
    print type(body)
    handle_incoming(body)
    channel.basic_ack(delivery_tag = method.delivery_tag)

def zmq_init(hosts, port, username, password):
    """
    Setup async call back on receiving
    """

    parameters = pika.ConnectionParameters(credentials=pika.PlainCredentials(username, password), host="localhost")
    connection = pika.SelectConnection(parameters, on_connected)

    try:
        connection.ioloop.start()
    except KeyboardInterrupt:
        connection.close()
        connection.ioloop.start()

def main(config_file, hosts, port, url, username, password, queue):
    global logger
    logger = logging.getLogger("app.%s" % __name__)
    sql.db_init(url)

    G.queue = queue

    # fiand and initialize all plugin modules
    plugins.scan(".")
    plugins.init( config_file, True)
    
    zmq_init(hosts, port, username, password)

    # we kick off the event loop with zmq_init()
    # after that, all we have to do is sit tight
    
    #TODO: Intercept Ctrl-C and run plugins.cleanup( True)

if __name__ == "__main__": main()
