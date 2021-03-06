#!/usr/bin/env python

# Copyright (C) 2011-2014 CRS4.
#
# This file is part of Seal.
#
# Seal is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# Seal is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.
#
# You should have received a copy of the GNU General Public License along
# with Seal.  If not, see <http://www.gnu.org/licenses/>.



"""
Calls the Seal Demux tool.  Then, it calls the custom galaxy integration script
split_demux_output.py to generate one Galaxy dataset per each sample extracted
by Demux.
"""

# parameters:
#    INPUT_DATA
#    MISMATCHES
#    NEW_FILE_PATH
#    NUM_REDUCERS
#    OUTPUT1
#    OUTPUT_ID
#    SAMPLE_SHEET
#    INPUT_FORMAT
#    OUTPUT_FORMAT
#    OUTPUT_COMPRESSION
#    SEPARATE_READS

import os
import re
import subprocess
import sys

# XXX: add --append-python-path to the possible arguments?

def parse_indexed(s):
  if s is not None:
    normalized = s.lower().strip()
    if normalized == 'notindexed':
      return False
    elif normalized == 'indexed':
      return True
  return None # failed to parse

def parse_index_present(param):
  is_indexed = parse_indexed(param)
  if is_indexed is None:
    # try to read it as a file
    if os.path.isfile(param):
      with open(param) as f:
        contents = f.readline(10000)
        uri, value = contents.split("\t", 1)
        is_indexed = parse_indexed(value)
        if is_indexed is None:
          raise RuntimeError("Error determining whether run has an index read. " + \
              "Couldn't parse the dataset that was supposed to specify it (first 1000 chars): %s" % contents)
  return is_indexed

def usage_error(msg=None):
  print >> sys.stderr, "Usage error"
  if msg:
    print >> sys.stderr, msg
  print >> sys.stderr, "Usage:", os.path.basename(sys.argv[0]),\
    "INPUT_DATA MISMATCHES NEW_FILE_PATH NUM_REDUCERS OUTPUT1 OUTPUT_ID SAMPLE_SHEET INPUT_FORMAT OUTPUT_FORMAT OUTPUT_COMPRESSION INDEX_PRESENT SEPARATE_READS"
  sys.exit(1)


if __name__ == "__main__":
  if len(sys.argv) != 13:
    usage_error()

  input_data         = sys.argv[1]
  mismatches         = sys.argv[2]
  new_file_path      = sys.argv[3]
  num_reducers       = sys.argv[4]
  output1            = sys.argv[5]
  output_id          = sys.argv[6]
  sample_sheet       = sys.argv[7]
  input_format       = sys.argv[8]
  output_format      = sys.argv[9]
  output_compression = sys.argv[10]
  index_present      = sys.argv[11]
  separate_reads     = sys.argv[12]

  mydir = os.path.abspath(os.path.dirname(__file__))

  # Run the demux program
  cmd = [
      'hadoop_galaxy',
      '--input', input_data,
      '--input-format', input_format, # --input-format for hadoop-galaxy
      '--output', output1,
      '--executable', 'seal',
      'demux',
      '--sample-sheet', sample_sheet,
      '--input-format', input_format, # --input-format for seal demux
      '--output-format', output_format
    ]
  if re.match(r'\s*\d+\s*', num_reducers):
    cmd.extend( ('--num-reducers', num_reducers) )

  if output_compression.lower() != 'none':
    cmd.extend( ('--compress-output', output_compression) )

  if mismatches != '0':
    cmd.extend( ('--mismatches', mismatches) )

  is_indexed = parse_index_present(index_present)
  if is_indexed is False:
    cmd.append("--no-index")

  norm_separate_reads = separate_reads.lower().strip()
  if norm_separate_reads == 'separate-reads':
    cmd.append("--separate-reads")
  elif norm_separate_reads.startswith('f'):
    pass
  else:
    raise RuntimeError("Unrecognized value for separate-reads parameter:  '%s'" % separate_reads)

  print >> sys.stderr, ' '.join(cmd)
  subprocess.check_call(cmd)

  ###
  # now the second phase: split_demux_output.py
  cmd = [
      os.path.join(mydir, 'split_demux_output.py'),
      output_id, output1, new_file_path ]
  print >> sys.stderr, ' '.join(cmd)
  subprocess.check_call(cmd)
