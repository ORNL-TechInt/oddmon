#!/usr/bin/env python

import os
import logging
import json
import time
from collections import defaultdict
try:
    from oddmon import lfs_utils
except:
    import lfs_utils

logger = None


class G:
    fsname = None
    ostnames = None
    stats = defaultdict(lambda: defaultdict(int))


def metric_init(name, config_file, is_subscriber=False,
                loglevel=logging.DEBUG):
    global logger
    logger = logging.getLogger("app.%s" % __name__)
    rv = True
    
    G.fsname, G.ostnames = lfs_utils.scan_targets(OSS=True)
    if not G.ostnames:
        logger.warn("No OST's found.  Disabling plugin.")
        rv = False
    elif not G.fsname:
        logger.error("OST's found, but could not discern filesystem name. "
                     "(This shouldn't happen.)  Disabling plugin.")
        rv = False
    
    return rv


def metric_cleanup(is_subscriber=False):
    pass


def get_stats():

    if G.fsname is None:
        logger.error("No valid file system ... skip")
        return ""

    update()

    return json.dumps(G.stats)


def save_stats(msg):
    logger = logging.getLogger("app.%s" % __name__)
    logger.warning("save_stats() unimplemented!")


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
                    ret["write_bytes_sum"] = int(chopped[6])
                if chopped[0] == "read_bytes":
                    ret["read_bytes_sum"] = int(chopped[6])

    if ret['read_bytes_sum'] == 0 and ret['write_bytes_sum'] == 0:
        return None

    return ret


def update():

    for ost in G.ostnames:
        fpath = '/proc/fs/lustre/obdfilter/' + ost
        ret = read_ost_stats(fpath)
        if ret:
            G.stats[ost] = ret


if __name__ == '__main__':
    metric_init("ost-stats")
    while True:
        print get_stats()
        time.sleep(5)
    metric_cleanup()
