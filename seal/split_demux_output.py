#!/usr/bin/env python

import logging
import os
import sys

import pydoop.hdfs as phdfs

from pathset import FilePathset

Debug = os.environ.get('DEBUG', None)
logging.basicConfig(level=logging.DEBUG if Debug else logging.INFO)

def usage_error(msg=None):
  if msg:
    print >>sys.stderr, msg
  print >>sys.stderr, "Usage:  %s OUTPUT_ID DEMUX_OUTPUT_PATHSET NEW_FILE_DIR" % os.path.basename(sys.argv[0])
  sys.exit(1)

# The format is dictated by the Galaxy documentation for tools that produce a variable
# number of output files:  http://wiki.g2.bx.psu.edu/Admin/Tools/Multiple%20Output%20Files
# We fix the file_type to 'pathset'.
Galaxy_output_name_template = "primary_%s_%s_visible_pathset"

if __name__ == '__main__':
  if len(sys.argv) != 4:
    usage_error("Wrong number of arguments")

  output_id, demux_data, dest_dir = sys.argv[1:]
  logging.debug("input args: output_id, demux_data, dest_dir = %s", sys.argv[1:])

  ipathset = FilePathset.from_file(demux_data)
  logging.debug("input path set: %s", ipathset)

  # ipathset points to the output directory given to demux.  Inside it
  # we should find all the sample subdirectories.  So, we list the output
  # dir and collect sample names and their paths.  In theory, the pathset
  # we receive as input should only contains the output from one demux; thus
  # a sample should only occur once.
  if len(ipathset) != 1:
    raise RuntimeError("Unexpected demux output pathset size of %d.  Expected 1 (the demux output path)" % len(ipathset))
  sample_paths = \
    filter(lambda p: not os.path.basename(p).startswith("_"), # filter hadoop hidden files
      phdfs.ls(iter(ipathset).next()) # List the contents of the pathset. ls produces absolute paths
    )

  # sample_paths is a list of paths.  Each one points to a directory
  # containing the data from one sample.  The last element of the
  # path is both the directory name and the sample name.
  # So, we'll collect the sample names and create a new pathset
  # for each one
  for sample_p in sample_paths:
    sample_name = os.path.basename(sample_p).replace('_', '-') # replace _ with - or galaxy won't like the name
    opathset = FilePathset(sample_p)
    opathset.set_datatype(ipathset.datatype)
    opath = os.path.join(dest_dir, Galaxy_output_name_template % (output_id, sample_name))
    logging.debug("writing path %s to file %s", sample_p, opath)
    with open(opath, 'w') as f:
      opathset.write(f)
