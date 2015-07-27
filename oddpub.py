#!/usr/bin/env python
__version__ = "0.1"
"""
    A simple distributed monitoring tool with plugin support
    author: Feiyi Wang <fwang2@ornl.gov>

"""
import sys
import time
import logging
import zmq
import json
import plugins

# Globals
logger  = None
ARGS    = None

class G:
    context = None
    publisher = None
    config = None

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
    plugins.cleanup()
    sys.exit(0)





def main():
    global logger, ARGS
    logger = logging.getLogger("app.%s" % __name__)

    zmq_init()

    # initialize all metric modules

    plugins.scan(".")
    plugins.init()

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
            G.publisher.send_string(json.dumps(merged))
        else:
            logger.warn("Empty stats")

        time.sleep(ARGS.interval)


    plugins.cleanup()

if __name__ == "__main__": main()

