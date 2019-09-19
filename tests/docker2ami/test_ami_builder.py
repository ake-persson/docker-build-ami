import configparser
import os
import pytest
import socket
from unittest.mock import call, MagicMock, patch

import docker2ami.ami_builder as ami_builder
from docker2ami.ami_builder import Color


class EmptyObj(object):
    """ So we can dynamically add attributes """
    pass


def test_color():
    assert Color.RED == '\033[31m'
    assert Color.YELLOW == '\033[33m'
    assert Color.DARK_GREY == '\033[90m'
    assert Color.CLEAR == '\033[0m'


@patch('docker2ami.ami_builder.socket.socket')
def test_check_port(socket_socket):
    s = socket_socket.return_value
    assert True is ami_builder._check_port('10.0.0.1', 123)
    assert socket_socket.called_with(socket.AF_INET, socket.SOCK_STREAM)
    assert s.connect.called_with(('10.0.0.1', 123))
    assert s.shutdown.called_with(socket.SHUT_RDWR)
    assert s.close.called


@patch('docker2ami.ami_builder.socket.socket')
def test_check_port_error(socket_socket):
    def raise_exception(self):
        raise socket.error()
    s = socket_socket.return_value
    s.connect.side_effect = raise_exception
    assert False is ami_builder._check_port('10.0.0.1', 123)


@pytest.fixture(scope='function')
def config_test_fixtures(request):
    # Get configuration
    request.cls.config = configparser.ConfigParser()

    # Set defaults
    request.cls.section_name = 'section'
    request.cls.defaults = {
        'host_tag': 'docker-build-ami',
        'tmp_dir': '/tmp',
        'image_name': 'docker-build-ami-image',
        'region': 'us-west-1',
        'instance_type': 'm3.medium',
        'subnet_id': 's12345',
        'image_id': 'ami-e4ff5c93',
        'image_user': 'centos',
        'aws_access_key_id': 'myid',
        'aws_secret_access_key': 'mypassword',
        'security_group_ids': '["s12345"]',
        'host_tags': '[{"Key": "Name", "Value": "myname"}]',
        'image_tags': '[{"Key": "Name", "Value": "myimage"}]',
    }
    request.cls.config.add_section(request.cls.section_name)
    for key, val in request.cls.defaults.items():
        request.cls.config.set(request.cls.section_name, key, val)

    # Set overrides
    request.cls.overrides = {
        'host_tag': 'docker-build-ami2',
        'tmp_dir': '/tmp2',
        'image_name': 'docker-build-ami-image2',
        'region': 'us-west-12',
        'instance_type': 'm3.medium2',
        'subnet_id': 's123452',
        'image_id': 'ami-e4ff5c932',
        'image_user': 'centos2',
        'aws_access_key_id': 'myid2',
        'aws_secret_access_key': 'mypassword2',
        'security_group_ids': '[s123452]',
        'host_tags': '[{"Key": "Name2", "Value": "myname2"}]',
        'image_tags': '[{"Key": "Name2", "Value": "myimage2"}]',
    }
    request.cls.overrideobj = EmptyObj()
    for key, val in request.cls.overrides.items():
        setattr(request.cls.overrideobj, key, val)

    # Set overrides with None
    request.cls.override_with_nones_obj = EmptyObj()
    for key, val in request.cls.overrides.items():
        setattr(request.cls.override_with_nones_obj, key, None)


@pytest.mark.usefixtures('config_test_fixtures')
class TestAwsConfig(object):
    def test_initializes_from_config(self):
        target = ami_builder.AwsConfig(self.config, 'section', object())
        for key, val in self.defaults.items():
            assert getattr(target, key) == val

    def test_initializes_from_overrides(self):
        target = ami_builder.AwsConfig(
          self.config, 'section', self.overrideobj)
        for key, val in self.overrides.items():
            assert getattr(target, key) == val

    def test_initializes_from_override_with_nones(self):
        target = ami_builder.AwsConfig(
          self.config, 'section', self.override_with_nones_obj)
        for key, val in self.overrides.items():
            assert getattr(target, key) == self.config.get('section', key)


@pytest.fixture(scope='function')
def config_fixtures(request):
    overrides = {
        'host_tag': 'docker-build-ami2',
        'tmp_dir': '/tmp',
        'image_name': 'docker-build-ami-image2',
        'region': 'us-west-12',
        'instance_type': 'm3.medium2',
        'subnet_id': 's123452',
        'image_id': 'ami-e4ff5c932',
        'image_user': 'centos2',
        'aws_access_key_id': 'myid2',
        'aws_secret_access_key': 'mypassword2',
        'security_group_ids': '["s123452"]',
        'host_tags': '[{"Key": "Name2", "Value": "myname2"}]',
        'image_tags': '[{"Key": "Name2", "Value": "myimage2"}]',
    }
    overrideobj = EmptyObj()
    for key, val in overrides.items():
        setattr(overrideobj, key, val)

    # Get configuration
    config = configparser.ConfigParser()
    request.cls.config = ami_builder.AwsConfig(config, 'main', overrideobj)


