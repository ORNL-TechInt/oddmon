#!/usr/bin/env python
__version__ = "0.1"
"""
Plugin support for oddpub & oddsub
"""

import os.path
import imp
import logging
import glob

class _G:
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
        if set(_G.callbacks).issubset(set(dir(mod))):
            _G.plugins[name] = mod
            logger.info("Registering plugin: %s" % name)
        else:
            logger.warn("Skipping %s" % name)

def init():
    for name, mod in _G.plugins.iteritems():
        mod.metric_init(name)

def cleanup():
    for name, mod in _G.plugins.iteritems():
        mod.metric_cleanup()
        
def found():
    '''
    Really simple, but lets us do things like "for name,mod in plugins.found():"
    '''
    return _G.plugins.iteritems()