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
import ConfigParser
import pika  # RabbitMQ client library
import ssl   # for encrypted connections to the RabbitMQ broker
import os

# Globals
logger  = None
ARGS    = None

class G:
    config = None
    channel = None
    connection = None
    routing_key = None


def rmq_init(config):
    '''
    Connect to the rabbitmq broker.
    
    config is a ConfigParser object that has already been set up. (That is,
    config.read() has been successfully called.)
    '''   
    try:
        broker = config.get("rabbitmq", "broker")
        username = config.get("rabbitmq", "username")
        password = config.get("rabbitmq", "password")
        port = config.getint("rabbitmq", "port")
        virt_host = config.get("rabbitmq", "virt_host")
        use_ssl = config.getboolean("rabbitmq", "use_ssl")
        
        G.routing_key = config.get("rabbitmq", "routing_key")
    except Exception, e:
        logger.critical('Failed to parse the "rabbitmq" section of the config file.')
        logger.critical('Reason: %s' % e)
        sys.exit(1)
    
    if use_ssl:
    # ToDo: These ssl settings are specific to rmq1.ccs.ornl.gov
    # I don't know if they're correct for other brokers
        ssl_opts=({"ca_certs"   : "/etc/pki/ca-trust/extracted/pem/tls-ca-bundle.pem",
                   "cert_reqs"  : ssl.CERT_REQUIRED,
                   "server_side": False})
    else:
        ssl_opts = None
    
    creds = pika.PlainCredentials( username, password)

    parameters = pika.ConnectionParameters(
        host=broker,
        port=port,
        virtual_host=virt_host,
        credentials = creds,
        ssl=use_ssl,
        ssl_options=ssl_opts)
    G.connection = pika.BlockingConnection(parameters)
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
    except Exception, e:
        logger.critical("Can't read configuration file")
        logger.critical("Reason: %s" % e)
        sys.exit(1)

    try:
        sleep_interval = config.getint("global", "interval")
    except Exception, e:
        logger.critical('Failed to parse the "global" section of the ' \
                        'config file.')
        logger.critical('Reason: %s' % e)
        sys.exit(1)


    # This will throw an exception if it fails to connect
    rmq_init(config)

    # initialize all metric modules
    plugins.scan(os.path.dirname(os.path.realpath(__file__))+"/metric_plugins")
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
            G.channel.basic_publish(exchange='', routing_key=G.routing_key,
                                    body=(json.dumps(merged)))
        else:
            logger.warn("Empty stats")

        time.sleep(sleep_interval)


    plugins.cleanup( False)

if __name__ == "__main__": main()

