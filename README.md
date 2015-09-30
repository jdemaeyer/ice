ICE
===

ICE is remote control of DSLRs aimed at experimentalists. It allows fast
framerates at full resolution by avoiding USB transfer, instead saving pictures
to an SD card.


Usage
-----

Example usage can be found in `capture.py`. You can also use this script
directly: Run it with `python capture.py` and wait until you see a shell. Type
`jm.capture_all()` to start the capture process. If necessary, you can stop
capturing before all pictures have been taken with `jm.stop_all()`. 


Dependencies
------------

*   Mandatory:
    *   gphoto2
