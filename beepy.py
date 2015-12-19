#!/usr/bin/env python
# encoding: utf8

# Copyright (c) 2012-2015 Raphaël Bois Rousseau <virtualdust@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software  and associated  documentation  files (the  "Software"), to
# deal in the Software without  restriction, including  without limitation the
# rights to use, copy, modify, merge,  publish, distribute, sublicense, and/or
# sell copies of the Software,  and to permit persons  to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice  and this permission notice  shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED  "AS IS", WITHOUT WARRANTY  OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING  BUT NOT  LIMITED TO THE  WARRANTIES OF  MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND  NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR  COPYRIGHT  HOLDERS BE  LIABLE FOR  ANY CLAIM,  DAMAGES  OR OTHER
# LIABILITY,  WHETHER IN AN  ACTION OF  CONTRACT, TORT  OR OTHERWISE,  ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

import struct
import math
import sys
TWO_PI = 2 * math.pi

class BeepyParseError(Exception):
  pass

class OptionableMeta(type):
  def __new__(cls, name, bases, cdict):
    t = type.__new__(cls, name, bases, cdict)
    if name not in ('Optionable', 'OptionableBase') and getattr(t, '__optionables__', None) is None:
      t.__optionables__ = dict()
    return t

if sys.version_info >= (3,):
  exec("class OptionableBase(object, metaclass=OptionableMeta): pass")
else:
  class OptionableBase(object):
    __metaclass__ = OptionableMeta

class Optionable(OptionableBase):
  __optgroupname__ = None
  __optgroupdesc__ = None
  # Tuple of options in the form:
  # ( ((args, ...), dict(kwargs=...)), ... )
  # each pair of 'args', 'kwargs' is passed as is to the optparse add_option()
  # method.
  #
  __options__ = None

  @classmethod
  def register(cls, name):
    def _optionable(_cls):
      cls.__optionables__[name] = _cls
      return _cls
    return _optionable

  @classmethod
  def getClass(cls, name):
    return cls.__optionables__.get(name, None)

  @classmethod
  def listAll(cls):
    a = list(cls.__optionables__.keys())
    a.sort()
    return a

  @classmethod
  def setupOptionsAll(cls, argparser):
    for o in cls.listAll():
      cls.__optionables__[o].setupOptions(argparser)

  @classmethod
  def setupOptions(cls, argparser):
    if not cls.__options__:
      return

    groupname = cls.__optgroupname__
    if not groupname:
      groupname = "%s options" % cls.__name__

    from optparse import OptionGroup
    group = OptionGroup(argparser, groupname, cls.__optgroupdesc__)
    for args, kwargs in cls.__options__:
      group.add_option(*args, **kwargs)
    argparser.add_option_group(group)


class Output(Optionable):
  def __init__(self, options):
    if self.__class__ is Output:
      raise NotImplementedError("Abstract class: Must be subclassed.")
    self.options = options

  def clear(self):
    pass
  def pushnote(self, notedata):
    raise NotImplementedError("pushnote")

  def runcommand(self, *cmdargs):
    import subprocess
    try:
      subprocess.call(cmdargs)
    except KeyboardInterrupt:
      pass

  def prerun(self):
    pass
  def run(self):
    pass
  def postrun(self):
    pass


class Parser(Optionable):
  def __init__(self, options):
    if self.__class__ is Parser:
      raise NotImplementedError("Abstract class: Must be subclassed.")
    self.options = options
    self.reset()

  def reset(self):
    self.output_notes = []
    self.cnote = {}
    return self.cnote

  def flushnote(self):
    self.output_notes.append(self.cnote)
    self.cnote = {}
    return self.cnote

  def parse(self, data):
    raise NotImplementedError()

  def feed(self, output):
    for n in self.output_notes:
      output.pushnote(n)


@Output.register('dummy')
class DummyOutput(Output):
  """ Dummy output for debug """
  def __init__(self, options):
    super(DummyOutput, self).__init__(options)
    self.debuginfo = []

  def clear(self):
    self.debuginfo = []
  def pushnote(self, notedata):
    if notedata:
      self.debuginfo.append("%r" % notedata)

  def prerun(self):
    if self.options.debug:
      import sys
      sys.stderr.write("\n".join(self.debuginfo)+"\n")


