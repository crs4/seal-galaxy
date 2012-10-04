#!/usr/bin/env python

import argparse
import copy
import logging
import os
import subprocess
import sys
import yaml

from pathset import Pathset, FilePathset

class SealToolRunner(object):
  """
  Implements the logic necessary to run a Hadoop-based Seal tool from
  within Galaxy.

  There are two reasons why this class is necessary.

  The first is that typical Hadoop programs produce an output directory
  containing many files.  Galaxy, on the other hand, better supports the case
  where a tool reads one input file and produces an output file.  It also
  supports multiple output files, but it seems to insist on trying to open the
  main output path as a file (which causes a problem since Hadoop produces a
  directory).

  The second issue is that, since Hadoop programs usually process large data sets
  and often operate on HDFS, one may not want to store those data sets in the Galaxy
  'file_path' directory (its configured data set location).

  To address these issues, we create a level of indirection.  The SealToolRunner reads
  as input a FilePathset and produces a FilePathset.  These are the job data sets, as far
  as Galaxy is concerned.  These Pathsets contain URIs to the real data files.  In turn,
  SealToolRunner invokes the Hadoop-based program providing it with the contents of the
  input Pathset as input paths, and recording its output directory in an output FilePathset
  (the output data set provided to Galaxy).

  The SealToolRunner also sets up the necessary Hadoop environment and forwards unrecognized
  arguments down to the actual tool executable.
  """

  def __init__(self, tool_name):
    """
    Initialize a SealToolRunner for a specific tool.

    tool_name will be used as the executable name.
    """
    self.tool = tool_name
    # a list of input paths, potentially containing wildcards that will be expanded by hadoop
    self.input_params = None
    # string -- output path
    self.output_str = None
    # a list of options
    self.generic_opts = []

  def __str__(self):
    return ' '.join(
       (str(type(self)),
        "tool:", self.tool,
        "conf:", str(self.conf),
        "input:", str(self.input_params),
        "output:", self.output_str,
        "opts:", str(self.generic_opts))
      )

  def set_conf(self, conf):
    """
    Set the dict object to use for configuration values.
    """
    self.conf = conf

  def set_input(self, pathset):
    """
    Set the input paths for the Hadoop command.
    """
    self.input_params = pathset.get_paths()

  def set_output(self, pathset):
    """
    Set the output path for the Hadoop command.
    """
    if len(pathset) != 1:
      raise RuntimeError("Expecting an output pathset containing one path, but got %d" % len(pathset))
    self.output_str = iter(pathset).next()

  def parse_args(self, args_list):
    """
    Gets the remainder of the arguments, split by argparse and sets them to
    self.generic_opts.  The arguments will be passed to the Hadoop tool as
    generic options (placed them between the command name and the input path.

    This method can be overridden to implement more sophisticated parsing
    strategies.
    """
    self.generic_opts = args_list

  def command(self):
    """
    Returns the arguments array to run this Hadoop command.

    The returned array can be passed to subprocess.call and friends.

    This method checks the 'seal_bin_path' configuration value and the PATH environment
    variable to see if it can find the tool to be run.  It also verifis that the input
    and output parameters have been set.
    """
    if self.tool is None:
      raise RuntimeError("tool name not set!")
    if self.input_params is None:
      raise RuntimeError("Input parameters not set!")
    if self.output_str is None:
      raise RuntimeError("output path not set!")

    # look for the tool, either in seal_bin_path or in PATH
    if self.conf.has_key('seal_bin_path'):
      tool = os.path.join(self.conf['seal_bin_path'], self.tool)
      if not os.access(tool, os.X_OK):
        raise RuntimeError("The tool %s either doesn't exist or isn't executable" % tool)
    else:
      tool = self.tool
      if not any(os.access(os.path.join(p, tool), os.X_OK)
          for p in os.environ.get('PATH', '').split(os.pathsep)):
        raise RuntimeError(
          ("The tool %s either isn't in the PATH or isn't executable.\n" +
           "You may also choose to create a configuration file seal_galaxy_conf.yaml in your\n" +
           "tool-data path and set seal_bin_path.\nPATH: %s") % (tool, os.environ.get('PATH', '')))

    return [tool] + self.generic_opts + self.input_params + [self.output_str]

  def make_env(self):
    """
    Returns a dict containing the environment for the tool to be run.

    This method starts by copying the current environment.  If the tool_env
    configuration key is set, then it's expected to be a dict who's key-value
    pairs will become variable-value settings in the new environment dict.

    Subclasses can override this method to implement their own behaviour
    relating to the environment set for the Hadoop program to be run.
    """
    tool_env = self.conf.get('tool_env')
    if tool_env is not None:
      env = copy.copy(os.environ.data)
      for k,v in tool_env.iteritems():
        env[k] = v
    else:
      env = os.environ
    return env

  def execute(self, log):
    """
    Executes the command.

    This method calls self.command to build the command array, calls
    self.make_env to create its environment, and then executes.
    """
    log.debug("seal_bin_path is %s", self.conf.get('seal_bin_path'))
    cmd = self.command()
    env = self.make_env()
    log.debug("attempt to remove output path %s", self.output_str)
    try:
      import pydoop.hdfs as phdfs
      phdfs.rmr(self.output_str)
    except IOError, e:
      log.warning(e)
    except ImportError:
      log.warning("Failed to import pydoop.hdfs: %s", str(e))

    if not phdfs.path.exists(phdfs.path.dirname(self.output_str)):
      phdfs.mkdir(phdfs.path.dirname(self.output_str))
      log.debug("Created parent of output directory")

    log.debug("Executing command: %s", cmd)
    subprocess.check_call(cmd, env=env)


