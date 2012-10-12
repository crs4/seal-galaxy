#!/usr/bin/env python

import fnmatch
import os
import sys
import urlparse

import pydoop.hdfs as phdfs
import pathset

SampleSheetPattern = "*/samplesheet*.csv"

def usage_error(msg=None):
  if msg:
    print >> sys.stderr, msg
  print >> sys.stderr, os.path.basename(__file__), "RUNDIR_PATHSET OUTPUT"
  sys.exit(1)

def norm_output_file(out_filename):
  u = urlparse.urlparse(out_filename)
  if u.scheme:
    return out_filename
  else:
    return 'file://' + os.path.abspath(out_filename)
  

if __name__ == '__main__':
  if len(sys.argv) != 3:
    usage_error()
  input_pathset, output_file = sys.argv[1:]

  pset = pathset.FilePathset.from_file(input_pathset)
  if len(pset) != 1:
    raise RuntimeError("Unexpected number of paths for run directory. Expected 1 but got %d" % len(pset))
  run_dir = pset.get_paths()[0]
  samplesheet = fnmatch.filter(phdfs.ls(run_dir), SampleSheetPattern)
  if len(samplesheet) == 0:
    raise RuntimeError("Didn't find sample sheet in run directory %s (looked for pattern %s)" % (run_dir, SampleSheetPattern))
  elif len(samplesheet) > 1:
    raise RuntimeError("Found too many sample sheets in run directory %s (looked for pattern %s)" % (run_dir, SampleSheetPattern))

  out = norm_output_file(output_file)
  try:
    # try to remove destination file since phdfs.cp won't overwrite it
    phdfs.rmr(out)
  except:
    pass
  phdfs.cp(samplesheet[0], out)
