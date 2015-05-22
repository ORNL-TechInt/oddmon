#!/usr/bin/env python
from __future__ import print_function
"""
    A simple distributed monitoring tool with plugin support
    author: Feiyi Wang <fwang2@ornl.gov>

"""
import sys
import signal
import logging
import ConfigParser
import argparse
import hostlist
from daemon import Daemon

# Globals
logger  = logging.getLogger("app")
ARGS    = None

class G:
    hosts = None
    config = None
    fmt = None
    console_handler = None
    file_handler = None
    username = None
    password = None
    splunk_host = None
    splunk_port = None
    splunk_index = None

def parse_args():
    parser = argparse.ArgumentParser(description="ODDMON program")

    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument("-v", "--verbose", default=False, action="store_true", help="verbose output")
    parent_parser.add_argument("--cfgfile", required=True,  help="configure file")
    parent_parser.add_argument("-p", "--port", type=int, nargs=1, default=8888)
    parent_parser.add_argument("--stop", default=False, action="store_true")
    parent_parser.add_argument("--start", default=False, action="store_true")
    subparsers = parser.add_subparsers(help="Provide one of the sub-commands")
    collect_parser = subparsers.add_parser("collect", parents=[parent_parser], help="Run in collector mode")
    collect_parser.add_argument("-i", "--interval", type=int, nargs=1, default=10)
    collect_parser.add_argument("--pid", default="collect.pid")
    collect_parser.set_defaults(func=main_collect)
    aggregate_parser = subparsers.add_parser("aggregate", parents=[parent_parser], help="Run in aggregator mode")
    aggregate_parser.add_argument("--pid", default="aggregate.pid")
    aggregate_parser.set_defaults(func=main_aggregate)
    myargs = parser.parse_args()
    return myargs

def sig_handler(signal, frame):
    print("\tUser cancelled ... cleaning up")
    sys.exit(0)

class CollectDaemon(Daemon):
    def run(self):
        import oddpub
        oddpub.ARGS = ARGS
        oddpub.main()

class AggregateDaemon(Daemon):
    def run(self):
        import oddsub
        oddsub.ARGS = ARGS
        oddsub.main(G.hosts, G.port, G.url, G.username, G.password, G.splunk_port, G.splunk_host)


def handle(p):
    global logger
    if ARGS.stop:
            p.stop()
    elif ARGS.start:
            logger.removeHandler(G.console_handler)
            p.start()
    else:
            p.run()


def main_aggregate():
    p = AggregateDaemon(ARGS.pid)
    handle(p)

def main_collect():
    p = CollectDaemon(ARGS.pid)
    handle(p)


def setup_logging(loglevel):

    global logger

    level = getattr(logging, loglevel.upper())

    fmt = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger.setLevel(level)

    logfile = None
    if hasattr(ARGS, "collect"):
        logfile = "LOG.collector"
    else:
        logfile = "LOG.aggregator"

    file_handler = logging.FileHandler(filename=logfile, mode="w")
    file_handler.setFormatter(fmt)

    console_handler = logging.StreamHandler();
    console_handler.setFormatter(fmt)
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    logger.propagate = False
def main():
    global logger, ARGS

    signal.signal(signal.SIGINT, sig_handler)

    ARGS = parse_args()

    if ARGS.verbose:
        setup_logging("debug")
    else:
        setup_logging("info")

    logger.debug(ARGS)

    G.config = ConfigParser.SafeConfigParser()
    try:
        G.config.read(ARGS.cfgfile)
        G.hosts = hostlist.expand_hostlist(G.config.get("global", "pub_hosts"))
        G.url = G.config.get("DB", "url")
        G.port = G.config.get("global", "pub_port")
        G.username = G.config.get("splunk", "username")
        G.password = G.config.get("splunk", "password")
        G.splunk_host = G.config.get("splunk", "host")
        G.splunk_port = G.config.get("splunk", "port")
        G.splunk_index = G.config.get("splunk", "index")
    except:
        logger.error("Can't read configuration file")
        sys.exit(1)

    ARGS.func()

if __name__ == "__main__": main()

