#!/usr/bin/env python
__version__ = "0.1"
"""
    A simple distributed monitoring tool with plugin support
    author: Feiyi Wang <fwang2@ornl.gov>

"""
import sys
import time
import logging
import json
import plugins
import pika
import ConfigParser

# Globals
logger  = None
ARGS    = None

class G:
    config = None
    channel = None
    parameters = None
    connection = None
    routing_key = None

def rmq_init(broker):
    G.parameters = pika.ConnectionParameters(host=broker)
    G.connection = pika.BlockingConnection(G.parameters)
    G.channel = G.connection.channel()

def sig_handler(signal, frame):
    print "\tUser cancelled ... cleaning up"
    plugins.cleanup()
    sys.exit(0)





def main( config_file):
    global logger, ARGS
    logger = logging.getLogger("app.%s" % __name__)

    config = ConfigParser.SafeConfigParser()
    try:
        config.read(config_file)
        broker = config.get("rabbitmq", "broker"))
        G.routing_key = config.get("rabbitmq", "routing_key")
        rmq_init(broker)
    except Exception, e:
        logger.error("Can't read configuration file")
        logger.error("Reason: %s" % e)
        sys.exit(1)

    # initialize all metric modules
    plugins.scan(".")
    plugins.init( config_file, False)

    while True:
        merged = {}
        for name, mod in plugins.found():
            msg = None
            try:
                msg = mod.get_stats()
            except Exception as e:
                logger.error("%s --->%s\n" % (name, e))

            if msg: merged[name] = msg

        if len(merged) > 0:
            logger.debug("publish: %s" % merged)
            G.channel.basic_publish(exchange='', routing_key=G.routing_key, body=(json.dumps(merged)))
        else:
            logger.warn("Empty stats")

        time.sleep(ARGS.interval)


    plugins.cleanup( False)

if __name__ == "__main__": main()

