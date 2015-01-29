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
import glob

import oddpub
import oddsub

# Globals
logger  = None
ARGS    = None

class G:

    context = None
    publisher = None
    config = None
    plugins = {}
    callbacks = ['metric_init', 'get_stats', 'metric_cleanup']

def parse_args():
    parser = argparse.ArgumentParser(description="MOND program")
    parent_parser = argparse.ArgumentParser(add_help=False)

    parent_parser.add_argument("-v", "--verbose", default=False, action="store_true", help="verbose output")
    parent_parser.add_argument("-c", "--conf", default="oddmon.cfg", help="configure file")

    subparsers = parser.add_subparsers(help="Provide one of the sub-commands")

    pub_parser = parsers.add_parser("server", parents=[parent_parser], help="Run in server mode")
    pub_parser.set_defaults(func=main_pub)

    sub_parser = parsers.add_parser("client", parents=[parent_parser], help="Run in client mode")
    sub_parser.set_defaults(func=main_sub)

    myargs = parser.parse_args()
    return myargs

def sig_handler(signal, frame):

    print "\tUser cancelled ... cleaning up"
    sys.exit(0)


def main():
    global logger, ARGS

    signal.signal(signal.SIGINT, sig_handler)

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

    ARGS.func()

if __name__ == "__main__": main()

