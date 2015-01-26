from distutils.core import setup
import glob

plugins = glob.glob("plugins/*.py")

setup(name='oddmon',
      version='0.1',
      author='Feiyi Wang',
      author_email='fwang2@ornl.gov',
      py_modules=['hostlist'],
      scripts=['mond.py','aggrd.py'],
      data_files=[ ('/usr/lib64/oddmon', plugins),
                  ('/etc/oddmon', ['oddmon.conf']),
                  ('/usr/share/doc/oddmon', ['README.md'])
                  ]
      )


