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



"""
Calls the Seal USort tool.  Then, it performs the custom galaxy integration
separating the output files into two data sets -- one for read 1, one for read 2.
"""

# parameters:
#    GALAXY_DATA_INDEX_DIR
#    NUM_REDUCERS
#    INPUT_DATA
#    OUTPUT1
#    OUTPUT2
#    INPUT_FORMAT
#    OUTPUT_FORMAT
#    OUTPUT_COMPRESSION

import logging
import os
import re
import subprocess
import sys

import pydoop.hdfs as phdfs

from pathset import FilePathset

Debug = os.environ.get('DEBUG', None)
logging.basicConfig(level=logging.DEBUG if Debug else logging.INFO)

# XXX: add --append-python-path to the possible arguments?

def usage_error(msg=None):
  print >> sys.stderr, "Usage error"
  if msg:
    print >> sys.stderr, msg
  print >> sys.stderr, "Usage:", os.path.basename(sys.argv[0]),\
    "GALAXY_DATA_INDEX_DIR INPUT_DATA OUTPUT1 OUTPUT2 INPUT_FORMAT OUTPUT_FORMAT OUTPUT_COMPRESSION"
  sys.exit(1)


def split_paths(galaxy_out_pathset):
  part_paths = \
    filter(lambda p: not os.path.basename(p).startswith("_"), # filter hadoop hidden files
      phdfs.ls(iter(galaxy_out_pathset).next()) # List the contents of the pathset. ls produces absolute paths
    )
  if len(part_paths) == 0:
    raise RuntimeError("Couldn't list any part files from path %s" % iter(galaxy_out_pathset).next())

  # partition the paths -- even on one side, odd on the other
  sorted_part_paths = sorted(part_paths)
  # XXX: make the following lines more robust -- for instance, catch errors name format
  r1 = [ p for p in sorted_part_paths if int(re.match(r'.*/part-.*(\d+).*', p).group(1)) % 2 == 1 ]
  r2 = [ p for p in sorted_part_paths if int(re.match(r'.*/part-.*(\d+).*', p).group(1)) % 2 == 0 ]

  if logging.getLogger().isEnabledFor(logging.DEBUG):
    logging.debug("paths for read 1:\n%s", "\n\t".join(r1))
    logging.debug("paths for read 2:\n%s", "\n\t".join(r2))

  return r1, r2

def write_pathset(element_paths, datatype, file_path):
  with open(file_path, 'w') as f_output:
    pset = FilePathset(*element_paths)
    pset.set_datatype(datatype)
    pset.write(f_output)



if __name__ == "__main__":
  if len(sys.argv) != 8:
    usage_error()

  galaxy_data_index_dir = sys.argv[1]
  input_data            = sys.argv[2]
  output1               = sys.argv[3]
  output2               = sys.argv[4]
  input_format          = sys.argv[5]
  output_format         = sys.argv[6]
  output_compression    = sys.argv[7]

  if output1 == output2:
    raise RuntimeError("The two output paths into which to split the reads cannot be the same (got %s and %s)" % (output1, output2))

  mydir = os.path.abspath(os.path.dirname(__file__))

  # We first run the hadoop-based USort program using the first
  # provided output path (`output1`).
  # Then, we rewrite the first pathset to only include the odd-numbered
  # parts (which contain read 1) and create a second pathset at path
  # `output2` containing the even-numbered parts (which contain read 2).

  # Build the usort command.
  cmd = [
      os.path.join(mydir, 'seal_galaxy.py'),
      '--input', input_data,
      '--output', output1
      ]
  conf_file = os.path.join(galaxy_data_index_dir, 'seal_galaxy_conf.yaml')
  if os.path.exists(conf_file):
    cmd.extend( ('--conf', conf_file) )

  cmd.append('seal_usort')

  cmd.extend( (
    '--input-format', input_format,
    '--output-format', output_format
    ))

  if output_compression.lower() != 'none':
    cmd.extend( ('--compress-output', output_compression) )
    logging.debug("Compressing output with %s", output_compression)

  logging.info(' '.join(cmd))
  try:
    subprocess.check_call(cmd)
  except subprocess.CalledProcessError as e:
    logging.exception(e)
    sys.exit(e.returncode)

  # Now "fix" the output pathsets.  We need to split the pathset that
  # was created for the usort job into two pathsets, one per dataset.
  # One will contain read 1, the other read 2.
  # USort writes its output so that the odd files contain read 1 and
  # the even files contain read 2.  We'll list the individual files
  # explicitly in the pathsets.

  logging.debug("Separating read files")

  original_pathset = FilePathset.from_file(output1)
  if len(original_pathset) != 1:
    raise RuntimeError("Unexpected usort output pathset size of %d.  Expected 1 (the usort output path)" % len(original_pathset))

  r1, r2 = split_paths(original_pathset)

  # Create final output pathsets
  write_pathset(r1, original_pathset.datatype, output1)
  logging.debug("Wrote read 1 fileset %s", output1)
  write_pathset(r2, original_pathset.datatype, output2)
  logging.debug("Wrote read 2 fileset %s", output2)

  logging.info("Finished")
