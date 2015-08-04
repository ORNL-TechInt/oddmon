import setuptools

import glob
import sys

# plugins = glob.glob("metric*.py")

if sys.version_info[:3] < (2,6,0):
    raise RuntimeError("This application requires Python 2.6+")

details="""
More details on the package
"""

setuptools.setup(name='oddmon',
    description="A distributed monitoring tool suite",
    url="http://github.com/ORNL-TechInt/oddmon",
    license="LGPL",
    version='0.1',
    author='Feiyi Wang, Ross Miller, Jeremy Anantharaj',
    author_email='fwang2@ornl.gov, rgmiller@ornl.gov, anantharajjd@ornl.gov',
    py_modules=['monctl', 'oddpub', 'oddsub','hostlist', 'plugins',
                'lfs_utils', 'daemon',
                'metric_ost_stats', 'metric_ost_job_stats',
                'metric_ost_brw_stats', 'sql'],
    entry_points={
        'console_scripts': [
            'monctl=monctl:main'
        ]
    },

    data_files=[ ('/etc/oddmon', ['oddmon.cfg']),
                 ('share/doc/oddmon', ['README.md']),
                 ('/etc/init', ['oddmon_aggregator.conf','oddmon_collector.conf'])
               ],
    classifiers=[
            'Development Status :: 3 - Alpha',
            'Intended Audience :: System Administrators',
            'Topic :: System :: Monitoring',
            'Programming Language :: Python :: 2',
            'Programming Language :: Python :: 2.6',
            'Programming Language :: Python :: 2.7',
      ],
    long_description=details
      )


