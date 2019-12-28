docker-build-ami
================

Build Amazon EC2 AMI image using a Dockerfile

Limitations
===========
Only supports instructions ENV, RUN, COPY and ADD, other instructions will just be ignored.

Configuration
=============

There is a separate config file for the script in either "/etc/docker-build-ami.conf" or "~/.docker-build-ami.conf".

.. code-block::

    # [main]

    # Temporary directory
    # tmp_dir = /tmp

    # Name tag for host building AMI image
    # host_tag = 'docker-build-ami'

    # Region
    # region = eu-west-1

    # Instance type
    # instance_type = m3.medium

    # Subnet ID
    # subnet_id = subnet-123abc45

    # Security Groups
    # security_group_ids = ["sg-1234", "sg-23456"]

    # Host Tags - additional tags to add to EC2 host
    # host_tags = [{"Key": "foo", "Value": "bar"}]

    # AWS access key id
    # aws_access_key_id = DFSDF3HGDF4SDSD1DDFF

    # AWS secret access key
    # aws_secret_access_key = 3riljdsf5SDFSDvsdfds452sdSDFDfsdf44SDFdRA

    # Base image from which the output image is built
    # image_id = ami-0df67e2624dedbae1

    # EC2 user used to build instances (usually AMI dependent)
    # image_user = ubuntu

    # The AMI Name of the output image
    # image_name = ubuntu-test

    # Image Tags - tags to add to AMI
    # image_tags = [{"Key": "foo", "Value": "bar"}]


Usage
=====

.. code-block::

        usage: docker-build-ami [-h] [-c CONFIG] [-d] [-r REGION] [-t INSTANCE_TYPE]
                                [-s SUBNET_ID] [-n IMAGE_NAME] [-i IMAGE_ID]
                                [-u IMAGE_USER]

        optional arguments:
          -h, --help            show this help message and exit
          -c CONFIG, --config CONFIG
                                Configuration file
          -d, --debug           Print debug info
          -r REGION, --region REGION
                                AWS region
          -t INSTANCE_TYPE, --instance-type INSTANCE_TYPE
                                EC2 instance type
          -s SUBNET_ID, --subnet-id SUBNET_ID
                                AWS subnet id
          -n IMAGE_NAME, --image-name IMAGE_NAME
                                Target AMI image name
          -i IMAGE_ID, --image-id IMAGE_ID
                                Source AMI image ID
          -u IMAGE_USER, --image-user IMAGE_USER
                                AMI image user

Running Tests
=============

.. code-block::

    # Run these lines once
    pip3 install -r requirements-test.txt
    pre-commit install

    # Run these lines to check code formatting and correctness
    flake8 --show-source --filename="\*.py" .
    pytest --cov=docker2ami

