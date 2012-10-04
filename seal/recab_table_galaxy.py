#!/usr/bin/env python

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

import pathset
import subprocess
import tempfile

# XXX: add --append-python-path to the possible arguments?

def usage_error(msg=None):
  if msg:
    print >> sys.stderr, msg
  print >> sys.stderr, os.path.basename(sys.argv[0]), "GALAXY_DATA_INDEX_DIR INPUT_DATA OUTPUT VCF NUM_REDUCERS [OTHER]"
  sys.exit(1)

if __name__ == "__main__":
  if len(sys.argv) < 6:
    usage_error()

  galaxy_data_index_dir = sys.argv[1]
  input_data = sys.argv[2]
  final_output = sys.argv[3]
  vcf = sys.argv[4]
  num_reducers = sys.argv[5]
  other = sys.argv[6:]

  mydir = os.path.abspath(os.path.dirname(__file__))
  with tempfile.NamedTemporaryFile(mode='rwb') as pathset_file:
    cmd = [
      os.path.join(mydir, 'seal_galaxy.py'),
      '--input', input_data,
      '--output', pathset_file.name
      ]
    conf_file = os.path.join(galaxy_data_index_dir, 'seal_galaxy_conf.yaml')
    if os.path.exists(conf_file):
      cmd.extend( ('--conf', conf_file) )
    cmd.extend( (
    'seal_recab_table',
    '--vcf-file', vcf,
    '--num-reducers', num_reducers
    ))
    cmd.extend(other)

    # now execute the hadoop job
    subprocess.check_call(cmd)
    # finally, fetch the result into the final output file
    p = pathset.FilePathset.from_file(pathset_file)
    cmd = ['seal_recab_table_fetch']
    cmd.extend(p.get_paths())
    cmd.append(final_output)
    try:
      # remove the file that galaxy creates.  recab_table_fetch refuses to
      # overwrite it
      os.unlink(final_output)
    except:
      pass
    subprocess.check_call(cmd)

# vim: et ai ts=2 sw=2
