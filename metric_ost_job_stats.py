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
    buf = None
    timestamp = 0

def metric_init(name, loglevel=logging.DEBUG):
    global logger
    #G.timestamp = int(time.time())
    logger = logging.getLogger("main.%s" % __name__)
    G.fsname, G.ostnames = lfs_utils.scan_osts()

def metric_cleanup():
    pass

def get_stats():
    if G.fsname is None:
        logger.error("No valid file system...skip")
        return ""

    update()

    return json.dumps(G.stats)

def update():
    for ost in G.ostnames:
        fpath = '/proc/fs/lustre/obdfilter/' + ost
        ret = read_ost_stats(fpath)
        if ret:
            G.stats[ost] = ret
        else:
            G.stats[ost] = {}

def read_ost_stats(f):
    stats = []
    
    pfile = os.path.realpath(f) + "/job_stats"

    with open(pfile) as f:
        flag = True
        timestamp = int(time.time())
        kw = ["punch:", "setattr:", "sync:"]
        next(f)
        while flag:
            job = {}
            i = 1
            while i%8 != 0:
                try:
                    data = next(f)
                except:
                    flag = False
                    break
                line = data.split()
                if "job_id:" in line:
                    job["job_id:"] = line[2]
                elif "snapshot_time:" in line:
                    job["snapshot_time:"] = line[1]
                elif "read:" in line:
                    job["read_sum:"] = line[11]
                    job["read_samples:"] = line[3].strip(",")
                elif "write:" in line:
                    job["write_sum:"] = line[11]
                    job["write_samples:"] = line[3].strip(",")
                elif any(s in line for s in kw):
                    job[line[0]] = line[3].strip(",")
                i+=1
            if job:
                stats.append(job)
                G.timestamp = int(job["snapshot_time:"])
    return stats
