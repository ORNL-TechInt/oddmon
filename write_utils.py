#!/usr/bin/env python

'''
to be written
'''

import logging
import logging.handlers
import json
import ast

logger  = None

def write_data(msg):

    logger.debug("Calling push_to_splunk...")
    blob = json.loads(msg[0])

    #index = G.service.indexes[G.SPLUNK_INDEX]

    print "-----------------------------"
    print "blob type: %s"%type(blob)
    print "blob keys: %s"%blob.keys()
    print "============================="
    print "blob[u'metric_ost_brw_stats'] type: %s"%type(blob[u'metric_ost_brw_stats'])
    print "*****************************"
    stats = ast.literal_eval(blob[u'metric_ost_brw_stats'])
    print "stats type: %s"%type(stats)
    print "stats keys(): %s"%stats.keys()
    print "-----------------------------"
    print "type of first stats value: %s"%type(stats[stats.keys()[0]])
    print "first stats value keys: %s"%stats[stats.keys()[0]].keys()
    print "============================="

    stats = ast.literal_eval(blob[u'metric_ost_brw_stats'])
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


# Set up the loggers
logger = logging.getLogger("app.%s" % __name__)
FileLogger = logging.getLogger("file.%s" % __name__)
FileLogger.propagate = False

#log to file until reaching maxBytes then create a new log file
FileLogger.addHandler(logging.handlers.RotatingFileHandler("log.txt", maxBytes=1024*1024, backupCount=1))
FileLogger.setLevel(logging.DEBUG)


