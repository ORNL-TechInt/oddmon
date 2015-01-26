#!/usr/bin/env python

import os
import glob



def scan_osts():
    fsname=None
    ostnames = []
    osts = glob.glob("/proc/fs/lustre/obdfilter/*")
    if len(osts) != 0:
        fsname, _ = os.path.basename(osts[0]).split("-")
        for ost in osts:
            ostnames.append(os.path.basename(ost))
    return fsname, ostnames



