#!/usr/bin/env python
# Copyright (c) 2018 roseengineering

from __future__ import print_function

from gnuradio import gr
from gnuradio import blocks
import osmosdr
import sys, struct, argparse
import numpy as np


def cast_stream(buf, byte=False, word=False, left=False):
    data = np.ndarray(shape=(len(buf)/4,), dtype='f', buffer=buf)
    if word:
        data = data * 32768
        buf = data.astype('h').tobytes()
    elif left:
        data = data * 32768 + 128
        buf = data.astype('B').tobytes()
    elif byte:
        data = data * 128 + 128
        buf = data.astype('B').tobytes()
    return buf


class queue_sink(gr.hier_block2):

    def __init__(self, options):
        item_size = gr.sizeof_gr_complex
        gr.hier_block2.__init__(self, "queue_sink",
            gr.io_signature(1, 1, item_size),
            gr.io_signature(0, 0, 0))
        self.qu = gr.msg_queue(0)
        message_sink = blocks.message_sink(item_size, self.qu, False)
        self.connect(self, message_sink)
		
    def next(self):
        msg = self.qu.delete_head()
        return msg.to_string()


class radio_stream(gr.top_block):

    def __init__(self, options):
        gr.top_block.__init__(self)
        self.options = options
        self.source = source = osmosdr.source(options['args'])
        self.sink = sink = queue_sink(options)
        self.connect(source, sink)

    def initialize(self):
        options = self.options
        source = self.source
        source.set_center_freq(int(options['freq'] or 100e6))
        if options['rate'] != None: source.set_sample_rate(options['rate'])
        if options['corr'] != None: source.set_freq_corr(options['corr'])
        if options['gain'] != None: source.set_gain(options['gain'])
        if options['auto'] != None: source.set_gain_mode(options['auto'])
  
    def print_ranges(self):
        source = self.source
        self.print_range('valid sampling rates', source.get_sample_rates())
        self.print_range('valid gains', source.get_gain_range())
        self.print_range('valid frequencies', source.get_freq_range())

    def print_status(self):
        source = self.source 
        print('rate = %d' % source.get_sample_rate(), file=sys.stderr)
        print('freq = %d' % source.get_center_freq(), file=sys.stderr)
        print('corr = %d' % source.get_freq_corr(), file=sys.stderr)
        print('gain = %d' % source.get_gain(), file=sys.stderr)
        print('auto = %s' % source.get_gain_mode(), file=sys.stderr)

    def print_range(self, name, r):
        print(name + ":", end="", file=sys.stderr)
        if r.empty():
            print(" <none>", file=sys.stderr)
            return
        for x in r:
            start = x.start()
            stop = x.stop()
            if start == stop: 
                print(" %d" % start, end="", file=sys.stderr)
            else:
                print(" %d-%d" % (start, stop), end="", file=sys.stderr)
        print(file=sys.stderr)

    def __iter__(self):
        return self.sink


parser = argparse.ArgumentParser()
parser.add_argument("--args", help="device arguments", default="")
parser.add_argument("--freq", help="center frequency (Hz)", type=float)
parser.add_argument("--rate", help="sample rate (Hz)", type=float)
parser.add_argument("--corr", help="freq correction (ppm)", type=float)
parser.add_argument("--gain", help="gain (dB)", type=float)
parser.add_argument("--auto", help="turn on automatic gain", action="store_true")
parser.add_argument("--word", help="signed word samples", action="store_true")
parser.add_argument("--left", help="left justified unsigned byte samples", action="store_true")
parser.add_argument("--float", help="32-bit float samples", action="store_true")
parser.add_argument("--host", help="host address", default="0.0.0.0")
parser.add_argument("--port", help="port address", type=int, default=1234)
args = parser.parse_args()

########################################

import select, socket