@Output.register('beep')
class BeepOutput(Output):
  """ Generate a 'beep' command and run it. """
  __optgroupname__ = "Beep Output Options"
  __options__ = (
      ( ('--beep',),
        dict(
          dest="beepapp", default='beep',
          help="Path to the beep executable. Default to 'beep' (PATH lookup)."
        )
      ),
      ( ('--beep-print',),
        dict(
          action="store_true", dest="beepprint", default=False,
          help="Print the generated beep command to standard output"
        )
      ),
    )

  def __init__(self, options):
    super(BeepOutput, self).__init__(options)
    import shutil
    if hasattr(shutil, 'which'):
      if not shutil.which(self.options.beepapp):
        raise RuntimeError("Beep program %r not found." % self.options.beepapp)
    self.beepargs = []

  def clear(self):
    self.beepargs = []
  def pushnote(self, notedata):
    f = notedata.get('frequency')
    l = notedata.get('length')
    D = notedata.get('pause')
    if ( f is not None and l is not None ) or D is not None:
      if self.beepargs:
        self.beepargs.append('-n')
      if f and l:
        self.beepargs.extend(['-f', '%.3f'%f, '-l', '%.3f'%l])
      else:
        self.beepargs.extend(['-f', '1', '-l', '0'])
      if D is not None:
        self.beepargs.extend(['-D', '%.3f'%D])

  def prerun(self):
    if self.options.beepprint:
      print(self.options.beepapp+" "+" ".join(self.beepargs))

  def run(self):
    self.runcommand(self.options.beepapp, *self.beepargs)


@Output.register('evdev')
class EvdevOutput(Output):
  """ Write directly to the speaker's input device. """
  __optgroupname__ = "Evdev Output Options"
  __options__ = (
      ( ('--evdev',),
        dict(
          dest="evdev", default='/dev/input/by-path/platform-pcspkr-event-spkr',
          help="The speaker event device to use.\n[default: /dev/input/by-path/platform-pcspkr-event-spkr]"
        )
      ),
    )

  EV_SND = 0x12
  SND_TONE = 0x02

  def __init__(self, options):
    super(EvdevOutput, self).__init__(options)

    import os
    try:
      fd = os.open(self.options.evdev, os.O_WRONLY)
      os.close(fd)
    except OSError:
      import sys
      t, e, tb = sys.exc_info()
      raise RuntimeError("Can't open device %r for writting: %s" % (self.options.evdev, e))

    self.rundata = []

  def clear(self):
    self.rundata = []
  def pushnote(self, notedata):
    f = notedata.get('frequency')
    l = notedata.get('length')
    p = notedata.get('pause')

    if ( f is None or l is None ) and p is None:
      return

    noteinfo = [None, None]
    if f and l:
      import struct
      noteinfo[0] = (
          struct.pack('@qqHHi', 0, 0, self.EV_SND, self.SND_TONE, int(f)),
          l/1000.0,
          struct.pack('@qqHHi', 0, 0, self.EV_SND, self.SND_TONE, 0),
          )
    if p:
      noteinfo[1] = p/1000.0
    self.rundata.append(noteinfo)

  def prerun(self):
    if self.options.debug:
      import sys
      sys.stderr.write("\n".join(map(lambda d:'%r'%d, self.rundata))+"\n")

  def run(self):
    import time, os
    fd = os.open(self.options.evdev, os.O_WRONLY)
    for n, p in self.rundata:
      if n:
        start, length, end = n
        try:
            os.write(fd, start)
            time.sleep(length)
        finally:
            # Prevent the sound to play forever in case of keyboard
            # interruption, for instance.
            os.write(fd, end)
      if p:
        time.sleep(p)
    os.close(fd)


