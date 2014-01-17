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
import sys

from automator import illumina_run_dir as ill
import pathset
import pydoop.hdfs as phdfs

def usage_error(msg=None):
  if msg:
    print >> sys.stderr, msg
  print >> sys.stderr, os.path.basename(__file__), "RUNDIR_PATHSET OUTPUT"
  sys.exit(1)


if __name__ == '__main__':
  if len(sys.argv) != 3:
    usage_error()
  input_pathset, output_file = sys.argv[1:]
  indexed_run = False

  # read the pathset to determine the path to the run directory
  pset = pathset.FilePathset.from_file(input_pathset)
  if len(pset) != 1:
    raise RuntimeError("Unexpected number of paths for run directory. Expected 1 but got %d" % len(pset))
  run_dir = pset.get_paths()[0]
  if not run_dir.startswith("file:/"):
    usage_error("Need a full URI to the run directory starting with 'file://' (it has to be locally accessible")

  # remove the file: prefix to the URI, then all the '/'.  Finally we add a new leading '/'
  norm_path = '/' + run_dir.replace('file:', '').strip('/')
  d = ill.RunDir(norm_path)
  info = d.get_run_info()
  if any( r.attrib['IsIndexedRead'] == 'Y' for r in info.reads ):
    indexed_run = True

  output = "%s\t%s" % (run_dir, 'Indexed' if indexed_run else 'NotIndexed')
  with open(output_file, 'w') as f:
    f.write(output)
  print output
