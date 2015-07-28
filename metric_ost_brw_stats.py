#!/usr/bin/env python

import os
import logging
import logging.handlers
import ConfigParser
import json
import time
from collections import defaultdict
try:
    from oddmon import lfs_utils
except:
    import lfs_utils

# Globals
logger = None  # used for normal logging messages
stats_logger = None # the logger we use to write the stats data

class G:
    fsname = None
    ostnames = None
    stats = defaultdict(lambda: defaultdict(int))
    buf = None
    save_dir = None

def extract_snaptime(ret):
    idx = G.buf.index('\n')
    ret['snapshot_time'] = G.buf[0].split()[1]
    # update buffer
    G.buf = G.buf[idx+1:]

def extract_hist(key1, key2, ret):
    idx = None

    try:
        idx = G.buf.index('\n')
    except:
        idx = len(ret) + 1

    # skip #0 and #1
    # process 1 line at a time
    for line in G.buf[2:idx]:
        fields = line.split()

        # after split: ['128:', '0', '0', '0', '|', '2', '0', '0']
        # first field '128:', remove colon
        ret[key1][fields[0][:-1]]  = fields[1:4]
        ret[key2][fields[0][:-1]] = fields[5:]

    # update buffer
    G.buf = G.buf[idx+1:]


def read_brw_stats(f):
    """
    expect input of a path to brw stats eg.
    /proc/fs/lustre/obdfilter/mytest-OST0000/brw_stats

    return a dictionary with key/val pairs
    """

    ret = { "snapshot_time"                 :'',
            "pages_per_bulk_read"           :defaultdict(list),
            "pages_per_bulk_write"          :defaultdict(list),
            "discontinuous_pages_read"       :{},
            "discontinuous_pages_write"      :{},
            "discontinuous_blocks_read"      :{},
            "discontinuous_blocks_write"     :{},
            "disk_fragmented_io_read"       :{},
            "disk_fragmented_io_write"      :{},
            "disk_io_in_flight_read"        :{},
            "disk_io_in_flight_write"       :{},
            "io_time_read"                  :{},
            "io_time_write"                 :{},
            "io_size_read"                  :{},
            "io_size_write"                 :{}
           }

    pfile = os.path.realpath(f) + "/brw_stats"
    with open(pfile, "r") as f:
        G.buf = f.readlines()
        extract_snaptime(ret)
        extract_hist('pages_per_bulk_read', 'pages_per_bulk_write', ret)
        extract_hist('discontinuous_pages_read', 'discontinuous_pages_write', ret)
        extract_hist('discontinuous_blocks_read', 'discontinuous_blocks_write', ret)
        extract_hist('disk_fragmented_io_read', 'disk_fragmented_io_write', ret)
        extract_hist('disk_io_in_flight_read', 'disk_io_in_flight_write', ret)
        extract_hist('io_time_read', 'io_time_write', ret)
        extract_hist('io_size_read', 'io_size_write', ret)

    # trim
    for key in ret.keys():
        if len(ret[key]) == 0:
            del ret[key]

    if len(ret.keys()) > 1:
        return ret
    else:                   # if only snapshot_time, return None
        return None


def update():
    for ost in G.ostnames:
        fpath = '/proc/fs/lustre/obdfilter/' + ost
        ret = read_brw_stats(fpath)
        if ret: G.stats[ost] = ret


def metric_init(name, config_file, is_subscriber = False, loglevel=logging.DEBUG):
    global logger, stats_logger
    logger = logging.getLogger("app.%s" % __name__)
    
    rv = True;
    if is_subscriber == False:
        G.fsname, G.ostnames = lfs_utils.scan_osts()   
    else:
        # config file is only needed for the location of the
        # stats_logger file, and that's only needed on the 
        # subscriber side
        config = ConfigParser.SafeConfigParser()
        try:
            config.read(config_file)
            G.save_dir = config.get(name, "save_dir")
        except Exception, e:
            logger.error("Can't read configuration file")
            logger.error("Exception: %s"%e)
            rv = False;

        #log to file until reaching maxBytes then create a new log file
        stats_logger = logging.getLogger("brw_stats.%s" % __name__)
        stats_logger.propagate = False
        stats_logger_name = G.save_dir+os.sep+"brw_log.txt"
        logger.debug("Stats data saved to: %s"%stats_logger_name)
        stats_logger.addHandler(logging.handlers.RotatingFileHandler(stats_logger_name, maxBytes=1024*1024*1024, backupCount=1))
        stats_logger.setLevel(logging.DEBUG)

    return rv;
    
def metric_cleanup( is_subscriber = False):
    pass

    
def get_stats():
    if G.fsname is None:
        logger.error("No valid file system ... skip")
        return ""

    update()
    return json.dumps(G.stats)


def save_stats( msg):
    brw_stats = json.loads(msg)
    for ost in brw_stats.keys():
        metrics_dict = brw_stats[ost]
        snapshot_time = float(metrics_dict["snapshot_time"])
        for metric in metrics_dict.keys():
            if metric == "snapshot_time":
                continue # snapshot_time is not a metric in and of itself
            else:
                logger.debug(metric)
                value = metrics_dict[metric]
                for k in value.keys():
                    event_str = "snapshot_time=%f bucket=%s counts=%s" %(snapshot_time, k, value[k][0])
                    stats_logger.info("%s host=%s source=%s sourcetype=brw_stats", event_str, str(ost), str(metric))
    
    



if __name__ == '__main__':
    # Set up a basic logging handler to use
    # logging.getLogger("main.__main__").addHandler(logging.StreamHandler())
    metric_init("brw-stats")
    while True:
        print get_stats()
        time.sleep(5)
    metric_cleanup()

