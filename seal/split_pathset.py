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



import pathset
import pydoop.hdfs as hdfs

import os
import re
import sys
import warnings

def usage_error(msg=None):
  if msg:
    print >> sys.stderr, msg
  print >> sys.stderr, os.path.basename(__file__), "EXPR ANCHOR_END EXPAND INPUT_PATHSET OUTPUT_TRUE OUTPUT_FALSE"
  sys.exit(1)


def expand(fs, root, max_levels):
    """
    Walk a directory hierarchy up to max_levels.  Yield all leaves.
    """
    if max_levels <= 0:
      yield root
    else: # max_levels >= 1
      root_info = fs.get_path_info(root)
      if root_info['kind'] == 'file':
          yield root_info['name']
      elif root_info['kind'] == 'directory':
          listing = \
            [ path_info for path_info in fs.list_directory(root_info['name'])
                   # Skip hidden files
                   if path_info['name'][0] not in ('.', '_') ]
          for item in listing:
              if max_levels == 1 or item['kind'] == 'file':
                  yield item['name']
              else:
                  for child in expand(fs, item['name'], max_levels - 1):
                      yield child
      else:
          warnings.warn("Skipping item %s. Unsupported file kind %s" % (root_info['name'], root_info['kind']))


def main():
  if len(sys.argv) != 7:
    usage_error()

  expr          = sys.argv[1]
  anchor_end    = sys.argv[2] == 'anchor_end'
  expand_levels = int(sys.argv[3])
  in_path       = sys.argv[4]
  match_path    = sys.argv[5]
  nomatch_path  = sys.argv[6]

  if expand_levels < 0:
    usage_error("number of levels to descend into path must be >= 0")

  print "input expression:", expr
  print "anchor end:", anchor_end
  if anchor_end:
    expr += '$'
  print "processed expression:", expr
  try:
    pattern = re.compile(expr)
  except RuntimeError as e:
    print >> sys.stderr, "Error compiling criteria regular expression"
    print >> sys.stderr, e
    sys.exit(2)

  source_pathset = pathset.FilePathset.from_file(in_path)

  match_pathset = pathset.FilePathset()
  match_pathset.datatype = source_pathset.datatype

  no_match_pathset = pathset.FilePathset()
  no_match_pathset.datatype = source_pathset.datatype

  for p in source_pathset:
    host, port = hdfs.path.split(p)[0:2]
    fs = hdfs.fs.hdfs(host, port)
    for leaf in expand(fs, p, expand_levels):
      if pattern.match(leaf):
        match_pathset.append(leaf)
      else:
        no_match_pathset.append(leaf)

  # write to file
  with open(match_path, 'w') as f:
    match_pathset.write(f)
  with open(nomatch_path, 'w') as f:
    no_match_pathset.write(f)

if __name__ == '__main__':
  main()
