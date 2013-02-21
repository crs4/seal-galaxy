#!/usr/bin/env python

import logging
import os
import subprocess
import sys
from urlparse import urlparse

import pathset
import pydoop
import pydoop.hdfs as phdfs

Debug = os.environ.get('DEBUG', None)
logging.basicConfig(level=logging.DEBUG if Debug else logging.INFO)

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
      logging.debug("hard linking %s to %s", u.path, dest_path)
      os.link(u.path, dest_path)
      return
    except OSError as e:
      logging.info("failed to hard link %s (Reason: %s). Will copy.", u.path, str(e))
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
  logging.debug(cmd)
  subprocess.check_call( cmd, shell=True )

def append_dir(d, output):
  """
  Appends the contents of all files within directory d to the output.
  The contents within the directory are ordered by name.

  Returns the number of files appended to the output.
  """
  contents = [ e for e in sorted(phdfs.ls(d)) if not os.path.basename(e).startswith('_') ]
  logging.debug("Appending %s items from directory %s", len(contents), d)
  items = 0
  for c in contents:
    if phdfs.path.isdir(c):
      logging.debug("Recursively descending into %s", c)
      items += append_dir(c, output)
    else:
      append_file(c, output)
      items += 1
  return items

if __name__ == '__main__':
  if len(sys.argv) != 3:
    usage_error()
  input_pathset, output_file = sys.argv[1:]

  output_file = os.path.abspath(output_file)

  pset = pathset.FilePathset.from_file(input_pathset)
  total = len(pset)

  def progress(i):
    logging.info("Processed %s of %s (%0.2f %%)", i, total, 100*(float(i) / total))
  progress(0)

  try:
    first_src_uri = iter(pset).next()
    u = urlparse(first_src_uri)
    if len(pset) == 1 and u.scheme == 'file' and os.path.isfile(u.path):
      logging.debug("Pathset contains single local file")
      copy_file(first_src_uri, output_file)
    else: # more than one path
      for idx, p in enumerate(pset):
        if phdfs.path.isdir(p):
          total += append_dir(p, output_file)
        else:
          append_file(p, output_file)
        if idx % 5 == 0:
          progress(idx + 1)
    progress(len(pset))
  except IOError as e:
    print >> sys.stderr, "IOError copying pathset to", output_file
    print >> sys.stderr, "Exception:", str(e)
    sys.exit(1)
