#!/usr/bin/env python

"""
Calls the Seal Demux tool.  Then, it calls the custom galaxy integration script
split_demux_output.py to generate one Galaxy dataset per each sample extracted
by Demux.
"""

# parameters:
#    GALAXY_DATA_INDEX_DIR
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
    "GALAXY_DATA_INDEX_DIR INPUT_DATA MISMATCHES NEW_FILE_PATH NUM_REDUCERS OUTPUT1 OUTPUT_ID SAMPLE_SHEET INPUT_FORMAT OUTPUT_FORMAT OUTPUT_COMPRESSION INDEX_PRESENT"
  sys.exit(1)


if __name__ == "__main__":
  if len(sys.argv) != 13:
    usage_error()

  galaxy_data_index_dir = sys.argv[1]
  input_data         = sys.argv[2]
  mismatches         = sys.argv[3]
  new_file_path      = sys.argv[4]
  num_reducers       = sys.argv[5]
  output1            = sys.argv[6]
  output_id          = sys.argv[7]
  sample_sheet       = sys.argv[8]
  input_format       = sys.argv[9]
  output_format      = sys.argv[10]
  output_compression = sys.argv[11]
  index_present      = sys.argv[12]

  mydir = os.path.abspath(os.path.dirname(__file__))

  # Run the demux program
  cmd = [
      os.path.join(mydir, 'seal_galaxy.py'),
      '--input', input_data,
      '--output', output1
      ]
  conf_file = os.path.join(galaxy_data_index_dir, 'seal_galaxy_conf.yaml')
  if os.path.exists(conf_file):
    cmd.extend( ('--conf', conf_file) )

  cmd.append('seal_demux')

  cmd.extend( (
    '--sample-sheet', sample_sheet,
    '--input-format', input_format,
    '--output-format', output_format
    ))
  if re.match(r'\s*\d+\s*', num_reducers):
    cmd.extend( ('--num-reducers', num_reducers) )

  if output_compression.lower() != 'none':
    cmd.extend( ('--compress-output', output_compression) )

  if mismatches != '0':
    cmd.extend( ('--mismatches', mismatches) )

  is_indexed = parse_index_present(index_present)
  if is_indexed is False:
    cmd.append("--no-index")

  print >> sys.stderr, ' '.join(cmd)
  subprocess.check_call(cmd)

  ###
  # now the second phase: split_demux_output.py
  cmd = [
      os.path.join(mydir, 'split_demux_output.py'),
      output_id, output1, new_file_path ]
  print >> sys.stderr, ' '.join(cmd)
  subprocess.check_call(cmd)
