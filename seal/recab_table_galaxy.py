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
Calls the Seal RecabTable tool.  Then, it calls recab_table_fetch to
concatenate all the partial tables and create a single csv file.
"""


# parameters:
#    GALAXY_DATA_INDEX_DIR
#    INPUT_DATA
#    OUTPUT
#    VCF
#    NUM_REDUCERS
#    [OTHER]

import os
import sys

from seal_galaxy import HadoopGalaxy
import pathset
import subprocess
import tempfile
import pydoop.hdfs as phdfs

# XXX: add --append-python-path to the possible arguments?

def usage_error(msg=None):
  if msg:
    print >> sys.stderr, msg
  print >> sys.stderr, os.path.basename(sys.argv[0]), "GALAXY_DATA_INDEX_DIR INPUT_DATA OUTPUT VCF NUM_REDUCERS [OTHER]"
  sys.exit(1)


def run_recab(conf_file, input_path, output_path, vcf, num_red, other_args):
  mydir = os.path.abspath(os.path.dirname(__file__))
  cmd = [
    os.path.join(mydir, 'seal_galaxy.py'),
    '--input', input_path,
    '--output', output_path,
    # XXX: assumes the output directory is on a locally mounted file system
    '--output-dir', os.path.join('file://', os.path.dirname(input_path), HadoopGalaxy.HadoopOutputDirName)
    ]

  if os.path.exists(conf_file):
    cmd.extend( ('--conf', conf_file) )

  cmd.extend( (
    'seal_recab_table',
    '--vcf-file', vcf,
    '--num-reducers', num_red
  ))

  if other_args:
    cmd.extend(other_args)

  # now execute the hadoop job
  subprocess.check_call(cmd)

def collect_table(pset, output_path):
  # finally, fetch the result into the final output file
  cmd = ['seal_recab_table_fetch']
  cmd.extend(pset.get_paths())
  cmd.append(output_path)
  try:
    # remove the file that galaxy creates.  recab_table_fetch refuses to
    # overwrite it
    os.unlink(output_path)
  except IOError:
    pass
  subprocess.check_call(cmd)

def cleanup(out_pathset):
  # clean-up job output
  for path in out_pathset:
    try:
      print >> sys.stderr, "Deleting output path", path
      phdfs.rmr(path)
    except StandardError as e:
      print >> sys.stderr, "Error!", str(e)

def main(args):
  if len(args) < 5:
    usage_error()

  galaxy_data_index_dir = args[0]
  input_data            = args[1]
  final_output          = args[2]
  vcf                   = args[3]
  num_reducers          = args[4]
  other                 = args[5:]

  conf_file = os.path.join(galaxy_data_index_dir, 'seal_galaxy_conf.yaml')

  # Create a temporary pathset to reference the recab_table
  # output directory
  with tempfile.NamedTemporaryFile(mode='rwb') as tmp_pathset_file:
    try:
      run_recab(conf_file, input_data, tmp_pathset_file.name, vcf, num_reducers, other)
      tmp_pathset_file.seek(0)
      out_paths = pathset.FilePathset.from_file(tmp_pathset_file)
      collect_table(out_paths, final_output)
    finally:
      cleanup(out_paths)

if __name__ == "__main__":
  main(sys.argv[1:])

# vim: et ai ts=2 sw=2
