#!/usr/bin/env python

# A really really thin wrapper.  We only seem to need it because Galaxy won't
# search for the command in the PATH

import os
import subprocess
import sys

if __name__ == '__main__':
  output_path = sys.argv[-1]
  try:
    # seal_merge_alignments won't overwrite an existing file, so we first remove
    # the file Galaxy creates for us.
    os.remove(output_path)
  except IOError:
    pass
  hadoopized_output_path = 'file://' + os.path.abspath(output_path)
  cmd = [ 'seal_merge_alignments' ] + sys.argv[1:-1]
  cmd.append(hadoopized_output_path)
  print "running command:", str(cmd)
  subprocess.check_call(cmd)
