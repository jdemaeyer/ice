import numpy as np
from IPython.core.debugger import Tracer; breakpoint = Tracer()

from ice import *


# TIME LISTS

# 20 seconds of 4 fps
#tl0 = np.arange(5000, 25000, 250)
# One minute of 1 fps
tl1 = np.arange(25000, 85000, 1000)
# Three minutes of 1/3 fps
tl2 = np.arange(85000, 265000, 3000)
# 25 minutes and 40 seconds of 1/10 fps
#tl3 = np.arange(265000, 1805000, 10000)
# 60 minutes of 1/10 fps
#tl3 = np.arange(265000, 3865000, 10000)
tl3 = np.arange(265000, 3865000 + 60*60000, 10000)

tl = list(np.concatenate((tl1, tl2, tl3)))
for i in range(len(tl)):
    tl[i] -= 25000

# NOTE DEBUG REMOVE
tl = range(0, 24*60*60*1000, 60000)
print "Total nr of images: {}".format(len(tl))


# CAMERAS
#cams = get_all_cameras()
from ice.debugging import DummyCamera
cams = [ DummyCamera("C0"), DummyCamera("C1") ]
#print "Nr of cameras: {}".format(len(cams))


# JOB MANAGER
jm = JobManager(cams, [tl] * len(cams))


# START CAPTURE
#jm.capture_all()


# DROP INTO SHELL
breakpoint()


