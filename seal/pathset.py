
import argparse
import os

class Pathset(object):
  """
  A collection of paths, with an associated data type.
  """

  Unknown = "Unknown"

  def __init__(self, *pathlist):
    self.paths = pathlist
    self.datatype = self.Unknown

  def set_datatype(self, datatype):
    self.datatype = datatype

  def append(self, p):
    self.paths.append(p)
    return self

  def get_paths(self):
    return self.paths

  def __str__(self):
    return os.pathsep.join(self.paths)

class FilePathset(Pathset):
  """
  Extends the Pathset with a serialization format.
  """
  Magic = "# Pathset"
  VersionTag = "Version"
  Version = "0.0"
  DataTypeTag = "DataType"

  @staticmethod
  def from_file(fd):
    retval = FilePathset()
    retval.read(fd)
    return retval

  def __init__(self, *pathlist):
    super(type(self), self).__init__(*pathlist)

  def __format_header(self):
    return '\t'.join((self.Magic, ':'.join( (self.VersionTag, self.Version) ), ':'.join( (self.DataTypeTag, self.datatype) )))

  def __parse_header(self, header_line):
    if not header_line.startswith(self.Magic):
      raise ValueError("Unrecognized Pathset file format. Expected string '%s' not found at start of file. Found %s" %\
          (self.Magic, header_line if len(header_line) <= 10 else header_line[0:10] + '...'))
    fields = header_line.split('\t')
    field_dict = dict( f.split(':') for f in fields[1:] )

    if field_dict.get(self.VersionTag, self.Version) != self.Version:
      raise ValueError("Incompatible Pathset file format (found version %s but expected version %s)" % (field_dict[self.VersionTag], self.Version))
    self.datatype = field_dict.get(self.DataTypeTag, self.Unknown)

  def read(self, fd):
    header = fd.readline()
    self.__parse_header(header)
    self.paths = [ line.rstrip('\n') for line in fd.xreadlines() ]
    return self

  def write(self, fd):
    fd.write(self.__format_header() + '\n')
    for p in self.paths:
      fd.write(p)
      fd.write('\n')

