changeset tool
==============
This is highlevel utility for easy patchset creation. Each patchset has
a version and description.

Installing
----------
To install the latest released version with pip::

    python3 -m pip install changeset

Upgrading
---------
If you previously installed from pypi::

    python3 -m pip install --upgrade changeset

Running from the checkout dir
-----------------------------
If you want to run from the checkout dir without installing the python
package, you can use the included ``cs.sh`` wrapper. You can set it as
an alias in your .bash_profile::

    alias cs="$HOME/path/to/changeset/cs.sh"

Setting up a symlink should also be possible.

Support
-------
For support or with any other questions, please email to authors.
