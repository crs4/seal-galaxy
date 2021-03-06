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



import os
import subprocess
import sys
import tempfile

import hadoop_galaxy.pathset as pathset
import hadoop_galaxy.cat_paths as cat_paths

def usage_error(msg=None):
  if msg:
    print >> sys.stderr, msg
  print >> sys.stderr, os.path.basename(__file__), "INPUT_PATHSET OUTPUT [args...]"
  sys.exit(1)

def main(args):
  if len(args) < 2:
    usage_error()

  # We generate the header with seal_merge_alignments, insert it at the
  # top of a copy of the input pathset, and then use cat_parts to
  # join everything into a single file.

  input_pathset, output_path = map(os.path.abspath, args[0:2])

  with tempfile.NamedTemporaryFile() as header_file:
    print "generating header"
    gen_header_cmd = [ 'seal', 'merge_alignments', '--header-only' ]
    gen_header_cmd.extend(args[2:])
    header_text = subprocess.check_output(gen_header_cmd)

    header_file.write(header_text)
    header_file.flush()
    print "header ready"
    print "generating new pathset"

    original_pathset = pathset.FilePathset.from_file(input_pathset)
    new_pathset = pathset.FilePathset()
    new_pathset.append(header_file.name)
    for p in original_pathset:
      new_pathset.append(p)

    with tempfile.NamedTemporaryFile() as temp_pathset:
      new_pathset.write(temp_pathset)
      temp_pathset.flush()

      print "concatenating pathset"
      # TODO:  Add ability to use dist_cat_paths
      cat_paths.main([temp_pathset.name, output_path])
      print "operation complete"

if __name__ == '__main__':
  main(sys.argv[1:])