@Output.register('pcm')
class PCMOutput(Output):
  """ Generate raw PCM data. """
  __optgroupname__ = "PCM Output Options"
  __options__ = (
      ( ('--pcm-samplerate',),
        dict(
          dest="pcm_sr", type=int, default=48000,
          help="Sample rate of raw data sent to sox"
        )
      ),
      ( ('--pcm-output',),
        dict(
          dest="pcm_out", default="-",
          help="Target file for pcm output (defaults to standard output)"
        )
      ),
    )

  def __init__(self, options, output=None):
    super(PCMOutput, self).__init__(options)
    self.samplerate = self.options.pcm_sr
    self.output = output
    self.rundata = []

  def clear(self):
    self.rundata = []
  def square(self, out, frequency, length, ampl = 2**12):
    sr = self.samplerate
    samples = math.ceil(sr * length)
    x = 0.0
    while x < samples:
      y = math.sin(TWO_PI * frequency * (x / sr))
      out.write(struct.pack('<h', ampl * (y >= 0 and 1 or -1)))
      x += 1.0
  def silence(self, out, length):
    sr = self.samplerate
    samples = math.floor(self.samplerate * length)
    x = 0.0
    while x < samples:
      out.write(struct.pack('<h', 0))
      x += 1.0
  def pushnote(self, notedata):
    f = notedata.get('frequency')
    l = notedata.get('length')
    D = notedata.get('pause')
    if ( f is not None and l is not None ) or D is not None:
      if f and l:
        self.rundata.append((self.square, (f, l/1000.0)))
      if D is not None:
        self.rundata.append((self.silence, (D/1000.0,)))
  def run(self):
    output = self.options.pcm_out if self.output is None else self.output
    if isinstance(output, str):
      if output == '-':
        # We need to write binary data to stdout:
        # - python3: sys.stdout.buffer
        # - python2: sys.stdout
        output = getattr(sys.stdout, 'buffer', sys.stdout)
        outclose = False
      else:
        output = open(output, 'wb')
        outclose = True
    else:
      outclose = False

    for gen, args in self.rundata:
      gen(output, *args)

    if outclose:
      output.close()



@Parser.register('qb')
class QBParser(Parser):
  "Parse Quick Basic PLAY data"
  def __init__(self, options):
    super(QBParser, self).__init__(options)

    # Init diatonic scale offsets
    scale = dict(
      c = 1,
      d = 3,
      e = 5,
      f = 6,
      g = 8,
      a = 10,
      b = 12
    )
    # Add semitones
    for n in "abcdefg":
      scale[n+'-'] = scale[n] - 1
      scale[n+'+'] = scale[n] + 1
    self.scale = scale

    # Init notes frequencies from C0- to B8+
    coeff=2.0 ** (1.0/12)
    notes = []
    for a in range(-1, 12 * 9 + 2):
      notes.append(440.0 * coeff ** float(a - 57))
    self.notes = notes

  def reset(self):
    # Defaults (same as QuickBasic)
    self.octave = 4
    self.tempo = 120.0
    self.note_type = 4
    self.note_duration = 7.0 / 8.0

    return super(QBParser, self).reset()

  def get_durations(self, dots):
    """ Get the duration in milliseconds, of the note and the post delay. """
    
    l = 4.0 * 60000.0 / (self.tempo * self.note_type)
    # each dot add half the duration of the previously added duration.
    ne = l / 2.0
    for i in range(dots):
      l += ne
      ne = ne / 2.0
    duration = self.note_duration
    return (duration * l, max(0.0, (1.0 - duration) * l))

  def parse(self, data):
    cnote = self.reset()

    data = data.lower() + " " # to handle EOF effortlessly.
    c = 0 # current position
    n = 1 # current line
    loffset = -1 # ofset, in characters, in the current line

    def loc():
      return "(line %d, column %d)" % (n, c - loffset)
    def err(s):
      raise BeepyParseError("%s %s" % (s, loc()))

    try:
      while True:
        x = data[c]
        c += 1
        if x == ";": # Extension: comments
          while data[c] != "\n":
            c += 1
          continue
        if x in " \t\r":
          continue
        if x == "\n":
          loffset = c - 1
          n += 1
          continue
        if x == "m":
          x = data[c]
          c += 1
          if x == "s":
            self.note_duration = 3.0/4.0
          elif x == "n":
            self.note_duration = 7.0/8.0
          elif x == "l":
            self.note_duration = 1.0
          elif x in "fb":
            continue
          else:
            err("Unknown character sequence '%s'" % ('m'+x))
        elif x in "oltp":
          v = ""
          while data[c] in "0123456789":
            v += data[c]
            c += 1
          if not v:
            err("Expected number after '%s'" % x)
          v = int(v)
          if x == "o":
            self.octave = min(8, max(0, v))
          elif x == "l":
            self.note_type = min(64, max(1, v))
          elif x == "t":
            self.tempo = float(min(255, max(32, v)))
          elif x == "p":
            dots = 0
            while data[c] == ".":
              dots += 1
              c += 1
            d, p = self.get_duration(dots)
            cnote['pause'] = cnote.get('pause', 0.0) + d + p
        elif x == ">":
          self.octave = min(8, self.octave + 1)
        elif x == "<":
          self.octave = max(0, self.octave - 1)
        elif x in "abcdefg":
          cnote = self.flushnote()
          cnote['symbolic'] = "%s%d" % (x, self.octave)
          if data[c] in "#+-":
            alt = data[c]
            if alt == '#':
              alt = '+'
            x += alt
            cnote['symbolic'] += alt
            c += 1
          dots = 0
          while data[c] == ".":
            dots += 1
            c += 1
          d, p = self.get_durations(dots)
          cnote['frequency'] = self.notes[12 * self.octave + self.scale[x]]
          cnote['length'] = d
          if p > 0.0:
            cnote['pause'] = p
        else:
          err("Unknown character '%s'" % x)
    except IndexError:
      pass
    self.flushnote()


