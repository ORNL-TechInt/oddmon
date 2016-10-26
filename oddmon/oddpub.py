#!/usr/bin/env python
__version__ = "0.1"
"""
    A simple distributed monitoring tool with plugin support
    author: Feiyi Wang <fwang2@ornl.gov>

"""
import sys
import time
import random
import logging
import json
import socket
import plugins
import ConfigParser
import pika  # RabbitMQ client library
import ssl   # for encrypted connections to the RabbitMQ broker
import os

# Globals
logger  = None
ARGS    = None

class G:
    # These 2 are set by calling rmq_init
    connection_params = None
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

    G.connection_params = pika.ConnectionParameters(
        host=broker,
        port=port,
        virtual_host=virt_host,
        credentials = creds,
        ssl=use_ssl,
        ssl_options=ssl_opts)

def rmq_connect( parameters):
    '''
    Connect to the RMQ server using the specified connection parameters.
    
    Expects a pika.ConnectionParameters object and returns a
    pika.BlockingConnection object.
    '''
    
    # The RabbitMQ server can't handle a bunch of clients attempting to 
    # simultaneously open connections and this is very likely to happen
    # if one of the admins uses pdsh to start the clients on all the servers.
    # So, we have to be clever about connecting:
    # Connection attempts happen inside a loop. (And the loop will terminate
    # after a fixed amount of time if we haven't successfully connected.)
    # Inside the loop, we'll sleep for a random amount of time in order to
    # spread the load out a bit.
    max_time = time.time() + 120 # spend a max of 2 minutes attempting to connect
    connection = None
    while (connection is None and time.time() < max_time):
        try:
            # Wait a small amount of time before attempting to connect
            wait_time = random.random() * 1.0
            time.sleep(wait_time)
            connection = pika.BlockingConnection(parameters)
            is_connected = True
        except pika.exceptions.AMQPConnectionError, e:
            # if we get a timeout error, wait a little bit longer before
            # trying again
            if "timed out" in str(e):
                wait_time = 1.0 + (random.random() * 4.0)
                logger.warning( "Timeout error connecting to RMQ server.  " \
                                "Retrying in %fs."%wait_time)
                time.sleep(wait_time)
            else:
                # Re-throw the exception
                logger.exception("%s ** attempting to connect to RMQ server\n" % e)
                raise
    # Exited from the while loop.  Did we connect?
    if connection is None:
        logger.critical( "Failed to connect to the RMQ server.")
        raise RuntimeError( "Failed to connect to the RMQ server.")
        
    return connection

#def publish_wrapper( body, exchange='', routing_key=G.routing_key):
def publish_wrapper( body):
    '''
    A simple wrapper around the BlockingChannel.basic_publish function.
    
    Calls rmq_connect() to open a connection, uses the connection to get a
    channel, then uses the channel to call basic_publish.  Then closes down
    the channel and connection.
    
    Note: would probably work with any channel type's basic_publish() 
    function.  rmq_connect() returns a BlockingConnection which will yield a
    BlockingChannel, so that's all this function has been tested with.
    '''
    conn = rmq_connect( G.connection_params)
    ch = conn.channel()
    try:
        ch.basic_publish( exchange='', routing_key=G.routing_key, body=body)
    except Exception, e:
        logger.exception("%s exception trying to publish to RMQ. (Exception message: %s)\n" % (type(e), e))
        raise  # re-throw the exception
    
    conn.close()  # will automatically close the channel

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
    try:
        disabled_plugins = config.get( "global", "disabled_plugins").split(',')
        disabled_plugins = map( str.strip, disabled_plugins)
    except ConfigParser.NoOptionError:
        # This is no problem.  The disabled_plugins config is optional
        disabled_plugins = [ ]

    # This will throw an exception if it fails
    rmq_init(config)
    
    # initialize all metric modules
    plugins.scan(os.path.dirname(os.path.realpath(__file__))+"/metric_plugins", disabled_plugins)
    plugins.init( config_file, False)

    while True:
        merged = {}
        for name, mod in plugins.found():
            msg = None
            try:
                msg = mod.get_stats()
            except Exception as e:
                logger.exception("%s ---> %s\n" % (name, e))

            if msg: merged[name] = msg

        if len(merged) > 0:   
            # This check is really overkill, but we've been seeing
            # occasional cases where the subscriber receives a corrupt JSON
            # string from the RMQ server.  This check will ensure that the
            # data we're about to send is really valid, and alert us with a
            # separate message if it's not.  (The possibilty of the error
            # message itself getting corrupted is something I'm
            # deliberately ignoring...)
            json_text = json.dumps(merged)
            try:
                temp_decoded = json.loads(json_text)
            except ValueError, e: # thrown when loads() can't decode something
                logger.error("Detected bad JSON data in output buffer")
                
                err_data = { }
                err_data['host'] = socket.gethostname()
                err_data['summary_message'] = "Detected bad JSON data in output buffer"
                err_data['exception_message'] = str(e)
                # TODO: Any other data we should gather?
                
                # Send the data as a separate message
                publish_wrapper( body=json.dumps( {'client_msg':err_data}))
            finally:
                temp_decoded = None 
                # allow the garbage collector to reclaim what could be rather
                # a lot of memory
                
            logger.debug("publish: %s" % merged)          
            publish_wrapper( body=json_text)            
        else:
            logger.warn("Empty stats")

        # Sleep until it's time to take the next sample.
        #
        # We expect there will be multiple publishers running, and would
        # like them to all collect samples at the same time.  (Doing so
        # makes aggregating all the samples together much easier.)  If we
        # just called time.sleep(), the different processes would eventually
        # get out of sync.  Instead, we're going base everything on the
        # time.time() call.  (We're assuming that computers running the
        # publishers all have their clocks sync'd.)
        #
        # We want to wake up when time.time() % sleep_interval == 0
        # In an effort to both wake up on time and avoid calling sleep()
        # for such short periods that it basically turns into a spinlock,
        # we try to be a little clever about calculating a length of time
        # to sleep.
        wake_time = time.time()
        wake_time += sleep_interval - (wake_time % sleep_interval)
        while (time.time() < wake_time):
            sleep_time = (wake_time - time.time()) / 2
            if sleep_time < 0.05:
                sleep_time = 0.05  # don't try to sleep for less than 50
                                   # milliseconds - we don't need that kind
                                   # of precision
            time.sleep( sleep_time)
        
        

    logger.debug( "Exited from main loop.  Cleaning up plugins.")
    plugins.cleanup( False)
    logger.info( "About to exit.")

if __name__ == "__main__": main()

