import setuptools

import glob
import sys

# plugins = glob.glob("metric*.py")

requires = [
        'pyzmq',
        'argparse']
if sys.version_info[:3] < (2,7,0):
    raise RuntimeError("This application requires Python 2.7+")

details="""
More details on the package
"""

setuptools.setup(name='oddmon',
    description="A distributed monitoring tool suite",
    url="http://github.com/ORNL-TechInt/oddmon",
    license="LGPL",
    version='0.1',
    author='Feiyi Wang',
    author_email='fwang2@ornl.gov',
    py_modules=['monctl', 'oddpub', 'oddsub','hostlist',
                'lfs_utils', 'daemon',
                'metric_ost_stats',
                'metric_ost_brw_stats'],
    entry_points={
        'console_scripts': [
            'monctl=monctl:main'
        ]
    },

    #             data_files=[ ('lib/oddmon', ['oddmon.cfg.sample']),
    #              ('share/doc/oddmon', ['README.md']),
    #            ('lib/oddmon', ['collector', 'aggregator'])
    #            ],
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


