#!/usr/bin/env python

import argparse
import copy
import logging
import os
import random
import shlex
import shutil
import subprocess
import sys
import urlparse
import yaml

class SealToolRunner(object):
  def __init__(self, tool_name):
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
    self.conf = conf

  def sanitize_path(self, path):
    """
    Turns a path into a full URI, if it's not already.  For now we're assuming all paths
    are on the local file system (no HDFS).

    How to support multiple file systems?
    """
    url = urlparse.urlparse(path)
    if url.scheme: # empty string if now available
      return path
    else:
      return "file://" + os.path.abspath(path)

  def set_input(self, input_params):
    """
    Input: a string that can be parsed as a list of input paths.
    We split the string with shlex.split as to properly pass the
    input arguments to the program to be called.
    """
    self.input_params = map(self.sanitize_path, shlex.split(input_params))

  def set_output(self, output_str):
    self.output_str = self.sanitize_path(output_str)

  def parse_args(self, args_list):
    """
    Gets the remainder of the arguments, split by argparse. In its simplest form,
    this method saves the arguments and passes them to as options to
    the Seal tool (placing them between the command name and the input
    path.
    """
    self.generic_opts = args_list

  def command(self):
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
        raise RuntimeError("The tool %s either isn't in the PATH or isn't executable. PATH: %s" % (tool, os.environ.get('PATH', '')))

    return [tool] + self.generic_opts + self.input_params + [self.output_str]

  def make_env(self):
    tool_env = self.conf.get('tool_env')
    if tool_env is not None:
      env = copy.copy(os.environ.data)
      for k,v in tool_env.iteritems():
        env[k] = v
    else:
      env = os.environ
    return env

  def execute(self, log):
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
    log.debug("Executing command: %s", cmd)
    subprocess.check_call(cmd, env=env)

class SealDemuxRunner(SealToolRunner):
  def __init__(self):
    super(type(self), self).__init__('seal_demux')

  def parse_args(self, args_list):
    super(type(self), self).parse_args(args_list)
    try:
      sample_sheet_idx = self.generic_opts.index("--sample-sheet")
      # the following argument should be the path to the sample sheet
      if sample_sheet_idx + 1 >= len(self.generic_opts):
        raise RuntimeError("Missing argumetn to --sample-sheet")
      # sanitize this path, assuming it's a local path
      path_idx = sample_sheet_idx + 1
      self.generic_opts[path_idx] = self.sanitize_path(self.generic_opts[path_idx])
    except ValueError: # raised if we don't find a --sample-sheet argument
      # in this case, we'll let the program go through and let Demux print
      # the appropriate error to the user
      pass


class SealSeqalRunner(SealToolRunner):
  def __init__(self):
    super(type(self), self).__init__('seal_seqal')

  def parse_args(self, args_str):
    pass

  def command(self):
    raise NotImplementedError()


class RunnerFactory(object):
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

  def __init__(self, conf):
    self.conf = conf

  def get_runner(self, tool_name, input_path, output_path, args):
    r = self.Runners.get(tool_name)
    if r is None:
      raise IndexError("Unknown seal tool %s" % tool_name)
    r.set_conf(self.conf)
    r.set_input(input_path)
    r.set_output(output_path)
    r.parse_args(args)
    return r

 
class SealGalaxy(object):
  def __init__(self):
    self.parser = argparse.ArgumentParser(description="Wrap Hadoop-based Seal tools to run within Galaxy")
    self.parser.add_argument('tool', metavar="SealExecutable", help="Seal program to run")
    self.parser.add_argument('--input', metavar="InputPath", help="Input paths provided by Galaxy.")
    self.parser.add_argument('--output', metavar="OutputPath", help="Output path provided by Galaxy")
    self.parser.add_argument('--append-python-path', metavar="PATH",
        help="Path to append to the PYTHONPATH before calling the Seal executable")
    self.parser.add_argument('--working-dir', metavar="PATH",
        help="URI to a working directory, if different from the Galaxy default. See the documentation for details.")
    self.parser.add_argument('--conf', metavar="SealConf", help="Seal+Galaxy configuration file")
    self.parser.add_argument('remaining_args', nargs=argparse.REMAINDER)
    logging.basicConfig(level=logging.DEBUG)

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

  def run(self):
    options = self.parser.parse_args(args=sys.argv[1:]) # parse args, skipping the program name
    self.log = logging.getLogger(options.tool or 'Seal')
    self.log.debug("options: %s", options)

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
    import pydoop.hdfs

    if self.log.isEnabledFor(logging.INFO):
      self.log.info("Hadoop settings:")
      for k,v in os.environ.iteritems():
        if k.startswith("HADOOP"):
          self.log.info("%s = %s", k, v)

    self.log.debug("Creating runner factory with conf %s", self.conf)
    self.factory = RunnerFactory(self.conf)
    if self.log.isEnabledFor(logging.DEBUG):
      self.log.debug("Runner tools: %s", ','.join(self.factory.Runners.iterkeys()))

    try:
      runner = self.factory.get_runner(options.tool, options.input, options.output, options.remaining_args)
      self.log.debug("executing runner")
      self.log.debug("%s", runner)
      runner.execute(self.log)
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
 

if __name__ == "__main__":
  wrapper = SealGalaxy()
  wrapper.run()

#hdfs = pydoop.hdfs.hdfs("default", 0)
#self.log.debug("connected to hdfs at %s", hdfs.host)


## hack to read the input path directly from the command line
##input_paths = [ galaxy_input ]
#
#with open(galaxy_input) as f:
#  input_paths = [ s.rstrip("\n") for s in f.readlines() ]
#
#output_path = os.path.join( hdfs.working_directory(), "galaxy-wrapper-%f" % random.random())
#
#hdfs.close()
#log.debug("hdfs closed")
#
#with open(galaxy_output, 'w') as f:
#  f.write(output_path)

# vim: set et ai sw=2 ts=2
