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

class JobDataError( RuntimeError):
    pass

# Holds a subset of the job data that we want to save for comparison
# with the next sample.  See G.job_times below.
class JobSummary:
    def __init__(self, ts=0, wsum=0, rsum=0, wsamp=0, rsamp=0):
        self.timestamp = ts
        self.write_sum = wsum
        self.read_sum = rsum
        self.write_samples = wsamp
        self.read_samples = rsamp
    
    def __str__(self): # this is mostly for debugging
        return "Timestamp: %d  WriteSum: %d  " % (self.timestamp, self.write_sum) + \
               "ReadSum: %d  WriteSamples: %d  " % (self.read_sum, self.write_samples) + \
               "ReadSamples: %d" % self.read_samples

# A class used simply as a place to store globals (and in particular, the C
# equivalent of static globals). Don't instantiate individual 'G' objects.
class G:
    # attributes used by the subscriber
    stats = defaultdict(lambda: defaultdict(int))
    buf = None
    save_dir = None

    # attributes used by the publisher
    fsname = ''
    target_names = []
    # Holds the names of the OST or MDT target(s) that the server we're
    # running on manages.

    job_times = defaultdict(lambda: defaultdict( JobSummary))
    # A dict of dicts of the most recent job id's timestamp, read_sum &
    # write_sum values.  Used down in read_target_stats() to ensure we don't
    # repeat data that hasn't changed since the previous check and also to
    # calculate the delta values for read_sum & write_sum
    # ex: G.job_times[<OST Name>][<job ID>].timestamp = <timestamp>

    is_mds = True  # We handle the MDS a little differently from the OSS's

    # attributes used by both subscriber & publisher
    # None yet...


def metric_init(name, config_file, is_subscriber=False,
                loglevel=logging.DEBUG):
    global logger, stats_logger
    logger = logging.getLogger("app.%s" % __name__)

    rv = True
    if is_subscriber is False:
        G.fsname, G.target_names = lfs_utils.scan_targets(OSS=False)
        if not G.target_names:
            # Check if we're running on an OSS
            G.is_mds = False
            G.fsname, G.target_names = lfs_utils.scan_targets(OSS=True)
            if not G.target_names:
                logger.warn("No OST's or MDT's found.  Disabling plugin.")
                rv = False
            elif not G.fsname:
                logger.error("OST's found, but could not discern filesystem "
                             "name. (This shouldn't happen.)  Disabling "
                             "plugin.")
                rv = False
        elif not G.fsname:
            logger.error("MDT's found, but could not discern filesystem "
                         "name. (This shouldn't happen.)  Disabling "
                         "plugin.")
            rv = False
          
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
                logging.handlers.TimedRotatingFileHandler(
                    stats_logger_name, when='h', interval=6, backupCount=5))
            stats_logger.setLevel(logging.DEBUG)
        except ConfigParser.Error, e:
            logger.error("Problem reading configuration file")
            logger.error("Exception: %s" % e)
            rv = False
        except Exception, e:
            logger.error("Unexpected Exception: %s" % e)
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
    # msg (and thus stats) is organized as a dictionary with target (OST or
    # MDT) names for keys.  The associated values are themselves lists of
    # dictionaries where each dictionary is the key/value data for one job.

    for target in stats:
        jobList = stats[target]
        for job in jobList:
            # convert the python structure into an event string suitable
            # for Splunk and write it out
            # Note that the formats for the OST's and MDT's differ
            if 'mknod:' in job:  # Is this an MDT record?
                event_str = "ts=%d job_id=%s open=%d  close=%d " %\
                            (int(job["snapshot_time:"]), str(job["job_id:"]),
                             int(job["open:"]), int(job["close:"]))
                event_str += "mknod=%d link=%d unlink=%d mkdir=%d " %\
                             (int(job["mknod:"]), int(job["link:"]),
                              int(job["unlink:"]), int(job["mkdir:"]))
                event_str += "rmdir=%d rename=%d getattr=%d setattr=%d " %\
                             (int(job["rmdir:"]), int(job["rename:"]),
                              int(job["getattr:"]), int(job["setattr:"]))
                event_str += "getxattr=%d setxattr=%d statfs=%d sync=%d " %\
                             (int(job["getxattr:"]), int(job["setxattr:"]),
                              int(job["statfs:"]), int(job["sync:"]))
                event_str += "samedir_rename=%d crossdir_rename=%d MDS=%s" %\
                             (int(job["samedir_rename:"]),
                              int(job["crossdir_rename:"]), str(target))
            else:  # OST record
                event_str = "ts=%d job_id=%s OST=%s " %\
                    (int(job["snapshot_time:"]), str(job["job_id:"]),
                     str(target))
                event_str += "punch=%d setattr=%d sync=%d " %\
                    (int(job["punch:"]), int(job["setattr:"]),
                     int(job["sync:"]))
                event_str += "write_samples=%d write_sum=%d " % \
                    (int(job["write_samples:"]), int(job["write_sum:"]))              
                event_str += "read_samples=%d read_sum=%d" %\
                    (int(job["read_samples:"]), int(job["read_sum:"]))
                

                # Older versions of the client don't have the *_delta keys
                # and we don't want to crash with a KeyError exception.                             
                if job.has_key("write_samples_delta"):
                    event_str += " wsamp_d=%d" % int(job["write_samples_delta"])
                if job.has_key("write_sum_delta"):
                    event_str += " wsum_d=%d" % int(job["write_sum_delta"])
                if job.has_key("read_samples_delta"):
                    event_str += " rsamp_d=%d" % int(job["read_samples_delta"])
                if job.has_key("read_sum_delta"):
                    event_str += " rsum_d=%d" % int(job["read_sum_delta"])

            stats_logger.info(event_str)


