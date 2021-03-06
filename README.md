
Galaxy wrapper for the Seal toolkit
====================================

These are the Galaxy wrappers for the Seal toolkit for Hadoop-based processing
of sequencing data (http://biodoop-seal.sf.net).


Installation
-------------------

You can install the Seal-Galaxy wrappers through the Galaxy toolshed or like
any other Galaxy tool.  The installation process will try to fetch and build
Seal and some of its dependencies.  However, you'll need to make sure that
the build process can find any required headers, libraries and executables,
such as:

* javac
* protobuf
* maven
* ant
* zlib
* git
* hadoop
  
For details on Seal's installation process refer directly to [its
documentation](http://biodoop-seal.sourceforge.net/installation.html).

Hadoop-Galaxy integration
----------------------------

These wrappers use the [Hadoop-Galaxy](https://github.com/crs4/hadoop-galaxy)
tool to implement the integration between Hadoop and Galaxy.  You should have a
look at its documentation.

An important issue
-----------------------

An implication of the integration provided by Hadoop-Galaxy is that Galaxy
knows nothing about your actual data. Because of this, removing the Galaxy
datasets does not delete the files produced by your Hadoop runs, potentially
resulting in the waste of a lot of space.  Also, be careful with situations
where you may end up with multiple pathsets pointing to the same data, or where
they point to data that you want to access from Hadoop but would not want to
delete (e.g., your run directories).

Have a look at the Hadoop-Galaxy README for more details.


Authors
-------------

Luca Pireddu <pireddu@crs4.it>


Support
-------------

No support is provided.



License
--------------

This code is release under the GPLv3.



Copyright
--------------

Copyright CRS4, 2011-2014.
