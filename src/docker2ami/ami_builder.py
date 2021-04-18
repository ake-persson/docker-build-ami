import boto3
import datetime
import glob
import json
import logging
import paramiko
import shlex
import socket
import tarfile
import time
import uuid

from os.path import expanduser, join
from sys import stdout


logger = logging.getLogger(__name__)


class Color:
    RED = '\033[31m'
    YELLOW = '\033[33m'
    DARK_GREY = '\033[90m'
    CLEAR = '\033[0m'


def _check_port(host, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((host, port))
        s.shutdown(socket.SHUT_RDWR)
        s.close()
        return True
    except socket.error:
        return False


class AwsConfig(object):
    """
    Holds AWS configuration info for the AMI Builder.
    """
    def __init__(self, config, section, overrides):
        """
        Initialize configuration information from the given config file and
        section. overrides is an object that will ovverde the values in config.
        """
        key_names = [
            'host_tag', 'tmp_dir', 'image_name', 'region', 'instance_type',
            'subnet_id', 'image_id', 'image_user', 'aws_access_key_id',
            'aws_secret_access_key', 'security_group_ids', 'host_tags',
            'image_tags',
        ]
        for key in key_names:
            setattr(self, key,
                    getattr(overrides, key)
                    if hasattr(overrides, key) and
                    not getattr(overrides, key) is None
                    else config.get(section, key))


class AmiBuilder(object):
    """
    Object for building up an AMI. Can be invoked via with: or by explicitly
    invoking start() and finish()
    """
    def __init__(self, aws_config):
        """
        Initializes the AMI from the given configuration.
        """
        self._config = aws_config
        self._key_name = str(uuid.uuid4())
        self._key_path = expanduser(join(self._config.tmp_dir,
                                         f'{self._key_name}.pem'))
        self._security_group_ids = json.loads(aws_config.security_group_ids)
        self._host_tags = json.loads(aws_config.host_tags)
        self._image_tags = json.loads(aws_config.image_tags)
        self._ec2 = None
        self._key_pair = None
        self._instance_obj = None

    def start(self):
        """
        Starts the process of building an AMI by launching and connecting to
        an EC2
        """
        # Connect to AWS
        try:
            self._ec2 = boto3.client(
              'ec2', region_name=self._config.region,
              aws_access_key_id=self._config.aws_access_key_id,
              aws_secret_access_key=self._config.aws_secret_access_key)
            self._ec2_resource = boto3.resource('ec2')
        except BaseException:
            raise RuntimeError('Failed to connect to EC2')

        # Create the EC2 instance that we will use to build the AMI
        self._key_pair = self._ec2.create_key_pair(KeyName=self._key_name)
        with open(self._key_path, 'w') as f:
            f.write(self._key_pair['KeyMaterial'])
        tags = self._host_tags + [
          {'Key': 'Name', 'Value': self._config.host_tag},
        ]
        tag_spec = [
          {'ResourceType': 'instance', 'Tags': tags},
          {'ResourceType': 'volume', 'Tags': tags},
        ]
        reservation = self._ec2.run_instances(
          ImageId=self._config.image_id, KeyName=self._key_name,
          InstanceType=self._config.instance_type,
          SubnetId=self._config.subnet_id, MinCount=1, MaxCount=1,
          TagSpecifications=tag_spec,
          SecurityGroupIds=self._security_group_ids)

        # Find the newly created EC2
        self._instance = None
        for r in self._ec2.describe_instances()['Reservations']:
            if r['ReservationId'] == reservation['ReservationId']:
                self._instance = r['Instances'][0]
                break
        if not self._instance:
            raise RuntimeError(
                f'Unable to find EC2: {reservation["ReservationId"]}')
        print(f'Instance: {self._instance["InstanceId"]}')
        print(f'Instance IP: {self._instance["PrivateIpAddress"]}')
        print(f'Connection SSH key: {self._key_path}')

        # Wait around for the EC2 to be running
        stdout.write('Waiting for instance status running.')
        stdout.flush()
        self._instance_obj = self._ec2_resource.Instance(
          self._instance['InstanceId'])
        while self._instance_obj.state['Name'] != 'running':
            stdout.write('.')
            stdout.flush()
            time.sleep(5)
            self._instance_obj.reload()

        # Wait for the EC2 to be accessible via SSH
        stdout.write('\nWaiting for SSH to become ready.')
        stdout.flush()
        while not _check_port(self._instance_obj.private_ip_address, 22):
            stdout.write('.')
            stdout.flush()
            time.sleep(5)

        # Connect via ssh
        key = paramiko.RSAKey.from_private_key_file(self._key_path)
        self._ssh = paramiko.SSHClient()
        self._ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self._ssh.connect(hostname=self._instance_obj.private_ip_address,
                          username=self._config.image_user,
                          pkey=key)

    def send_archive(self):
        print('\nCreate archive...')
        with tarfile.open(
          join(self._config.tmp_dir, 'docker-build-ami.tar.gz'),
          'w:gz') as tar:
            for fn in glob.glob('*'):
                logger.info(f'Adding file to archive: {fn}')
                tar.add(fn)

        print('\nCopy archive...')
        sftp = self._ssh.open_sftp()
        sftp.put(self._config.tmp_dir + '/docker-build-ami.tar.gz',
                 '/tmp/docker-build-ami.tar.gz')
        sftp.close()

        # Untar archive
        print('\nUntar archive...')
        self.run_cmd('',
                     'mkdir /tmp/docker-build-ami; '
                     'tar -xzf /tmp/docker-build-ami.tar.gz'
                     ' -C /tmp/docker-build-ami')

    def run_cmd(self, env, cmd):
        stdin, stdout, stderr = self._ssh.exec_command(
          f'set -ex; echo {shlex.quote(env)} {shlex.quote(cmd)} | sudo -i --',
          get_pty=True)
        output = stdout.read()
        if output:
            print(f'{Color.YELLOW}{str(output, "utf8")}{Color.CLEAR}')
        output = stderr.read()
        if output:
            print(f'{Color.RED}{str(output, "utf8")}{Color.CLEAR}')

        ecode = stdout.channel.recv_exit_status()
        if ecode != 0:
            logger.error(
                f'The command {cmd} returned a non-zero code: {ecode}')
            exit(ecode)

    def save_ami(self):
        print(f'\nCreate AMI from instance: {self._instance_obj.instance_id}')
        image_obj = self._instance_obj.create_image(
            Name=f'{self._config.image_name}-'
                 f'{datetime.datetime.now().strftime("%Y%m%d%H%M%S")}')
        self._ec2.create_tags(Resources=[image_obj.image_id],
                              Tags=self._image_tags
                              + [{'Key': 'Name',
                                  'Value': self._config.image_name}])
        while image_obj.state == 'pending':
            stdout.write('.')
            stdout.flush()
            time.sleep(5)
            image_obj.reload()

        print(f'\nCreated image: {image_obj.image_id}')

    def finish(self):
        try:
            if self._instance_obj:
                self._instance_obj.terminate()
        finally:
            self._instance_obj = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.finish()