def update():
    if G.is_mds:
        base_path = '/proc/fs/lustre/mdt/'
    else:
        base_path = '/proc/fs/lustre/obdfilter/'

    for target in G.target_names:
        fpath = base_path + target
        ret = read_target_stats(fpath, target)
        if ret:
            G.stats[target] = ret
        else:
            # The only time we'd get here is if read_target_stats() hit an
            # error and exited early...which it wouldn't do without raising
            # an exception.
            G.stats[target] = []


def process_job_data( job, target_name):
    '''
    Compares the collected data for one job against the previous data for that job.
    
    job is a dictionary who's keys are from the job_stats file ("setattr:",
    "write_bytes:", etc..).  If the data in job is newer that what we have
    stored in G.job_times, then do some more post-processing on it (calculate
    the read and write delta values, if necessary) and update G.job_times.
    
    Returns True if the job has new data that needs to be sent to the
    aggregator.
    '''
    
    rv = False  # return value
    
    # First, some sanity checks.  What fields are in the dictionary depends on
    # the Lustre version and whether we're on an OSS or MDS, but a couple of fields
    # are mandatory
    if not ("job_id:" in job) or \
       not ("snapshot_time:" in job):
        raise JobDataError();

    # Now check the snapshot time against G.job_times
    job_id = job["job_id:"]
    if G.job_times[target_name][job_id].timestamp >= \
        int(job["snapshot_time:"]):
        # Hooray for defaultdict:  if the time hasn't been set,
        # it will default to 0
        pass
    else: # job containds newer data - update G.job_times
        # Data from the OSS's has read & write bytes values, and we need to
        # calculate deltas using the previous data from G.job_times
        if ("write_sum:" in job):  # if write_sum exists, so will the others
            job["write_sum_delta"] = int(job["write_sum:"]) - G.job_times[target_name][job_id].write_sum
            job["read_sum_delta"] = int(job["read_sum:"]) - G.job_times[target_name][job_id].read_sum                  
            job["write_samples_delta"] = int(job["write_samples:"]) - G.job_times[target_name][job_id].write_samples
            job["read_samples_delta"] = int(job["read_samples:"]) - G.job_times[target_name][job_id].read_samples
            
            # overwrite the old summary data with the new
            G.job_times[target_name][job_id] = \
                JobSummary( int(job["snapshot_time:"]), int(job["write_sum:"]),
                            int(job["read_sum:"]), int(job["write_samples:"]),
                            int(job["read_samples:"]))
            # Note the conversions to int!  We want to ensure the
            # comparison up above works as expected!
        else: # this is MDS data - just need the timestamp
            # overwrite the old summary data with the new
            G.job_times[target_name][job_id] = \
                JobSummary( int(job["snapshot_time:"]))
        rv = True

    return rv
        
    
    
def read_target_stats( path, target_name):
    '''
    Parse the job_stats file in the specified path
    '''
    stats = []  # The return value - a list of dictionaries where each
                # dictionary holds key/value pairs for a single job

    pfile = os.path.realpath(path) + "/job_stats"

    with open(pfile) as f:
        flag = True
        timestamp = int(time.time())
      
        next(f)  # ignore the first line (it just says "job stats:")
        job = {}  # stores key/value pairs for a single job in the file`
        for data in f:
            line = data.split()

            if line[0] == '-':
                # Start of a new job - check to see if the he previous job actually
                # contains new data
                if (len( job)): # If we're at the top of the file, job will be empty
                    if process_job_data( job, target_name):
                        stats.append(job)
                    job = {}

            # There's some lines in the stanza that are special cases
            if "job_id:" in line:
                job["job_id:"] = line[2]
            elif "snapshot_time:" in line:
                job["snapshot_time:"] = line[1]
            # "read:" and "write:" are only in 2.5
            elif "read:" in line:
                job["read_sum:"] = line[11]
                job["read_samples:"] = line[3].strip(",")
            elif "write:" in line:
                job["write_sum:"] = line[11]
                job["write_samples:"] = line[3].strip(",")
            # "read_bytes:" and "write_bytes:" are only in 2.8 (and probably newer)
            elif "read_bytes:" in line:
                job["read_sum:"] = line[11]
                job["read_samples:"] = line[3].strip(",")
            elif "write_bytes:" in line:
                job["write_sum:"] = line[11]
                job["write_samples:"] = line[3].strip(",")
            else:  # all the other lines are handled identically
                job[line[0]] = line[3].strip(",")

        # End of the for loop (and thus the file), process the last job dict
        if (len(job)):
            # Practically speaking, the only time job would be empty is
            # during testing on my VM's, but process_job_data will throw
            # an exception if the required fields are missing, so we check
            # for an empty dict before calling the function.
            if process_job_data( job, target_name):
                stats.append(job)
        
    return stats
