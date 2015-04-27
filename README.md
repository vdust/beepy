Simple 'QBasic music language' interpreter
==========================================

Project motivated by the recovery of some old QuickBasic files with 'play'
commands in them. The idea of a standalone interpreter for this basic music
language, fully documented in the quick basic help pages, came to me very
quickly.

The first version was a simple 'beep' command generator. The 'evdev' output
was implemented to avoid the generation of very long commandlines.

The 'pcm' output is now available. It writes raw 48000Hz signed 16bits pcm
data to standard output (or a file with the --pcm-output option).
To play it using sox:

    ./beepy -o pcm file.txt | play -t raw -r 48000 -b 16 -e signed-integer -

The sample rate is also configurable using the option --pcm-samplerate



REQUIREMENTS
------------

This program should be compatible with both python 2 and python 3.



USAGE
-----

You'll probably need root privileges to run it. However, if you're in a real tty
(no xterm, no remote connection) or if the beep program is suid as root, using
the 'beep' output method should work directly.

To play some files:

    ./beepy [options] files...

To list available output methods:

    ./beepy --output=list



SYNTAX
------

The documentation of the PLAY statement can be found in a lot of places, so it
won't be put here.

Let's just point out the differences and limitations:

Octaves from 0 to 8 are supported (instead of 0 to 6). Also, notes might sound
one octave lower than original implementations.

The command 'Nn' (play the specified note in the 'original' seven-octave range)
is not implemented and will trigger a syntax error. I admit it's pure
laziness... I would need to find out which note N1 is (and because of the wilder
octave range supported, some notes won't be reachable with this command)

'MB' and 'MF' are parsed but do nothing (for obvious reasons i think)

';' is silently discarded with the rest of the line it appears on (up to the
first '\n'). It adds simple comment support.



EXAMPLES
--------

The directory 'samples' contains some pieces that i digged up from an old
folders that survived several hdd crashes and formatting.

    ./beepy samples/mariocomplete.txt

    ./beepy -o beep -- samples/presto.txt - < samples/mariocomplete.txt


If the default speaker device doesn't exist, you can grep
/proc/bus/input/devices for "PC Speaker" and find the handler (eventX) it is
linked to. Then:

    ./beepy --evdev=/dev/input/eventX samples/mariocomplete.txt



BUGS
----

This program was tested only an an x86 linux-based system. The input event
frames for the 'evdev' output method are generated based on informations
gathered from linux/input.h and its dependencies. Different platforms may use
different packing formats. Feel free to test and report.
