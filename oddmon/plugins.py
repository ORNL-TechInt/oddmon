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

__version__ = "0.1"
"""
Plugin support for oddpub & oddsub

Plugin protocol documentation:

Plugins must define 4 functions:

def metric_init(name, config_file, is_subscriber = False, loglevel=logging.DEBUG)   
def metric_cleanup( is_subscriber = False)
def get_stats()
def save_stats( msg)


metric_init returns True if it initialized properly.
get_stats() returns the data that is to be published.  (Currently all plugins
use JSON-encoded text, but that's probably not actually necessary.)

The other functions return nothing.

get_stats() is called by the publisher.  save_stats() is called by the
subscriber.  metric_init() and metric_cleanup() are called by both.

The data that get_stats() returns (on the publisher side) is passed to
save_stats() (on the subscriber side).  It's up to save_stats() to do
something useful with the data.
"""

#TODO: Should we switch to using kwargs for the plugin callback functions?

import os.path
import imp
import logging
import glob
import ConfigParser

class _G:
    plugins = {}
    callbacks = ['metric_init', 'get_stats', 'save_stats', 'metric_cleanup']

def scan(pathname, disabled_plugins):

    pathname = os.path.realpath(pathname) + "/metric*.py"
    logger = logging.getLogger("app.%s" % __name__)
    logger.debug("Plugin path: %s" % pathname)
    logger.debug("Disabled plugins: %s" % disabled_plugins)
    sources = glob.glob(pathname)

    for s in sources:
        name = os.path.basename(s).split(".")[0]
        if name in disabled_plugins:
            logger.info ("%s plugin disabled by config file. " % name)
        else:
            mod = imp.load_source(name, s) 
            if set(_G.callbacks).issubset(set(dir(mod))):
                _G.plugins[name] = mod
                logger.info("Registering plugin: %s" % name)
            else:
                logger.warn("Skipping %s" % name)


def init( config_file, is_subscriber = False):
    names = _G.plugins.keys();
    for name in names:
        if (_G.plugins[name].metric_init(name, config_file, is_subscriber) == False):
            logger = logging.getLogger("app.%s" % __name__)    
            logger.warn( "%s failed to initialize. "
                         "Removing from plug-ins list" % name)
            _G.plugins.pop(name)
           

def cleanup( is_subscriber = False):
    for name, mod in _G.plugins.iteritems():
        mod.metric_cleanup( is_subscriber)
        
def found():
    '''
    Really simple, but lets us do things like "for name,mod in plugins.found():"
    '''
    return _G.plugins.iteritems()