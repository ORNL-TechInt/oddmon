#!/usr/bin/env python
__version__ = "0.1"
"""
    A simple distributed monitoring tool with plugin support
    author: Feiyi Wang <fwang2@ornl.gov>
    
    A note about our use of the multiprocessing package:
    
    This program uses the multiprocessing library to launch a separate
    process to handle all the Pika calls (connect, publish, disconnect).
    Normally, this would be considered overkill, but we've been seeing odd
    errors where Pika's connection.close() method hangs.  Basic debugging
    shows that Pika is waiting for a confirmation message from the server
    before closing the TCP socket.  That said, there's some further evidence
    that the actual problem occurred earlier in the basic_publish() function.
    Regardless, since we're using a blocking connection, any sort of hang
    pretty much locks up the whole process.
    
    Our solution is to put all the Pika calls into a separate subprocess.  If
    the subprocess hangs, the main process can just terminate it.  That may
    leave a bit of a mess on the RMQ server, but since the problem appears to
    be coming from the server in the first place, I don't feel particularly
    guilty about that.
    
    Lest anyone forgets: the reason we're opening and closing separate
    connections for each message is that we were having problems with long
    duration connections: Occasionaly, we would see cases where the socket
    got reset (again, from the server end).  It's possible this is related
    to how the Pika BlockingConnection class handles heartbeat timeouts,
    but that's still unclear.
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
import multiprocessing


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

def rmq_connect():
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
            connection = pika.BlockingConnection( G.connection_params)
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


def publish_subprocess( body, success_event):
    '''
    A simple wrapper around the channel.basic_publish function.
    
    Calls rmq_connect() to open a connection, uses the connection to get a
    channel, then uses the channel to call basic_publish.  Then closes down
    the channel and connection.
    '''
    global logger
    logger = logging.getLogger( logger.name + '.subproc')
    # using getChild() would be easier, but we need a newer version of the
    # logging library for that...
    
    logger.debug( "Inside subprocess")
        
    conn = rmq_connect()
    ch = conn.channel()
    ch.confirm_delivery() # set delivery confirmation mode on for the channel
    # NOTE: This is important! Without delivery confirmation, basic_publish()
    # returns before the send actually finishes (despite the fact that it's
    # supposed to be a BLOCKING channel).
    
    try:   
        # --------------------------------------------------------------------
        # This check is really overkill, but we've been seeing
        # occasional cases where the subscriber receives a corrupt JSON
        # string from the RMQ server.  This check will ensure that the
        # data we're about to send is really valid, and alert us with a
        # separate message if it's not.  (The possibilty of the error
        # message itself getting corrupted is something I'm
        # deliberately ignoring...)
        try:
            temp_decoded = json.loads( body)
        except ValueError, e: # thrown when loads() can't decode something
            logger.error("Detected bad JSON data in output buffer")
            
            err_data = { }
            err_data['host'] = socket.gethostname()
            err_data['summary_message'] = "Detected bad JSON data in output buffer"
            err_data['exception_message'] = str(e)
            # TODO: Any other data we should gather?
            
            # Send the data as a separate message
            ch.basic_publish( exchange='', routing_key=G.routing_key,
                              body=json.dumps( {'client_msg':err_data}))
        
        # Normally, I'd set temp_decoded to None so that python could reclaim
        # the memory.  Since this function is executing in a short-lived
        # process, though, I think it's more efficient to just let the process
        # end and let the OS reclaim all the memory at once.
        # --------------------------------------------------------------------
        
        logger.debug("Calling basic_publish()")
        start_time = time.time()    
        while not success_event.is_set():
            if ch.basic_publish( exchange='', routing_key=G.routing_key,
                                 body=body, mandatory=True):
                # NOTE: In the 0.9.x version (that we're using in production),
                # basic_publish() always seems to return True. I have no idea
                # what would cause it to return False.  (Possibly a failure
                # related to the mandatory or immediate flags would.)
                
                 # let the main process know we've managed to send the message
                success_event.set()
            # NOTE: If we upgrade to a newer version of pika (the 0.10.x
            # series, I think), we can also test for None, which gets set if 
            # delivery confirmation is not enabled.
            #elif success is None:  # basic_publish() returned None
            #    logger.warning( "Delivery confirmation disabled.  Assuming successful publish.")
            #    success_event.set()
            else:  # basic_publish() returned False
                logger.error( "basic_publish() failed.  Retrying...")           
                
        logger.debug("basic_publish() complete. Elapsed time: %0.3es"%(time.time() - start_time))
        
    # NOTE: If we upgrade to a newer version of Pika (the 0.10.x series),
    # we can use BlockingChannel.publish() and trap these 2 new exceptions...
    # except pika.exceptions.UnroutableError, e:
    #     logger.exception("UnroutableError trying to publish to RMQ. (Exception message: %s)\n" % e)
    # except pika.exceptions.NackError, e:
    #     logger.exception("NackError trying to publish to RMQ. (Exception message: %s)\n" % e)
    except pika.exceptions.AMQPChannelError, e:
        logger.exception("AMQPChannelError trying to publish to RMQ. (Exception message: %s)\n" % e)
    except Exception, e:
        logger.exception("%s exception trying to publish to RMQ. (Exception message: %s)\n" % (type(e), e))
        # No need to re-throw the exception since the sub-process is going to end anyway
    
    conn.close()  # will automatically close the channel
    logger.debug( "Connection closed.  Subprocess exiting.")


def publish_wrapper( body):
    '''
    A simple wrapper around the multiprocessing and Pika publishing code.
    
    Launches a sub-process that will open the RMQ connection, publish a 
    message and close the connection.  If it appears the sub-process has
    hung, will forcibly terminate it.
    '''  
    
    logger.debug( "Launching Sub-process")
    
    # Add a small, random delay so that multiple publishers (they'll be almost
    # 300 running in production) don't all hammer the RMQ servers at the same
    # time.
    time.sleep( random.random() * 10.0) # up to 10 seconds
    
    # Use an event to allow the sub process to signal success to us
    success_evt = multiprocessing.Event()
    success_evt.clear()
    while not success_evt.is_set():
        p = multiprocessing.Process( name = "oddpub_subproc",
                                    target = publish_subprocess,
                                    args = (body, success_evt))
        
        start_time = time.time()
        p.start()
        
        success_evt.wait( 30) # wait up to 30 seconds for the sub-process to
                              # open the connection and send the data
        if not success_evt.is_set():
            logger.error( "Timed out waiting for successful send. Terminating the sub-process.")
            p.terminate()
        else:
            # give it another 30 seconds to close the connection and exit
            # the process
            p.join( 30) 
            if p.is_alive():
                logger.warning("Terminating stuck publishing sub-process.")
                p.terminate()
                # Note that the sub-process has already set the success event
                # in this case, so we don't need to re-start the process.
            else:
                end_time = time.time()
                logger.debug( "Sub-process complete. Elapsed time: %0.3es"%(end_time - start_time))
                
        if not success_evt.is_set():
            logger.warning( "Re-starting the sub-process.")


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
            json_text = json.dumps(merged)
            logger.debug("publish: %s" % merged)
            publish_wrapper( body=json_text)
        else: # len(merged) was 0
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
        logger.debug( "Next wake time: %d"%wake_time)
        while (time.time() < wake_time):
            sleep_time = (wake_time - time.time()) / 2
            if sleep_time < 0.05:
                sleep_time = 0.05  # don't try to sleep for less than 50
                                   # milliseconds - we don't need that kind
                                   # of precision
            time.sleep( sleep_time)
        logger.debug( "Actual wake time: %d"%int(time.time()))
        
        

    logger.debug( "Exited from main loop.  Cleaning up plugins.")
    plugins.cleanup( False)
    logger.info( "About to exit.")

if __name__ == "__main__": main()