@pytest.mark.usefixtures('config_fixtures')
class TestAmiBuilder(object):
    def setup(self):
        self._target = ami_builder.AmiBuilder(self.config)
        self._start_dir = os.getcwd()

    def teardown(self):
        self._target.finish()
        os.chdir(self._start_dir)

    def test_finish_before_start_does_not_raise(self):
        self._target.finish()

    @patch('time.sleep')
    @patch('builtins.print')
    @patch('docker2ami.ami_builder.paramiko')
    @patch('docker2ami.ami_builder._check_port')
    @patch('docker2ami.ami_builder.boto3')
    def test_start(self, boto3, check_port, paramiko, print, sleep):
        ec2 = boto3.client.return_value = MagicMock()
        ec2_resource = boto3.resource.return_value = MagicMock()
        ec2.create_key_pair.return_value = {'KeyMaterial': 'abcdefg'}
        ec2.run_instances.return_value = {
            'ReservationId': '12345',
        }
        ec2.describe_instances.return_value = {
            'Reservations': [
                {'ReservationId': 'ABCDEFG'},
                {'ReservationId': '12345',
                 'Instances': [{
                    'InstanceId': 'i12345',
                    'PrivateIpAddress': '10.0.0.1',
                 }], },
                {'ReservationId': '678910'},
            ]
        }
        instance_obj = ec2_resource.Instance.return_value = MagicMock()
        instance_obj.private_ip_address = '10.0.0.1'
        ii = -1

        def reload_side_effect():
            nonlocal ii
            ii = ii + 1
            instance_obj.state = {'Name': ['starting', 'running'][ii]}

        instance_obj.reload.side_effect = reload_side_effect
        check_port.side_effect = [False, True]
        self._target.start()

        assert boto3.client.called_with(
          'ec2', region_name=self._target._config.region,
          aws_access_key_id=self._target._config.aws_access_key_id,
          aws_secret_access_key=self._target._config.aws_secret_access_key)

        tags = [
            {"Key": "Name2", "Value": "myname2"},
            {"Key": "Name", "Value": self._target._config.host_tag},
        ]
        assert ec2.run_instances.called_with(
            ImageId=self._target._config.image_id,
            KeyName=self._target._key_name,
            InstanceType=self._target._config.instance_type,
            SubnetId=self._target._config.subnet_id,
            MinCount=1,
            MaxCount=1,
            TagSpecifications=[
                {'ResourceType': 'instance', 'Tags': tags},
                {'ResourceType': 'volume', 'Tags': tags},
            ],
            SecurityGroupIds=['s123452'],
        )

        assert paramiko.RSAKey.from_private_key_file.called_with(
            self._target._key_path)
        assert self._target._ssh == paramiko.SSHClient.return_value
        assert self._target._ssh.set_missing_host_key_policy.called_with(
            paramiko.AutoAddPolicy.return_value)
        assert self._target._ssh.connect.called_with(
            hostname='10.0.0.1',
            username='centos2',
            pkey=paramiko.RSAKey.from_private_key_file.return_value
        )

        assert print.has_calls([
          call('Instance: i12345'),
          call('Instance IP: 10.0.0.1'),
          call(f'Connection SSH key: {self._target._key_path}'),
        ])

        assert self._target._instance_obj == instance_obj
        assert self._target._ssh == paramiko.SSHClient.return_value

    @patch('docker2ami.ami_builder.boto3')
    def test_start_throws_when_cant_find_ec2(self, boto3):
        ec2 = boto3.client.return_value = MagicMock()
        ec2.create_key_pair.return_value = {'KeyMaterial': 'abcdefg'}
        with pytest.raises(RuntimeError):
            self._target.start()

    def test_finish_terminates(self):
        instance_obj = self._target._instance_obj = MagicMock()
        self._target.finish()
        assert instance_obj.terminate.called
        assert self._target._instance_obj is None

    @patch('time.sleep')
    @patch('docker2ami.ami_builder.paramiko')
    @patch('docker2ami.ami_builder._check_port')
    @patch('docker2ami.ami_builder.boto3')
    def test_with(self, boto3, check_port, paramiko, sleep):
        ec2 = boto3.client.return_value = MagicMock()
        ec2_resource = boto3.resource.return_value = MagicMock()
        ec2.create_key_pair.return_value = {'KeyMaterial': 'abcdefg'}
        ec2.run_instances.return_value = {
            'ReservationId': '12345',
        }
        ec2.describe_instances.return_value = {
            'Reservations': [
                {'ReservationId': '12345',
                 'Instances': [{
                    'InstanceId': 'i12345',
                    'PrivateIpAddress': '10.0.0.1',
                 }], },
            ]
        }
        instance_obj = ec2_resource.Instance.return_value = MagicMock()
        instance_obj.private_ip_address = '10.0.0.1'

        def reload_side_effect():
            instance_obj.state = {'Name': 'running'}

        instance_obj.reload.side_effect = reload_side_effect
        check_port.return_value = True
        with self._target:
            pass
        assert instance_obj.terminate.called
        assert self._target._instance_obj is None

    @patch('docker2ami.ami_builder.tarfile')
    def test_send_archive(self, tarfile):
        archive_dir = os.path.join(
            os.path.dirname(__file__), 'fixtures/archive')
        os.chdir(archive_dir)
        ssh = self._target._ssh = MagicMock()
        run_cmd = self._target.run_cmd = MagicMock()
        self._target.send_archive()
        tar = tarfile.open.return_value.__enter__.return_value
        assert tar.add.has_calls(
            (call('hello.c'), call('images')),
            any_order=True,
        )
        assert tarfile.open.return_value.__exit__.called
        assert ssh.open_sftp.called
        sftp = ssh.open_sftp.return_value
        assert sftp.put.called_with(
            '/tmp/docker-build-ami.tar.gz', '/tmp/docker-build-ami.tar.gz')
        assert sftp.close.called
        assert run_cmd.called_with(
            '',
            'mkdir /tmp/docker-build-ami; '
            'tar -xzf /tmp/docker-build-ami.tar.gz'
            ' -C /tmp/docker-build-ami')

    @patch('builtins.print')
    def test_run_cmd(self, print):
        ssh = self._target._ssh = MagicMock()
        stdin, stdout, stderr = (MagicMock(), MagicMock(), MagicMock())
        stdout.read.return_value = b'Hello world'
        stderr.read.return_value = b'Error: something bad happened'
        self._target._ssh.exec_command.return_value = (stdin, stdout, stderr)
        stdout.channel.recv_exit_status.return_value = 0
        self._target.run_cmd(
            'FOO=BAR; BAR=BAZ;',
            'echo "hello world" && echo goodbye')
        assert ssh.exec_command.called_with(
          'FOO=BAR; BAR=BAZ; set -ex; echo \'echo "hello world" '
          '&& echo goodbye\' | sudo -i --',
          get_pty=True)
        print.has_calls(
            f'{Color.YELLOW}HelloWorld{Color.CLEAR}',
            f'{Color.RED}Error: something bad happened{Color.CLEAR}',
        )

    @patch('builtins.print')
    def test_run_cmd2(self, print):
        ssh = self._target._ssh = MagicMock()
        stdin, stdout, stderr = (MagicMock(), MagicMock(), MagicMock())
        stdout.read.return_value = b'Hello world'
        stderr.read.return_value = b'Error: something bad happened'
        self._target._ssh.exec_command.return_value = (stdin, stdout, stderr)
        stdout.channel.recv_exit_status.return_value = 0
        self._target.run_cmd(
            'FOO=BAR; BAR=BAZ;',
            'echo "hello world" && echo goodbye')
        assert ssh.exec_command.called_with(
          'FOO=BAR; BAR=BAZ; set -ex; echo \'echo "hello world" '
          '&& echo goodbye\' | sudo -i --',
          get_pty=True)
        print.has_calls(
            f'{Color.YELLOW}HelloWorld{Color.CLEAR}',
            f'{Color.RED}Error: something bad happened{Color.CLEAR}',
        )

    @patch('builtins.exit')
    @patch('builtins.print')
    def test_run_cmd_error(self, print, exit):
        ssh = self._target._ssh = MagicMock()
        stdin, stdout, stderr = (MagicMock(), MagicMock(), MagicMock())
        stdout.read.return_value = b'Hello world'
        stderr.read.return_value = b'Error: something bad happened'
        self._target._ssh.exec_command.return_value = (stdin, stdout, stderr)
        stdout.channel.recv_exit_status.return_value = 123
        self._target.run_cmd(
            'FOO=BAR; BAR=BAZ;',
            'echo "hello world" && echo goodbye')
        assert ssh.exec_command.called_with(
          'FOO=BAR; BAR=BAZ; set -ex; echo \'echo "hello world" '
          '&& echo goodbye\' | sudo -i --',
          get_pty=True)
        assert print.has_calls(
            f'{Color.YELLOW}HelloWorld{Color.CLEAR}',
            f'{Color.RED}Error: something bad happened{Color.CLEAR}',
        )
        assert exit.called_with(123)

    @patch('builtins.print')
    @patch('docker2ami.ami_builder.datetime')
    @patch('time.sleep')
    def test_save_ami(self, sleep, datetime, print):
        instance_obj = self._target._instance_obj = MagicMock()
        instance_obj.instance_id = 'i12345'
        image_obj = instance_obj.create_image.return_value
        image_obj.image_id = 'i54321'
        ec2 = self._target._ec2 = MagicMock()
        datetime.datetime.now.return_value.strftime.return_value =\
            '20191112085423'

        ii = -1

        def image_reload_sideeffect():
            nonlocal ii
            ii = ii + 1
            image_obj.state = ['pending', 'ready']

        self._target.save_ami()

        assert print.has_calls((
            call('\nCreate AMI from instance: i12345'),
            call('\nCreated image: i54321')))
        assert instance_obj.create_image.called_with(
            Name='docker-build-ami-image2-20191112085423')
        assert ec2.create_tags.called_with(
            Resources=['i54321'],
            Tags=self._target._image_tags + [
                {'Key': 'Name', 'Value': self.config.image_name}
            ]
        )
