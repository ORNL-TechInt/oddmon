#!/usr/bin/env python

import os
import glob
import logging
import json
import time
from collections import defaultdict
try:
    from oddmon import lfs_utils
except:
    import lfs_utils

# Globals

logger = None

class G:
    fsname = None
    ostnames = None
    stats = defaultdict(lambda: defaultdict(int))

def read_ost_stats(f):
    """
    expect input of a path to ost stats
    return a dictionary with key/val pairs
    """
    ret = {'read_bytes_sum': 0, 'write_bytes_sum': 0}

    pfile = os.path.normpath(f) + "/stats"
    with open(pfile, "r") as f:
            for line in f:
                chopped = line.split()
                if chopped[0] == "snapshot_time":
                    ret["snapshot_time"] = chopped[1]
                if chopped[0] == "write_bytes":
                    ret["write_bytes_sum"] = chopped[6]
                if chopped[0] == "read_bytes":
                    ret["read_bytes_sum"] = chopped[6]

    return ret


def update():
    logger.debug("Updating stats")

    for ost in G.ostnames:
        fpath = '/proc/fs/lustre/obdfilter/' + ost
        G.stats[ost] = read_ost_stats(fpath)

    logger.debug("Sucessfully refreshing OST stats")


def metric_init(name, loglevel=logging.DEBUG):
    global logger
    logging.basicConfig(level=loglevel,
                    format="%(asctime)s - %(name)s - %(levelname)s\t - %(message)s")
    logger = logging.getLogger(name)

    G.fsname, G.ostnames = lfs_utils.scan_osts()

def get_stats():

    if G.fsname is None:
        logger.error("No valid file system ... skip")
        return ""

    update()

    return json.dumps(G.stats)

def metric_cleanup():
    pass

if __name__ == '__main__':
    metric_init("ost-stats")
    while True:
        print get_stats()
        time.sleep(5)
    metric_cleanup()