class Beepy(object):
  """ A class to convert QuickBasic music to the provided output """
  def __init__(self, options):
    self.options = options

    outputCls = Output.getClass(options.output)
    if outputCls is None:
      raise RuntimeError("Unknown output %r" % options.output)

    parserCls = Parser.getClass(options.parser)
    if parserCls is None:
      raise RuntimeError("Unknown parser %r" % options.parser)

    self.output = outputCls(options)
    self.parser = parserCls(options)

  def clear(self):
    self.output.clear()
    self.parser.reset()

  def parse(self, data):
    self.parser.parse(data)
    self.parser.feed(self.output)

  def run(self, inputdata=None):
    if inputdata:
      self.parse(inputdata)

    self.output.prerun()
    if self.options.dorun:
      self.output.run()
    self.output.postrun()


if __name__ == '__main__':
  import sys
  from optparse import OptionParser

  oparser = OptionParser(usage="%prog [options] files...")
  oparser.add_option('--encoding', dest="encoding", default="UTF-8",
      help="Define the encoding charset of the inputs. All input files must be in the same encoding. Ignored on stdin. [default: UTF-8]")
  oparser.add_option('-o', '--output', dest="output", default="evdev",
      help="Select the output method. Use --output=list to list available outputs and exit. [default: beep]")
  oparser.add_option('-p', '--parser', dest="parser", default="qb",
      help="Select the parser method. Use --output=list to list available outputs and exit. [default: qb]")
  oparser.add_option('-R', '--no-run', action="store_false", dest="dorun", default=True,
      help="Don't run the generated command.")
  oparser.add_option('--debug', action="store_true", dest="debug", default=False,
      help="Run in debug mode.")
  Output.setupOptionsAll(oparser)
  Parser.setupOptionsAll(oparser)

  options, args = oparser.parse_args()

  def printOptionables(kindCls, kindName, default):
    print("Available %ss:" % kindName)
    print("\n".join([
      "    %s: %s%s" % (n, (kindCls.getClass(n).__doc__ or n).strip(), n == default and " [default]" or "")
      for n in kindCls.listAll()
      ]))

  if options.output == 'list':
    printOptionables(Output, 'output', 'evdev')
  if options.parser == 'list':
    printOptionables(Parser, 'parser', 'qb')
  if options.output == 'list' or options.parser == 'list':
    raise SystemExit(0)


  if not args:
    args = ['-']

  try:
    beepy = Beepy(options)
    for path in args:
      if path == '-':
        beepy.parse(sys.stdin.read())
      else:
        with open(path, 'rb') as f:
          data = f.read()
          beepy.parse(data.decode(options.encoding))
    beepy.run()
  except (BeepyParseError, RuntimeError, OSError, IOError):
    import sys
    sys.stderr.write("%s\n" % sys.exc_info()[1])
    raise SystemExit(1)
  except KeyboardInterrupt:
    pass
