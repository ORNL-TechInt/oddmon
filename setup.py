from distutils.core import setup
import glob
import sys
plugins = glob.glob("metric*.py")

requires = [
        'pyzmq',
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
    version='0.1a1',
    author='Feiyi Wang',
    author_email='fwang2@ornl.gov',
    py_modules=['oddpub', 'oddsub','hostlist', 'lfs_utils'],
    scripts=['oddmon.py'],
    data_files=[ ('lib/oddmon', plugins),
                  ('lib/oddmon', ['oddmon.cfg.sample']),
                  ('share/doc/oddmon', ['README.md'])
                  ],
    classifiers=[
            'Development Status :: 3 - Alpha',
            'Intended Audience :: System Administrators',
            'Topic :: System :: Monitoring',
            'Programming Language :: Python :: 2',
            'Programming Language :: Python :: 2.6',
            'Programming Language :: Python :: 2.7',
      ],
    install_requires = requires,
    long_description=details
      )


