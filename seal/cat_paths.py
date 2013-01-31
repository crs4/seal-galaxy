#!/usr/bin/env python

import os
import shutil
import subprocess
import sys
from urlparse import urlparse

from automator import illumina_run_dir as ill
import pathset
import pydoop
import pydoop.hdfs as phdfs

def usage_error(msg=None):
  if msg:
    print >> sys.stderr, msg
  print >> sys.stderr, os.path.basename(__file__), "PATHSET OUTPUT"
  sys.exit(1)

def copy_file(src_url, dest_path):
  u = urlparse(src_url)
  if u.scheme.startswith('file:'):
    try:
      # Both source and destination should be on mounted file systems.
      # Try to make a hard link to the original file
      os.link(u.path, dest_path)
      return
    except OSError as e:
      pass
  # In all other cases, remove the destination file, if it exists, and call append_file
  try:
    if os.path.exists(dest_path):
      os.unlink(dest_path)
  except OSError:
    pass
  append_file(u, dest_path)

def append_file(src_url, dest_path):
  u = urlparse(src_url)
  if u.scheme == 'file':
    cmd = "cat %s >> %s" % (u.path, dest_path)
  else:
    cmd = "%s dfs -cat %s >> %s" % (pydoop.hadoop_exec(), src_url, dest_path)
  subprocess.check_call( cmd, shell=True )

if __name__ == '__main__':
  if len(sys.argv) != 3:
    usage_error()
  input_pathset, output_file = sys.argv[1:]

  output_file = os.path.abspath(output_file)

  pset = pathset.FilePathset.from_file(input_pathset)

  def progress(i):
    print "Processed %s of %s (%0.2f %%)" % (i, len(pset), 100*(float(i) / len(pset)))
  progress(0)

  try:
    if len(pset) == 1:
      src_uri = iter(pset).next()
      copy_file(src_uri, output_file)
    else: # more than one path
      for idx, p in enumerate(pset):
        append_file(p, output_file)
        if idx % 5 == 0:
          progress(idx + 1)
    progress(len(pset))
  except IOError as e:
    print >> sys.stderr, "IOError copying pathset to", output_file
    print >> sys.stderr, "Exception:", str(e)
    sys.exit(1)