# 0x07: rtlsdr_set_testmode(dev, ntohl(cmd.param));
# 0x08: rtlsdr_set_agc_mode(dev, ntohl(cmd.param));
# 0x09: rtlsdr_set_direct_sampling(dev, ntohl(cmd.param));
# 0x0a: rtlsdr_set_offset_tuning(dev, ntohl(cmd.param));
# 0x0b: rtlsdr_set_xtal_freq(dev, ntohl(cmd.param), 0);
# 0x0c: rtlsdr_set_xtal_freq(dev, 0, ntohl(cmd.param));
# 0x0d: set_gain_by_index(dev, ntohl(cmd.param));

command_fmt = ">BI"
command_size = struct.calcsize(command_fmt)

def handle_command(source, data):
    command, param = struct.unpack(command_fmt, data)
    if command == 0x01:
        print('0x%02x set_center_freq: %s Hz' % (command, param), file=sys.stderr)
        source.set_center_freq(param)
    elif command == 0x02:
        print('0x%02x set_sample_rate: %s Hz' % (command, param), file=sys.stderr)
        source.set_sample_rate(param)
    elif command == 0x03:
        param = bool(param)
        print('0x%02x set_gain_mode: auto is %s' % (command, param), file=sys.stderr)
        source.set_gain_mode(param)
    elif command == 0x04:
        print('0x%02x set_gain: %s' % (command, param), file=sys.stderr)
        if param: 
            if not args.auto: source.set_gain(param)
        else: 
            print('     ignoring gains of 0', file=sys.stderr)
    elif command == 0x05:
        print('0x%02x set_freq_corr: %s' % (command, param), file=sys.stderr)
        source.set_freq_corr(param)
    elif command == 0x06:
        param = param & 0xffff
        print('0x%02x set_freq_corr: %s' % (command, param), file=sys.stderr)
        source.set_if_gain(param);
    else:
        print('0x%02x unimplemented: %s' % (command, param), file=sys.stderr)


# create socket
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.setblocking(0)  # set non-blocking mode

# bind socket and listen
server_address = (args.host, args.port)
server.bind(server_address)
server.listen(5)

# tell user
print('listening on %s port %s' % server_address, file=sys.stderr)


def close_connection(sock):
    print('closing %s:%s' % clients[sock], file=sys.stderr)
    outputs.remove(sock)
    inputs.remove(sock)
    del readbuf[sock]
    del clients[sock]
    sock.close()
    print('%d remaining connections' % len(outputs), file=sys.stderr)


def open_connection(sock):
    conn, client_address = sock.accept()
    print('new connection from %s:%s' % client_address, file=sys.stderr)
    conn.setblocking(0)
    inputs.append(conn)
    outputs.append(conn)
    readbuf[conn] = ""
    clients[conn] = client_address
    print('%d open connections' % len(outputs), file=sys.stderr)


# select
inputs = [ server ]  # for reading
outputs = []         # for writing
readbuf = {}
clients = {}

# start stream
stream = radio_stream(args.__dict__)
stream.print_ranges()
stream.initialize()
stream.print_status()
stream.start()

args.byte = not args.left and not args.word and not args.float

for data in stream:

    data = cast_stream(data, byte=args.byte, word=args.word, left=args.left)
    readable, writable, exceptional = select.select(inputs, outputs, outputs, 0)

    for sock in outputs:
        if sock in exceptional:
            print('exception %s:%s' % clients[sock], file=sys.stderr)
            close_connection(sock)

    for sock in outputs:
        if sock in writable:
            try:
                sock.send(data)
            except socket.error:
                print('bad write %s:%s' % clients[sock], file=sys.stderr)
                close_connection(sock)

    for sock in inputs:
        if sock in readable:
            if sock is server:
                open_connection(sock)
            else:
                data = sock.recv(command_size - len(readbuf[sock]))
                if not data:
                    print('bad read %s:%s' % clients[sock], file=sys.stderr)
                    close_connection(sock)
                else:
                    readbuf[sock] += data
                    if len(readbuf[sock]) == command_size:
                        if sock is outputs[0]:
                            handle_command(stream.source, readbuf[sock])
                        readbuf[sock] = ""



