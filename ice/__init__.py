"""
Image Capturing for Experimentalists.

Author:        Jakob de Maeyer <jakobdm1@gmail.com>
Last Changed:  24 November 2014
"""

import threading
import collections
import time
import datetime
import math
import random
import os.path
from PIL import Image

import logging
logging.basicConfig(
    format='%(levelname)s: %(name)s: %(asctime)s: %(message)s', level=logging.INFO)

import gphoto2 as gp


def gp_logging():
    gp.check_result(gp.use_python_logging())


def random_nonexisting_filename():
    while True:
        tempfile = ".ICE_temp_{:5d}".format(random.randint(0, 99999))
        if not os.path.isfile(tempfile):
            return tempfile


def get_all_cameras():
    # Ugh, C libraries >.<
    # Get all available ports
    portinfolist = gp.check_result(gp.gp_port_info_list_new())
    gp.check_result(gp.gp_port_info_list_load(portinfolist))
    # Get all available cameras and a string of their port
    context = gp.gp_context_new()
    camlist = gp.check_result(gp.gp_camera_autodetect(context))
    cameralist = []
    for i in range(camlist.count()):
        camname = camlist.get_name(i)
        camport = camlist.get_value(i)
        # Find port info for this camera
        portindex = portinfolist.lookup_path(camport)
        portinfo = portinfolist.get_info(portindex)
        # Create camera object and associate with given port
        cam = gp.check_result(gp.gp_camera_new())
        gp.check_result(gp.gp_camera_set_port_info(cam, portinfo))
        myCamera = Camera("{} ({})".format(camname, camport), cam, context)
        cameralist.append(myCamera)
    return cameralist


class Camera(object):

    def __init__(self, name = "My Camera", camera = None, context = None,
            controlfocus = False):
        self.name = name
        if context is None:
            self.context = gp.gp_context_new()
        else:
            self.context = context
        if camera is None:
            self.camera = gp.check_result(gp.gp_camera_new());
        else:
            self.camera = camera
        self.logger = logging.getLogger(self.name)
        self.controlfocus = controlfocus
        self.in_preview = False
        gp.check_result(gp.gp_camera_init(self.camera, self.context))

    def log(self, msg, level = logging.INFO):
        self.logger.log(level, msg)

    def release(self):
        self.log("Released")
        gp.check_result(gp.gp_camera_exit(self.camera, self.context))

    def retry_until_not_busy(self, cmd):
        while True:
            try:
                cmd()
                break
            except gp.GPhoto2Error as e:
                if e.code == gp.GP_ERROR_CAMERA_BUSY:
                    continue
                raise

    def _get_widget(self, config_name):
        config = gp.check_result(
                    gp.gp_camera_get_config(self.camera, self.context))
        widget = gp.check_result(
                    gp.gp_widget_get_child_by_name(config, config_name))
        return config, widget

    def get_config(self, config_name):
        config, widget = self._get_widget(config_name)
        return gp.check_result(gp.gp_widget_get_value(widget))

    def set_config(self, config_name, value):
        self.log("Setting '{}' to '{}'".format(config_name, value))
        config, widget = self._get_widget(config_name)
        gp.check_result(gp.gp_widget_set_value(widget, value))
        gp.check_result(
                gp.gp_camera_set_config(self.camera, config, self.context))
        self.log("Set '{}' to '{}'".format(config_name, value))

    def get_event(self, timeout = 0):
        return gp.check_result(
                gp.gp_camera_wait_for_event(self.camera, timeout, self.context))

    def wait_for_event(self, eventcode = gp.GP_EVENT_TIMEOUT, timeout = 10):
        """Block until next event"""
        self.log("Waiting for event: {}".format(eventcode))
        code = -1
        while code != eventcode:
            code, data = self.get_event(timeout = timeout)
        return code, data

    def enter_preview(self):
        self.log("Entering preview")
        self.set_config('viewfinder', 1)
        self.in_preview = True

    def exit_preview(self):
        self.log("Exiting preview")
        self.set_config('viewfinder', 0)
        self.in_preview = False

    def trigger(self):
        self.log("Triggering")
        gp.check_result(gp.gp_camera_trigger_capture(self.camera, self.context))
        self.log("Triggered")
        self.in_preview = False

    def capture_filepath(self):
        self.log("Capturing")
        # Enter preview mode so we won't trigger autofocus engine
        if self.controlfocus and not self.in_preview:
            self.enter_preview()
        camerafilepath = gp.check_result(gp.gp_camera_capture(
                self.camera,
                gp.GP_CAPTURE_IMAGE,
                self.context))
        self.in_preview = False
        return camerafilepath

    def get_filepath(self, camerafilepath):
        self.log("Downloading")
        camerafile = gp.CameraFile()
        camerafile = gp.check_result(gp.gp_camera_file_get(
                self.camera,
                camerafilepath.folder,
                camerafilepath.name,
                gp.GP_FILE_TYPE_NORMAL,
                self.context))
        return camerafile

    def capture(self, save_to = None):
        self.set_config('capturemode', 'Single Shot')
        camerafilepath = self.capture_filepath()
        camerafile = self.get_filepath(camerafilepath)
        if save_to is not None:
            camerafile.save(save_to)
        return camerafile

    def capture_preview(self, save_to = None):
        self.log("Capturing preview")
        if not self.in_preview:
            self.enter_preview()
        camerafile = gp.check_result(gp.gp_camera_capture_preview(
                self.camera,
                self.context))
        if save_to is not None:
            camerafile.save(save_to)
        return camerafile

    def _focusstep(self, step):
        self.log("Single focus step: {}".format(step))
        if not self.in_preview:
            self.enter_preview()
        try:
            self.set_config('manualfocusdrive', step)
        except gp.GPhoto2Error as e:
            if e.code == -113:
                # Camera could not complete operation = At focus limit
                self.log("Focus limit reached")
            raise

    def _cf_to_img(self, cf):
        # TODO: Find a way to load image directly (w/o saving)
        tempfilename = random_nonexisting_filename()
        cf.save(tempfilename)
        img = Image.open(tempfilename)
        os.remove(tempfilename)
        return img

    def focus(self, focusfunc = None):
        # TODO: Implement "circa focus distance" and range within to focus
        self.log("Focusing")
        if not self.controlfocus:
            self.log(("Cannot focus camera. Set Camera.controlfocus = True and"
                      "switch lens to 'A' or 'A/M' mode"), logging.ERROR)
            return
        self.enter_preview()
        # Go to end of focus range
        while True:
            try:
                self._focusstep(-10000)
            except gp.GPhoto2Error as e:
                if e.code == -113:
                    # At focus limit
                    break
                else:
                    raise
        focuslist = list()
        for i in range(25):
            self._focusstep(200)
            focusval = focusfunc(self._cf_to_img(self.capture_preview()))
            focuslist.append((i*200, focusval))
            print "{} {}".format(*focuslist[-1])
        self.exit_preview()
        # TODO: Examine around max with real images, move to max
        return focuslist

    def autofocus(self, contrast = False):
        self.log("Autofocusing")
        if not self.controlfocus:
            self.log(("Cannot focus camera. Set Camera.controlfocus = True and"
                      "switch lens to 'A' or 'A/M' mode"), logging.ERROR)
            return
        was_in_preview = self.in_preview
        if contrast:
            self.enter_preview()
        else:
            self.exit_preview()
        self.set_config('autofocusdrive', 1)
        if was_in_preview:
            self.enter_preview()
        else:
            self.exit_preview()



