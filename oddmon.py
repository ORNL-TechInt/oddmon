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
    parser = argparse.ArgumentParser(description="ODDMON program")

    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument("-v", "--verbose", default=False, action="store_true", help="verbose output")
    parent_parser.add_argument("--cfgfile", required=True,  help="configure file")
    subparsers = parser.add_subparsers(help="Provide one of the sub-commands")
    collect_parser = subparsers.add_parser("collect", parents=[parent_parser], help="Run in collector mode")
    collect_parser.add_argument("-p", "--port", type=int, nargs=1, default=8888)
    collect_parser.add_argument("-i", "--interval", type=int, nargs=1, default=10)
    collect_parser.set_defaults(func=main_collect)
    aggregate_parser = subparsers.add_parser("aggregate", parents=[parent_parser], help="Run in aggregator mode")
    aggregate_parser.set_defaults(func=main_aggregate)
    myargs = parser.parse_args()
    return myargs

def sig_handler(signal, frame):

    print "\tUser cancelled ... cleaning up"
    sys.exit(0)


def main_collect():
    import oddpub
    oddpub.ARGS = ARGS
    oddpub.main()

def main_aggregate():
    import oddsub


def setup_logging(loglevel):
    global logger
    logger = logging.getLogger("main")

    level = getattr(logging, loglevel.upper())
    logger.setLevel(level)

    fmt = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh = logging.FileHandler(filename="oddmon.log", mode="w")
    fh.setFormatter(fmt)
    ch = logging.StreamHandler();
    ch.setFormatter(fmt)
    ch.setLevel(level)
    logger.addHandler(fh)
    logger.addHandler(ch)

def main():
    global logger, ARGS

    signal.signal(signal.SIGINT, sig_handler)

    ARGS = parse_args()

    if ARGS.verbose:
        setup_logging("debug")
    else:
        setup_logging("info")

    logger.debug(ARGS)

    try:
        G.config = ConfigParser.SafeConfigParser()
        G.config.read(ARGS.cfgfile)
    except:
        logger.error("Can't read configuration file")
        sys.exit(1)

    ARGS.func()

if __name__ == "__main__": main()

