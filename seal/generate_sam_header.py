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



# A really really thin wrapper.  We only seem to need it because Galaxy won't
# search for the command in the PATH

import os
import subprocess
import sys

if __name__ == '__main__':
  output_path = sys.argv[-1]
  try:
    # seal merge_alignments won't overwrite an existing file, so we first remove
    # the file Galaxy creates for us.
    os.remove(output_path)
  except IOError:
    pass
  hadoopized_output_path = 'file://' + os.path.abspath(output_path)
  cmd = [ 'seal', 'merge_alignments' ] + sys.argv[1:-1]
  cmd.append(hadoopized_output_path)
  print "running command:", str(cmd)
  subprocess.check_call(cmd)