class SealDemuxRunner(SealToolRunner):
  """
  Specialized class to run the seal_demux command.

  The specialization implements support for the --sample-sheet argument, since
  it's path is passed to Hadoop and thus needs to be a complete URI.
  """
  def __init__(self):
    super(type(self), self).__init__('seal_demux')

  def parse_args(self, args_list):
    super(type(self), self).parse_args(args_list)
    try:
      sample_sheet_idx = self.generic_opts.index("--sample-sheet")
      # the following argument should be the path to the sample sheet
      if sample_sheet_idx + 1 >= len(self.generic_opts):
        raise RuntimeError("Missing argument to --sample-sheet")
      # sanitize this path, assuming it's a local path
      path_idx = sample_sheet_idx + 1
      self.generic_opts[path_idx] = Pathset.sanitize_path(self.generic_opts[path_idx])
    except ValueError: # raised if we don't find a --sample-sheet argument
      # in this case, we'll let the program go through and let Demux print
      # the appropriate error to the user
      pass


class SealSeqalRunner(SealToolRunner):
  def __init__(self):
    super(type(self), self).__init__('seal_seqal')

  def parse_args(self, args_list):
    # need to sanitize the reference argument.  Should be the last one
    self.reference_path = Pathset.sanitize_path(args_list[-1])
    self.generic_opts = args_list[:-1]

  def command(self):
    """
    Overrides the default 'command' method by appending the reference path to
    the end of the returned command array.
    """
    cmd = super(type(self), self).command()
    cmd.append(self.reference_path)
    return cmd


