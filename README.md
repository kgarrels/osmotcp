
osmotcp.py
==========

This repo provides a Python 2.7 gnuradio script named osmotcp.py.
The script serves samples from any gr-osmosdr supported device
over TCP/IP.  The server supports the RTL\_TCP protocol.  In addition
the output stream can be configured to send either signed words or floating point
IQ samples -- not just the default unsigned byte IQ samples of RTL\_TCP.

Usage for osmotcp.py is as follow: 

    $ python osmotcp.py -h

    usage: osmotcp.py [-h] [--args ARGS] [--freq FREQ] [--rate RATE] [--corr CORR]
                      [--gain GAIN] [--auto] [--word] [--left] [--float]
                      [--host HOST] [--port PORT]

    optional arguments:
      -h, --help   show this help message and exit
      --args ARGS  device arguments
      --freq FREQ  center frequency (Hz)
      --rate RATE  sample rate (Hz)
      --corr CORR  freq correction (ppm)
      --gain GAIN  gain (dB)
      --auto       turn on automatic gain
      --word       signed word samples
      --left       left justify samples
      --float      32-bit float samples
      --host HOST  host address
      --port PORT  port address

If you get a value out of range error, try running the program again.

Here is screenshot of SDRTouch connected to osmotcp serving
samples from "rtl=0"

![Screenshot](screenshot.png)

- Copyright 2018 (c) roseengineering
