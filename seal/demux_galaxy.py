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

import os
import subprocess
import sys

# XXX: add --append-python-path to the possible arguments?

def usage_error(msg=None):
  if msg:
    print >> sys.stderr, msg
  print >> sys.stderr, os.path.basename(sys.argv[0]),\
    "GALAXY_DATA_INDEX_DIR INPUT_DATA MISMATCHES NEW_FILE_PATH NUM_REDUCERS OUTPUT1 OUTPUT_ID SAMPLE_SHEET"
  sys.exit(1)


if __name__ == "__main__":
  if len(sys.argv) != 9:
    usage_error()

  galaxy_data_index_dir = sys.argv[1]
  input_data = sys.argv[2]
  mismatches = sys.argv[3]
  new_file_path = sys.argv[4]
  num_reducers = sys.argv[5]
  output1 = sys.argv[6]
  output_id = sys.argv[7]
  sample_sheet = sys.argv[8]

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

  cmd.extend( (
    'seal_demux', 
    '--sample-sheet', sample_sheet,
    '--num-reducers', num_reducers,
    ))

  if mismatches != '0':
    cmd.extend( ('--mismatches', mismatches) )

  print >> sys.stderr, ' '.join(cmd)
  subprocess.check_call(cmd)

  ###
  # now the second phase: split_demux_output.py
  cmd = [
      os.path.join(mydir, 'split_demux_output.py'),
      output_id, output1, new_file_path ]
  print >> sys.stderr, ' '.join(cmd)
  subprocess.check_call(cmd)
