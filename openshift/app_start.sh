# This script will launch the monctl collector process.  It's expected
# to be called from the OpenShift container.  (Specifically, from the
# s2i-python-container package from the OpenShift catalog.)

# Not sure yet where the docker image actually stores the python interpreter.
# (Hopefully, it's in the path...)
$PYTHON=python

# Note: I'm assuming the current directory is the root of the git repo.  
#$PYTHON ./monctl aggregate --cfgfile openshift/oddmon-openshift.cfg -C -v
$PYTHON openshift/hello_world.py
