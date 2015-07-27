#!/usr/bin/env python
__version__ = "0.1"
"""
Plugin support for oddpub & oddsub
"""

import os.path
import imp
import logging
import glob

# TODO: For the moment, this code has just be copied verbatum
# out of oddpub.py.  This class G is probably something we
# want to replace with a proper interface.  Or maybe an 
# attribute on the plugins module itself??
class G:
    plugins = {}
    callbacks = ['metric_init', 'get_stats', 'metric_cleanup']

def scan(pathname):

    pathname = os.path.realpath(pathname) + "/metric*.py"
    logger = logging.getLogger("app.%s" % __name__)
    logger.debug("Plugin path: %s" % pathname)
    sources = glob.glob(pathname)

    for s in sources:
        name = os.path.basename(s).split(".")[0]
        mod = imp.load_source(name, s)
        if set(G.callbacks).issubset(set(dir(mod))):
            G.plugins[name] = mod
            logger.info("Registering plugin: %s" % name)
        else:
            logger.warn("Skipping %s" % name)

def init():
    for name, mod in G.plugins.iteritems():
        mod.metric_init(name)

def cleanup():
    for name, mod in G.plugins.iteritems():
        mod.metric_cleanup()