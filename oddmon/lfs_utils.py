#!/usr/bin/env python

# This work was supported by the Oak Ridge Leadership Computing Facility at
# the Oak Ridge National Laboratory, which is managed by UT Battelle, LLC for
# the U.S. DOE (under the contract No. DE-AC05-00OR22725).
#
#
# This file is part of OddMon.
#
# OddMon is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software
# Foundation, either version 2 of the License, or (at your option) any later
# version.
#
# OddMon is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along
# with OddMon.  If not, see <http://www.gnu.org/licenses/>.

import os
import glob
import logging

class G:
    fmt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

def scan_targets( OSS=True):
    fsname = None
    targetnames = []
    targets = []
    
    if OSS:
        targets = glob.glob("/proc/fs/lustre/obdfilter/*OST*")
    else:
        targets = glob.glob("/proc/fs/lustre/mdt/*MDT*")
        
    if len(targets) != 0:
        fsname, _ = os.path.basename(targets[0]).split("-")
        for target in targets:
            targetnames.append(os.path.basename(target))
    return fsname, targetnames

def get_filehandler(f, m="w", level=logging.DEBUG):
    fh = logging.FileHandler(filename=f, mode=m)
    fh.setLevel(level)
    fh.setFormatter(G.fmt)
    return fh

def get_consolehandler(level=logging.DEBUG):
    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(G.fmt)
    return ch