class WorkUnit(object):

    WAITING = 0
    SETUP = 1
    RUNNING = 2
    CAPTURED = 3
    DOWNLOADED = 4

    def __init__(self, camera, nr_of_images = 1, fps = 0):
        self.camera = camera
        self.nr_of_images = nr_of_images
        self.wanted_fps = float(fps)  # Avoid integer divison in setup()
        self.real_fps = None
        self.status = self.WAITING
        self.images_shot = 0
        self.images_downloaded = 0
        self._filepaths = None

    def __unicode__(self):
        return u"{} shots at {} fps".format(self.nr_of_images, self.wanted_fps)

    def setup(self):
        """Set camera configuration for this work unit"""
        # Save to card
        self.camera.set_config('capturetarget', "Memory card")
        # Figure out "burst setting" from fps
        if self.wanted_fps > 4: 
            self.real_fps = 4.5
            self.camera.set_config('capturemode', 'Burst')
            # Wanted FPS might be higher than achievable FPS, reduce number of
            # images to keep total time
            logging.log(logging.WARNING, ("Cannot get FPS higher than 4.5, "
                                          "reducing number of images."))
            self.nr_of_images = round(self.nr_of_images / self.wanted_fps
                                                        * self.real_fps)
            self.camera.set_config('burstnumber', self.nr_of_images)
        elif self.wanted_fps >= 1:
            self.real_fps = round(self.wanted_fps)
            self.camera.set_config('capturemode', 'Continuous Low Speed')
            self.camera.set_config('shootingspeed', 
                                   '{:.0f} fps'.format(self.real_fps))
            self.nr_of_images = round(self.nr_of_images / self.wanted_fps
                                                        * self.real_fps)
            self.camera.set_config('burstnumber', self.nr_of_images)
        else:
            self.real_fps = self.wanted_fps
            self.camera.set_config('capturemode', 'Single Shot')
        self.status = self.SETUP

    def trigger(self):
        self.status = self.RUNNING
        self.camera.trigger()

    def download(self):
        raise NotImplementedError

    def download_one(self):
        raise NotImplementedError


