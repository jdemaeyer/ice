import logging


class DummyCamera(object):
    """Debug camera object that'll simply print what you tell it to do."""

    def log(self, msg, level = logging.INFO):
        self.logger.log(level, msg)

    def __init__(self, name = "Dummy", controlfocus = False, **kwargs):
        self.name = name
        self.logger = logging.getLogger(self.name)

    def release(self):
        self.log("Released")

    def retry_until_not_busy(self, cmd):
        cmd()

    def _get_widget(self, config_name):
        self.log("Requested widget: {}".format(config_name))
        return None, None

    def get_config(self, config_name):
        self.log("Requested config: {}".format(config_name))
        return None

    def set_config(self, config_name, value):
        self.log("Set config '{}' to '{}'".format(config_name, value))

    def get_event(self, timeout = 0):
        self.log("Getting event")
        return 0, None

    def wait_for_event(self, eventcode = 1, timeout = 10):
        self.log("Blocking until next {}".format(eventcode))
        return 0, None

    def enter_preview(self):
        self.log("Entering preview")
        self.in_preview = True

    def exit_preview(self):
        self.log("Exiting preview")
        self.in_preview = False

    def trigger(self):
        self.log("Triggered")
        self.in_preview = False

    def capture_filepath(self):
        # Enter preview mode so we won't trigger autofocus engine
        if self.controlfocus and not self.in_preview:
            self.enter_preview()
        self.log("Capturing with filepath")
        self.in_preview = False
        return None

    def get_filepath(self, camerafilepath):
        self.log("Downloading filepath")
        return None

    def capture(self, save_to = None):
        self.log("Capturing")
        return None

    def capture_preview(self, save_to = None):
        if not self.in_preview:
            self.enter_preview()
        self.log("Capturing preview")
        return None

    def _focusstep(self, step):
        if not self.in_preview:
            self.enter_preview()
        self.log("Focus step: {}".format(step))

    def focus(self, focusfunc = None):
        self.log("Focusing")
        return []

    def autofocus(self, contrast = False):
        if not self.controlfocus:
            logging.log(logging.ERROR, ("Cannot focus camera. Set "
                                    "Camera.controlfocus = True and switch lens"
                                    "to 'A' or 'A/M' mode"))
            return
        was_in_preview = self.in_preview
        if contrast:
            self.enter_preview()
        else:
            self.exit_preview()
        self.log("Autofocusing (contrast: {})".format(contrast))
        if was_in_preview:
            self.enter_preview()
        else:
            self.exit_preview()
