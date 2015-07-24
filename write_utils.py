#!/usr/bin/env python

'''
to be written
'''

import logging
import logging.handlers
import json
import time

logger  = None

class G:
    timestamp = int(time.time())
    jobids = {}
    save_dir = ""

def get_log_loc(save_dir):
    G.save_dir = save_dir

def write_data(msg):
    logger.debug("Writing data...")
    blob = json.loads(msg[0])
    print G.save_dir
    print "-----------------------------"
    print "blob type: %s"%type(blob)
    print "blob keys: %s"%blob.keys()
    print "============================="

    job_stats = json.loads(blob[u'metric_ost_job_stats'])
    brw_stats = json.loads(blob[u'metric_ost_brw_stats'])
    
    if brw_stats:
        write_brw_stats(brw_stats)
    else:
        print "Empty BRW stats data"

    if all(not d for d in job_stats.values()):
        print "Empty job stats data"
        G.jobids = {}
    else:
        write_job_stats(job_stats)

# Set up the loggers
logger = logging.getLogger("app.%s" % __name__)
FileLogger = logging.getLogger("brw_stats.%s" % __name__)
JobLogger = logging.getLogger("job_stats.%s" % __name__)
JobLogger.propagate = False
FileLogger.propagate = False

#log to file until reaching maxBytes then create a new log file
FileLogger.addHandler(logging.handlers.RotatingFileHandler(G.save_dir+"brw_log.txt", maxBytes=1024*1024*1024, backupCount=1))
FileLogger.setLevel(logging.DEBUG)
JobLogger.addHandler(logging.handlers.RotatingFileHandler(G.save_dir+"job_log.txt", maxBytes=1024*1024*1024, backupCount=1))
JobLogger.setLevel(logging.DEBUG)

def write_brw_stats(stats):
    for ost in stats.keys():
        metrics_dict = stats[ost]
        snapshot_time = float(metrics_dict["snapshot_time"])
        for metric in metrics_dict.keys():
            if metric == "snapshot_time":
                continue # snapshot_time is not a metric in and of itself
            else:
                logger.debug(metric)
                value = metrics_dict[metric]
                for k in value.keys():
                    event_str = "snapshot_time=%f bucket=%s counts=%s" %(snapshot_time, k, value[k][0])
                    FileLogger.info("%s host=%s source=%s sourcetype=brw_stats", event_str, str(ost), str(metric))

def write_job_stats(stats):
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
                    event_str =("snapshot_time=%d job_id=%d write_samples=%d write_sum=%d read_samples=%d read_sum=%d "
                                "punch=%d setattr=%d sync=%d host=%s sourcetype=job_stats"
                                % (int(job["snapshot_time:"]), int(job["job_id:"]), int(job["write_samples:"]), int(job["write_sum:"]),
                                    int(job["read_samples:"]), int(job["read_sum:"]), int(job["punch:"]), int(job["setattr:"]),
                                    int(job["sync:"]), str(ost))
                                )
                    print event_str
                    JobLogger.info(event_str)
                else:
                    print "Old data"