class Job(threading.Thread):

    WAITING = 0
    PAUSED = 1
    RUNNING = 2
    ALL_TRIGGERED = 3
    CAPTURED = 4
    DOWNLOADED = 5
    STOPPED = 6

    def __init__(self, camera, timelist):
        super(Job, self).__init__()
        self.camera = camera
        self.timelist = timelist
        self.inittime = datetime.datetime.now()
        self.work_units = self.list_to_units(self.timelist)
        self.work_units_abstime = None
        self.status = self.WAITING
        self.statuschange = threading.Event()
        self.start()

    def _set_status(self, newstatus):
        self.status = newstatus
        self.statuschange.set()

    @staticmethod
    def _dt_to_fps(dt):
        """Converts an interval between two frames (in ms) into fps.""" 
        fps = 1000. / dt
        if fps > 4:
            fps = 4.5
        elif fps > 1:
            fps = math.ceil(fps)
        return fps

    def list_to_units(self, timelist):
        """Convert a list of ms timestamps into work units.

        IMPORTANT:  This function is not very smart. It will not produce what
                    you want if you feed it FPS higher than 4.5, and it will be
                    inaccurate if you feed it time differences corresponding to
                    non-integer FPS between 1 and 4 (everything below 1, i.e.
                    every dt > 1000 ms is fine).
        """
        units = collections.deque()
        thistime = None
        thisfps = None
        for t in timelist:
            if thistime is None:
                # First shot in a WU
                thistime = t
                thisshots = 1
            elif thisfps is None:
                # (Possible) second shot in a WU
                thisfps = Job._dt_to_fps(t - thistime)
                lasttime = t
                thisshots = 2
                if thisfps <= 1:
                    # Previous shot more than 1000 ms away, make single shot WU
                    units.append( (thistime, 
                                   WorkUnit(self.camera, 1, 0)) )
                    thistime = t
                    thisshots = 1
                    thisfps = None
                    continue
                else:
                    thisshots = 2
            else:
                # (Possible) third and later shots in a WU
                # thistime, lasttime, thisshots, thisfps are set at this point
                newfps = Job._dt_to_fps(t - lasttime)
                lasttime = t
                if newfps == thisfps:
                    thisshots += 1
                else:
                    # Start new WU
                    units.append( (thistime,
                                   WorkUnit(self.camera, thisshots, thisfps)) )
                    thistime = t
                    thisshots = 1
                    thisfps = None
        # There is an unfinished WU
        units.append( (thistime, WorkUnit(
                                    self.camera,
                                    thisshots,
                                    thisfps if thisshots > 1 else 0
                                    )) )
        return units

    def shift_units(self, timedelta):
        self.work_units_abstime = collections.deque(
                [ (dt + timedelta, wu)
                  for wu in self.work_units_abstime ])

    def run(self):
        # Our simple state machine
        while True:
            if self.status == self.RUNNING:
                self._running()
            elif self.status == self.STOPPED:
                return
            else:
                self._wait_for_statuschange()

    def _running(self):
        try:
            this_time, this_wu = self.work_units_abstime[0]
        except IndexError:
            # Done :)
            self._set_status(self.ALL_TRIGGERED)
            return
        # Wait until 150 ms before this_time, return on statuschange
        try:
            if self.statuschange.wait(
                  (this_time - datetime.datetime.now()).total_seconds() - .15):
                return
        except IOError:
            # TODO: Behind schedule!
            pass
        self.camera.retry_until_not_busy(this_wu.setup)
        try:
            time.sleep((this_time - datetime.datetime.now()).total_seconds())
        except IOError:
            # TODO: Behind schedule!
            pass
        self.camera.retry_until_not_busy(this_wu.trigger)
        # TODO: Check for camera events?
        # Remove the WU we just processed from queue
        self.work_units_abstime.popleft()

    def _wait_for_statuschange(self):
        self.statuschange.wait()
        self.statuschange.clear()

    def capture(self):
        self.starttime = datetime.datetime.now()
        self.work_units_abstime = collections.deque(
                [ (self.starttime + datetime.timedelta(milliseconds = dt),
                   wu)
                   for dt, wu in self.work_units ])
        self._set_status(self.RUNNING)

    def pause(self):
        self.pausetime = datetime.datetime.now()
        self._set_status(self.PAUSED)

    def resume(self, skip_missed = False):
        self.resumetime = datetime.datetime.now()
        if skip_missed:
            # Delete all WUs that should've been triggered already
            while True:
                if self.work_units_abstime[0][0] < resumetime:
                    self.work_units_abstime.popleft()
        else:
            self.shift_units(self.resumetime - self.pausetime)
        self._set_status(self.RUNNING)

    def stop(self):
        self._set_status(self.STOPPED)


class JobManager(object):

    WAITING = 0
    PAUSED = 1
    RUNNING = 2
    CAPTURED = 3
    DOWNLOADED = 4
    STOPPED = 5

    def __init__(self, cameras, timelists):
        if len(cameras) != len(timelists):
            raise ValueError("Different number of cameras and timelists")
        self.jobs = [ Job(c, t) for c, t in zip(cameras, timelists) ]
        self.status = self.WAITING

    def capture_all(self):
        for j in self.jobs:
            print "CAPTURING"
            j.capture()
        self.status = self.RUNNING

    def pause_all(self):
        for j in self.jobs:
            j.pause()
        self.status = self.PAUSED

    def resume_all(self, skip_missed = False):
        for j in self.jobs:
            j.resume(skip_missed)
        self.status = self.RUNNING

    def stop_all(self):
        for j in self.jobs:
            j.stop()
        self.status = self.STOPPED

