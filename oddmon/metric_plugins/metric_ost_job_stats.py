#!/usr/bin/env python

import os
import logging
import logging.handlers
import json
import time
import ConfigParser
from collections import defaultdict
try:
    from oddmon import lfs_utils
except:
    import lfs_utils

logger = None        # used for normal logging messages
stats_logger = None  # the logger we use to write the stats data


class G:
    fsname = None
    ostnames = None
    stats = defaultdict(lambda: defaultdict(int))
    buf = None
    timestamp = 0
    jobids = {}
    save_dir = None


def metric_init(name, config_file, is_subscriber=False,
                loglevel=logging.DEBUG):
    global logger, stats_logger
    logger = logging.getLogger("app.%s" % __name__)

    rv = True
    if is_subscriber is False:
        G.fsname, G.ostnames = lfs_utils.scan_osts()
    else:
        # config file is only needed for the location of the
        # stats_logger file, and that's only needed on the
        # subscriber side
        config = ConfigParser.SafeConfigParser()
        try:
            config.read(config_file)
            G.save_dir = config.get(name, "save_dir")

            # log to file until reaching maxBytes then create a new log file
            stats_logger = logging.getLogger("brw_stats.%s" % __name__)
            stats_logger.propagate = False
            stats_logger_name = G.save_dir+os.sep+"job_log.txt"
            logger.debug("Stats data saved to: %s" % stats_logger_name)
            stats_logger.addHandler(
                logging.handlers.RotatingFileHandler(stats_logger_name,
                                                     maxBytes=1024*1024*1024,
                                                     backupCount=1))
            stats_logger.setLevel(logging.DEBUG)
        except Exception, e:
            logger.error("Can't read configuration file")
            logger.error("Exception: %s" % e)
            rv = False

    return rv

def metric_cleanup(is_subscriber=False):
    pass


def get_stats():
    if G.fsname is None:
        logger.error("No valid file system...skip")
        return ""

    update()

    return json.dumps(G.stats)


def save_stats(msg):
    stats = json.loads(msg)

    for ost in stats.keys():
        if ost in G.jobids.keys():
            pass
        else:
            G.jobids[ost] = []
        jobList = stats[ost]
        for job in jobList:
            if job["job_id:"] in G.jobids[ost]:
                pass
            else:
                if int(job["snapshot_time:"]) > G.timestamp:
                    G.jobids[ost].append(job["job_id:"])
                    event_str = ("snapshot_time=%d job_id=%d write_samples=%d "
                                 "write_sum=%d read_samples=%d read_sum=%d "
                                 "punch=%d setattr=%d sync=%d OST=%s"
                                 % (int(job["snapshot_time:"]), int(job["job_id:"]), int(job["write_samples:"]), int(job["write_sum:"]),
                                    int(job["read_samples:"]), int(job["read_sum:"]), int(job["punch:"]), int(job["setattr:"]),
                                    int(job["sync:"]), str(ost))
                                )
                    stats_logger.info(event_str)
                else:
                    logger.debug( "Old data")


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
            while i % 8 != 0:
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
                i += 1
            if job:
                stats.append(job)
                G.timestamp = int(job["snapshot_time:"])
    return stats
