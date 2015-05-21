#!/usr/bin/env python

'''
A collection of utility functions for dealing with Splunk
'''

import logging
import json
import ast
import getpass

import splunklib.client as client
import splunklib.results as results


logger  = None

class G:
    # Splunk connection stuff
    service = None
    SPLUNK_HOST="192.168.122.1"
    SPLUNK_PORT=8089
    SPLUNK_INDEX="brw_stats"

def connect_to_splunk():
    # Prompt for the password
    # This section should get cut out once we've got the api_ddntools
    # user set up
    #SPLUNK_USER=getpass.getuser()
    SPLUNK_USER=raw_input("Username: ")
    SPLUNK_PWD=getpass.getpass( 'Password for user %s:'%SPLUNK_USER)

    G.service = client.connect( host=G.SPLUNK_HOST, port=G.SPLUNK_PORT,
            username=SPLUNK_USER, password=SPLUNK_PWD)


def push_to_splunk( msg):

    logger.debug("Calling push_to_splunk...")
    blob = json.loads(msg[0])

    index = G.service.indexes[G.SPLUNK_INDEX]

    print "-----------------------------"
    print "blob type: %s"%type(blob)
    print "blob keys: %s"%blob.keys()
    #print blob[u'metric_ost_brw_stats']
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
            # event_str = "snapshot_time = %f "%snapshot_time

            # The values for the different metrics need to be handled differently
            if metric == "snapshot_time":
                continue # snapshot_time is not a metric in and of itself
            else:
                logger.debug(metric)
                value = metrics_dict[metric]
                for k in value.keys():
                    event_str = "snapshot_time = %f bucket=%s counts=%s" %(snapshot_time, k, value[k][0])
                    # logger.debug( "event_str: %s"%event_str)
                    # Commented out - too much text even for debug
                    index.submit( event_str, host = ost, source=metric, sourcetype="brw_stats")




# Set up the logger
logger = logging.getLogger("app.%s" % __name__)