class SealGalaxy(object):
  Runners = {
    'seal_bwa_index_to_mmap': SealToolRunner('seal_bwa_index_to_mmap'),
    'seal_demux':             SealDemuxRunner(),
    'seal_distcp_files':      SealToolRunner('seal_distcp_files'),
    'seal_merge_alignments':  SealToolRunner('seal_merge_alignments'),
    'seal_prq':               SealToolRunner('seal_prq'),
    'seal_read_sort':         SealToolRunner('seal_read_sort'),
    'seal_recab_table':       SealToolRunner('seal_recab_table'),
    'seal_recab_table_fetch': SealToolRunner('seal_recab_table_fetch'),
    'seal_seqal':             SealSeqalRunner(),
    'seal_tsvsort':           SealToolRunner('seal_tsvsort'),
    'seal_version':           SealToolRunner('seal_version'),
  }

  def __init__(self):
    self.parser = argparse.ArgumentParser(description="Wrap Hadoop-based Seal tools to run within Galaxy")
    self.parser.add_argument('tool', metavar="SealExecutable", help="Seal program to run")
    self.parser.add_argument('--input', metavar="InputPath", help="Input paths provided by Galaxy.")
    self.parser.add_argument('--output', metavar="OutputPath", help="Output path provided by Galaxy")
    self.parser.add_argument('--append-python-path', metavar="PATH",
        help="Path to append to the PYTHONPATH before calling the Seal executable")
    self.parser.add_argument('--output-dir', metavar="PATH",
        help="URI to a working directory, if different from the Galaxy default. See the documentation for details.")
    self.parser.add_argument('--conf', metavar="SealConf", help="Seal+Galaxy configuration file")
    self.parser.add_argument('remaining_args', nargs=argparse.REMAINDER)
    logging.basicConfig(level=logging.DEBUG)

  def get_runner(self, tool_name, input_pathset, output_pathset, args):
    r = self.Runners.get(tool_name)
    if r is None:
      raise IndexError("Unknown seal tool %s" % tool_name)
    r.set_conf(self.conf)
    r.set_input(input_pathset)
    r.set_output(output_pathset)
    r.parse_args(args)
    return r


  def set_hadoop_conf(self):
    """
    If our configuration contains HADOOP_HOME or HADOOP_CONF_DIR
    copy them to our environment.  Else, whatever is in the
    current environment will remain as such.
    """
    if self.conf.has_key('HADOOP_HOME'):
      os.environ['HADOOP_HOME'] = self.conf['HADOOP_HOME']
    if self.conf.has_key('HADOOP_CONF_DIR'):
      os.environ['HADOOP_CONF_DIR'] = self.conf['HADOOP_CONF_DIR']

  def gen_output_path(self, options, name=None):
    if name:
      suffix_path = name
    else:
      # We'll use the name of the output file as the name of the data file,
      # knowing that the datapath (below) will be calculated as to not put data
      # and pathset file in the same place.
      suffix_path = os.path.basename(options.output)

    if os.path.abspath(options.output_dir) == os.path.abspath(os.path.dirname(options.output)):
      # If pathset output and data are being written to the same directory,
      # put the data in a 'hadoop_output' subdirectory.
      datapath = os.path.join(options.output_dir, 'hadoop_output')
      self.log.debug("Data output directory same as pathset output directory.")
    else:
      datapath = options.output_dir
    p = os.path.join(datapath, suffix_path)
    self.log.info("Generated data output path %s", p)
    return p

  def __configure_myself(self, options):
    if not options.conf:
      self.conf = dict()
    else:
      self.log.debug("loading config from %s", options.conf)
      try:
        with open(options.conf) as f:
          self.conf = yaml.load(f)
        self.log.debug("loaded conf: %s", self.conf)
      except IOError, e:
        self.log.critical("Couldn't load configuration from %s", options.conf)
        self.log.exception(e)
        sys.exit(1)

    self.set_hadoop_conf()

    if self.log.isEnabledFor(logging.INFO):
      self.log.info("Hadoop settings:")
      for k, v in os.environ.iteritems():
        if k.startswith("HADOOP"):
          self.log.info("%s = %s", k, v)

  def __run_tool(self, options):
    with open(options.input) as f:
      input_pathset = FilePathset.from_file(f)
      self.log.debug("Read input pathset: %s", input_pathset)

    output_pathset = FilePathset(self.gen_output_path(options))

    try:
      runner = self.get_runner(options.tool, input_pathset, output_pathset, options.remaining_args)
      self.log.debug("executing runner")
      self.log.debug("%s", runner)
      runner.execute(self.log)
      with open(options.output, 'w') as f:
        output_pathset.write(f)
    except IndexError, e:
      self.log.exception(e)
      sys.exit(2)
    except subprocess.CalledProcessError, e:
      if e.returncode < 0:
        self.log.critical("%s was terminated by signal %d", options.tool, e.returncode)
      elif e.returncode > 0:
        self.log.critical("%s exit code: %d", options.tool, e.returncode)
      sys.exit(e.returncode)
    except OSError, e:
      self.log.critical("Execution failed: %s", e)
      sys.exit(1)

  def run(self):
    options = self.parser.parse_args(args=sys.argv[1:]) # parse args, skipping the program name
    self.log = logging.getLogger(options.tool or 'Seal')

    if not options.output_dir:
      # if the output directory isn't specified, use the same
      # directory as the output file.
      options.output_dir = os.path.dirname(options.output)

    self.log.debug("options: %s", options)

    if self.log.isEnabledFor(logging.DEBUG):
      self.log.debug("Runner tools: %s", ','.join(self.Runners.iterkeys()))

    self.__configure_myself(options)

    # try importing pydoop.hdfs and fail here if something goes wrong (probably a problem
    # with Hadoop-related configuration.
    import pydoop.hdfs

    self.__run_tool(options)

if __name__ == "__main__":
  wrapper = SealGalaxy()
  wrapper.run()

# vim: expandtab autoindent shiftwidth=2 tabstop=2
