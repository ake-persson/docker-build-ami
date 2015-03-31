docker-build-ami
================

Build Amazon EC2 AMI image using a Dockerfile

Beware this is a work in progress, it work's but it's in need of a rewrite.

Restrictions
============
- Only support operations RUN, COPY at the moment
- Doesn't correctly quote Bash $var at moment

Configuration
=============

Requires a ~/.boto config file for Credentials:

.. code-block::

    [Credentials]
    aws_access_key_id = <access key>
    aws_secret_access_key = <secret key>

There is a separate config file for the script in either "/etc/docker-build-ami.conf" or "~/.docker-build-ami.conf".

.. code-block::

    # Temporary directory
    tmp_dir = /tmp

    # Name tag for host building AMI image
    # host_tag = 'docker-build-ami'

    # Region
    # region = eu-west-1

    # Instance type
    # instance_type = m3.medium

    # Subnet ID
    # subnet_id = subnet-123abc45

Usage
=====

.. code-block::

    usage: docker-build-ami [-h] [-c CONFIG] [-d] [-r] [-t] [-s] [-n] [-i] [-u]

    optional arguments:
      -h, --help            show this help message and exit
      -c CONFIG, --config CONFIG
                        Configuration file
      -d, --debug           Print debug info
      -r, --region          AWS region
      -t, --instance-type   EC2 instance type
      -s, --subnet-id       AWS subnet id
      -n, --image-name      AMI image name
      -i, --image-id        AMI image ID
      -u, --image-user      AMI image user

Roadmap
=======
- Move credentials to config file
- Rewrite and cleanup
