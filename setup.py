from distutils.core import setup
import glob

plugins = glob.glob("metric*.py")

setup(name='oddmon',
      version='0.1',
      author='Feiyi Wang',
      author_email='fwang2@ornl.gov',
      py_modules=['hostlist', 'lfs_utils'],
      scripts=['mond.py','aggrd.py'],
      data_files=[ ('/usr/lib64/oddmon', plugins),
                  ('/etc/oddmon', ['oddmon.conf']),
                  ('/usr/share/doc/oddmon', ['README.md'])
                  ],
      requires=['argparse']
      )


