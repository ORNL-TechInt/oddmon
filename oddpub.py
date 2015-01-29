#!/usr/bin/env python
__version__ = "0.1"
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
import json

# Globals
logger  = None
ARGS    = None

class G:

    context = None
    publisher = None
    config = None
    plugins = {}
    callbacks = ['metric_init', 'get_stats', 'metric_cleanup']

def zmq_init(port=8888):
    pub = "tcp://*:%s" % port
    G.context = zmq.Context()
    G.publisher = G.context.socket(zmq.PUB)
    # prevent publisher overflow from slow subscribers
    if hasattr(zmq, "HWM"):
        G.publisher.setsockopt(zmq.HWM, 1)
    elif hasattr(zmq, "SNDHWM"):
        G.publisher.setsockopt(zmq.SNDHWM, 1)
    else:
        logger.warn("Can't set High Water Mark option")

    if hasattr(zmq, "SWAP"):
        G.publisher.setsockopt(zmq.SWAP, 2500000)
    else:
        logger.warn("Can't set SWAP option")

    G.publisher.bind(pub)
    logger.debug("Bind to %s" % pub)

def sig_handler(signal, frame):

    print "\tUser cancelled ... cleaning up"
    plugin_cleanup()
    sys.exit(0)


def plugin_scan(pathname):

    pathname = os.path.realpath(pathname) + "/metric*.py"
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
    logger = logging.getLogger("main.%s" % __name__)

    zmq_init()

    # initialize all metric modules

    plugin_scan(".")
    plugin_init()

    while True:
        merged = {}
        for name, mod in G.plugins.iteritems():
            try:
                msg = mod.get_stats()
            except Exception as e:
                logger.error("%s --->\n" % (name, e))
            merged[name] = msg

        if len(merged) > 0:
            logger.debug("%s" % merged)
            G.publisher.send_string(json.dumps(merged))
        else:
            logger.warn("Empty stats")

        time.sleep(ARGS.interval)


    plugin_cleanup()

if __name__ == "__main__": main()

