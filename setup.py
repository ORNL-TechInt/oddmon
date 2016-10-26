import setuptools
import platform
import sys

def get_distro():
    '''
    Returns a tuple consisting of the distro name (string) and major
    number (int)
    '''
    distro, version = platform.dist()[0:2]
    majorVersion = int(version.split('.')[0])
    return (distro, majorVersion)

# Do some sanity checks on the distribution we're packaging for
(distro, version) = get_distro()
if not (distro == "redhat" or
        distro == "centos"):
    raise RuntimeError("Unknown Linux distribution: '%s'. " % distro +
                       "We can only build packages for RedHat Enterprise " +
                       "Linux and CentOS.")

if version < 6:
    raise RuntimeError("Linux distribution too old.  We need at least v6.")

if version > 7:
    raise RuntimeError("Linux distribution too new.  v7 is the latest " +
                       "currently supported.")

if sys.version_info[:3] < (2,6,0):
    raise RuntimeError("This application requires Python 2.6+")

details="""
More details on the package
"""

# Choose the appropriate startup script to include in the package
if version == 7:
    # Use the systemd script
    startup_tuple = ('/usr/lib/systemd/system', ['oddmon_aggregator.service','oddmon_collector.service'])
else:
    # Use the upstart script
    startup_tuple = ('/etc/init', ['oddmon_aggregator.conf','oddmon_collector.conf'])


setuptools.setup(name='oddmon',
    description="A distributed monitoring tool suite",
    url="http://github.com/ORNL-TechInt/oddmon",
    license="LGPL",
    version='1.6.0',
    author='Feiyi Wang, Ross Miller, Jeremy Anantharaj',
    author_email='fwang2@ornl.gov, rgmiller@ornl.gov, anantharajjd@ornl.gov',
    packages = ['oddmon', 'oddmon.metric_plugins'],
    # Note: metrics isn't technically a package (it has no __init__.py), but
    # it is where all of the plugins live and we definitely want to include
    # them in the distribution...
    # ToDo: explore using setuptools.findpackages()
    scripts = ['monctl.py'],
    data_files=[ ('/etc/oddmon', ['oddmon.cfg.sample']),
                 ('share/doc/oddmon', ['README.md']),
                 startup_tuple
               ],
    classifiers=[
            'Development Status :: 5 - Production/Stable',
            'Intended Audience :: System Administrators',
            'Topic :: System :: Monitoring',
            'Operating System :: POSIX :: Linux',
            'Programming Language :: Python :: 2',
            'Programming Language :: Python :: 2.6',
            'Programming Language :: Python :: 2.7',
      ],
    # Work around distutils' lack of "%config(noreplace)" support by using a
    # post install scriptlet to copy /etc/oddmon/oddmon.cfg.sample over to
    # /etc/oddmon/oddmon.cfg *IF* the latter file doesn't already exist.
    # We could also add a "post_uninstall" option if we need it.
    options = { 'bdist_rpm':{'post_install' : 'post_install'}},
    long_description=details
      )


