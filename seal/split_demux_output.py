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
    print >> sys.stderr, msg
  print >> sys.stderr, "Usage:  %s OUTPUT_ID DEMUX_OUTPUT_PATHSET NEW_FILE_DIR" % os.path.basename(sys.argv[0])
  sys.exit(1)


class PathsetWriter(object):
  # The format is dictated by the Galaxy documentation for tools that produce a variable
  # number of output files:  http://wiki.g2.bx.psu.edu/Admin/Tools/Multiple%20Output%20Files
  # We fix the file_type to 'pathset'.
  Galaxy_output_name_template = "primary_%s_%s_visible_pathset"

  def __init__(self, output_dir, output_id, data_type):
    self.output_dir = output_dir
    self.output_id = output_id
    self.data_type = data_type

  def write_pathset(self, dataset_path, name):
    """
    dataset_path: the path of the dataset to which the new pathset needs to refer
    name:  name of dataset to appear in Galaxy
    """
    if not name:
      raise RuntimeError("Blank dataset name")
    sanitized_name = name.replace('_', '-') # replace _ with - or galaxy won't like the name
    opathset = FilePathset(dataset_path)
    opathset.set_datatype(self.data_type)
    opath = os.path.join(self.output_dir, self.Galaxy_output_name_template % (self.output_id, sanitized_name))
    logging.debug("writing dataset path %s to pathset file %s", dataset_path, opath)
    with open(opath, 'w') as f:
      opathset.write(f)
    return self # to allow chaining



def main():
  if len(sys.argv) != 4:
    usage_error("Wrong number of arguments")

  output_id, demux_data, dest_dir = sys.argv[1:]
  logging.debug("input args: output_id, demux_data, dest_dir = %s", sys.argv[1:])

  ipathset = FilePathset.from_file(demux_data)
  logging.debug("input path set: %s", ipathset)

  writer = PathsetWriter(dest_dir, output_id, ipathset.datatype)

  # ipathset points to the output directory given to demux.  Inside it
  # we should find all the project/sample subdirectories, plus 'unknown' (if there
  # were any reads not attributable to a sample).  So, we list the output
  # dir and collect sample names and their paths.  In theory, the pathset
  # we receive as input should only contains the output from one demux; thus
  # a sample should only occur once.
  if len(ipathset) != 1:
    raise RuntimeError("Unexpected demux output pathset size of %d.  Expected 1 (the demux output path)" % len(ipathset))

  project_paths = \
    filter(lambda p: os.path.basename(p)[0] not in ('_', '.'), # filter hadoop and regular hidden files
      phdfs.ls(iter(ipathset).next()) # List the contents of the pathset. ls produces absolute paths
    )
  # Each project_path points to a directory containing the data from one project.
  # There may also be a directory 'unknown'
  for project_path in project_paths:
    if os.path.basename(project_path).lower() == 'unknown':
      writer.write_pathset(project_path, 'unknown')
    else:
      for project_sample_path in phdfs.ls(project_path):
        # take the last two elements of the path -- should be project, sample
        complete_sample_name = "%s.%s" % tuple(project_sample_path.split(os.path.sep)[-2:])
        writer.write_pathset(project_sample_path, complete_sample_name)

if __name__ == '__main__':
  main()
