#!/usr/bin/env python
"""
    A simple distributed monitoring tool with plugin support

    author: Feiyi Wang <fwang2@ornl.gov>

"""
import sys
import os.path
import signal
import time
import logging
import ConfigParser
import argparse
import zmq
import glob
import imp

# Globals
logger  = None
ARGS    = None

class G:

    context = None
    socket = None
    config = None
    plugins = {}
    callbacks = ['metric_init', 'get_stats', 'metric_cleanup']




def parse_args():
    parser = argparse.ArgumentParser(description="MOND program")
    parser.add_argument("-v", "--verbose", default=False, action="store_true", help="verbose output")
    myargs = parser.parse_args()
    return myargs

def zmq_init(pub):
    pub = "tcp://*:" + pub
    logger.debug("Bind to %s" % pub)
    G.context = zmq.Context()
    G.socket = G.context.socket(zmq.PUB)
    G.socket.bind(pub)

def sig_handler(signal, frame):

    print "\tUser cancelled ... cleaning up"
    plugin_cleanup()
    sys.exit(0)


def plugin_scan(pathname):

    pathname = os.path.realpath(pathname) + "/*.py"
    logger.debug("Plugin path: %s" % pathname)
    sources = glob.glob(pathname)

    for s in sources:
        name = os.path.basename(s).split(".")[0]
        mod = imp.load_source(name, s)
        if set(G.callbacks).issubset(set(dir(mod))):
            G.plugins[name] = mod
            logger.info("Registering plugin: %s" % name)
        else:
            logger.warn("Skipping %s" % name)

def plugin_init():
    for name, mod in G.plugins.iteritems():
        mod.metric_init(name)

def plugin_cleanup():
    for name, mod in G.plugins.iteritems():
        mod.metric_cleanup()


def main():
    global logger, ARGS

    signal.signal(signal.SIGINT, sig_handler)

    logger = logging.getLogger("mond")

    ARGS = parse_args()
    if ARGS.verbose:
        logging.basicConfig(level=logging.DEBUG,
            format="%(asctime)s - %(name)s - %(levelname)s\t - %(message)s")
    else:
        logging.basicConfig(level=logging.INFO,
            format="%(name)s - %(message)s")


    G.config = ConfigParser.SafeConfigParser()
    G.config.read("oddmon.conf")
    interval = G.config.getint("global", "interval")
    zmq_init( G.config.get("global", "pub_port") )

    # initialize all metric modules

    plugin_scan("./plugins")
    plugin_init()

    while True:
        for name, mod in G.plugins.iteritems():
            msg = mod.get_stats()
            logger.debug("%s -> %s" % (name, msg))
            G.socket.send_string(msg)

        time.sleep(interval)

    plugin_cleanup()

if __name__ == "__main__": main()

