from distutils.core import setup
import glob
import sys

plugins = glob.glob("metric*.py")

requires = [
        'setuptools',
        'argparse']
if sys.version_info[:3] < (2,5,0):
    raise RuntimeError("This application requires Python 2.6+")

details="""
More details on the package
"""

setup(name='oddmon',
      description="A distributed monitoring tool suite",
      url="http://github.com/fwang2/oddmon",
      license="LGPL",
      version='0.1',
      author='Feiyi Wang',
      author_email='fwang2@ornl.gov',
      py_modules=['hostlist', 'lfs_utils'],
      scripts=['odd_server.py','odd_client.py'],
      data_files=[ ('/usr/lib64/oddmon', plugins),
                  ('/etc/oddmon', ['oddmon.conf']),
                  ('/usr/share/doc/oddmon', ['README.md'])
                  ],
      install_requires=requires,
      long_description=details
      )


