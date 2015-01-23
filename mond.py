#!/usr/bin/env python

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

logging.basicConfig(level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s\t - %(message)s")

class G:

    context = None
    socket = None
    config = None
    plugins = {}

def zmq_init(pub):

    logging.debug("Bind to %s" % pub)
    G.context = zmq.Context()
    G.socket = G.context.socket(zmq.PUB)
    G.socket.bind(pub)

def sig_handler(signal, frame):

    print "\tUser cancelled!"
    sys.exit(0)


def plugin_init(pathname):

    pathname = os.path.realpath(pathname) + "/*.py"

    logging.debug("Plugin path: %s" % pathname)

    sources = glob.glob(pathname)


    for s in sources:
        name = os.path.basename(s).split(".")[0]
        mod = imp.load_source(name, s)
        try:
            mod.get_stats()
        except:
            logging.warn("Skipping %s" % name)
        G.plugins[name] = mod


    logging.debug("Found plugins: %s" % "".join(G.plugins.keys()))

def main():

    signal.signal(signal.SIGINT, sig_handler)

    G.config = ConfigParser.SafeConfigParser()
    G.config.read("oddman.conf")
    pub = G.config.get("global", "pub")
    interval = G.config.getint("global", "interval")
    zmq_init(pub)

    # initialize all metric modules

    plugin_init("./plugins")

    while True:
        for name, mod in G.plugins.iteritems():
            msg = mod.get_stats()
            logging.debug("%s -> %s" % (name, msg))
            G.socket.send_string(msg)

        time.sleep(interval)

if __name__ == "__main__": main()

