import logging
import os
import pytest

from unittest import mock

from docker2ami.ami_builder import Color
from docker2ami import docker2ami, parser


@pytest.fixture(scope='function')
def docker2ami_fixtures(request):
    request.cls.ami_builder_mock = mock.MagicMock()
    request.cls.parser_state = parser.ParserState()
    request.cls.parser_state.env = "FOO=BAR;"
    request.cls.target = docker2ami.Docker2AmiParserDelegate(
        request.cls.ami_builder_mock, request.cls.parser_state)


@pytest.mark.usefixtures('docker2ami_fixtures')
class TestDocker2Ami(object):
    def test_run_run_invokes_run_cmd(self):
        self.target.run_run('echo hello; echo goodbye')
        assert self.ami_builder_mock.run_cmd.called_with(
            self.parser_state.env,
            'echo hello; echo goodbye')

    def test_run_copy_would_copy(self):
        self.target.run_copy('foo/src', '/dst/place')
        assert self.ami_builder_mock.run_cmd.called_with(
            self.parser_state.env,
            f'cp -rf /tmp/docker-build-ami/foo/src /dst/place')

    def test_run_add_with_file_path_src(self):
        self.target.run_add('docker/foo.json', '/dst/place')
        assert self.ami_builder_mock.run_cmd.called_with(
            self.parser_state.env,
            f'cp -rf /tmp/docker-build-ami/docker/foo.json /dst/place')

    def test_run_add_with_tarball_file_path_src(self):
        for ext in ('tar', 'tar.gz', 'tgz', 'tar.bz', 'tar.xz'):
            self.target.run_add(f'docker/foo.{ext}', '/dst/place')
            assert self.ami_builder_mock.run_cmd.called_with(
                self.parser_state.env,
                f'tar -xpvf /tmp/docker-build-ami/docker/foo.{ext} '
                '-C /dst/place')

    def test_run_add_with_url_src(self):
        for url in (
          'http://www.ginkgobioworks.com/wp-content/uploads/2019/10/foo.png',
          'https://www.ginkgobioworks.com/wp-content/uploads/2019/10/foo.tgz'):
            self.target.run_add(f'{url}', '/dst/place')
            assert self.ami_builder_mock.run_cmd.called_with(
                self.parser_state.env,
                f'curl {url} -o /dst/place')

    @mock.patch('builtins.print')
    def test_run_unknown_prints_message(self, print_mock):
        self.target.run_unknown('echo oops, I forgot the RUN')
        assert print_mock.called_with(
            f'{Color.YELLOW}Unknown Command: '
            f'echo oops, I forgot the RUN{Color.CLEAR}')


@pytest.fixture(scope='function')
def argparser_fixture(request):
    return docker2ami.create_arg_parser()


def assert_args_work(parser, short_flag, long_flag, arg_val):
    def arg_val_getter(args):
        return getattr(args, long_flag[2:].replace('-', '_'))
    args = parser.parse_args([short_flag, arg_val])
    assert arg_val_getter(args) == arg_val
    args = parser.parse_args([long_flag, arg_val])
    assert arg_val_getter(args) == arg_val


def test_accepts_configuration_files(argparser_fixture):
    assert_args_work(argparser_fixture, '-c', '--config', '/foo/bar.cfg')


def test_accepts_debug(argparser_fixture):
    args = argparser_fixture.parse_args([])
    assert args.debug is False
    args = argparser_fixture.parse_args(['-d'])
    assert args.debug is True


def test_accepts_region(argparser_fixture):
    assert_args_work(argparser_fixture, '-r', '--region', 'us-east-1a')


def test_accepts_instance_type(argparser_fixture):
    assert_args_work(argparser_fixture, '-t', '--instance-type', 'a1.large')


def test_accepts_image_name(argparser_fixture):
    assert_args_work(argparser_fixture, '-n', '--image-name', 'my-first-image')


def test_accepts_image_id(argparser_fixture):
    assert_args_work(argparser_fixture, '-i', '--image-id',
                     'my-first-image-id')


def test_accepts_image_user(argparser_fixture):
    assert_args_work(argparser_fixture, '-u', '--image-user', '12345678')


@pytest.fixture(scope='function')
def empty_config_fixture_path(request):
    fixture_dir = os.path.join(os.path.dirname(__file__), 'fixtures')
    return os.path.join(fixture_dir, 'empty.conf')


@pytest.fixture(scope='function')
def example_config_fixture_path(request):
    fixture_dir = os.path.join(os.path.dirname(__file__), 'fixtures')
    return os.path.join(fixture_dir, 'example.conf')


@pytest.fixture(scope='function')
def config_fixture(request):
    return docker2ami.create_config_parser()


def test_reads_empty_config_files(config_fixture, empty_config_fixture_path):
    config_fixture.read(empty_config_fixture_path)
    conf = config_fixture
    assert conf.get('main', 'image_name') == 'docker-build-ami'
    assert conf.get('main', 'image_id') == 'ami-e4ff5c93'
    assert conf.get('main', 'image_user') == 'centos'
    assert conf.get('main', 'region') == 'us-west-1'
    assert conf.get('main', 'subnet_id') == ''
    assert conf.get('main', 'instance_type'), 'm3.medium'
    assert conf.get('main', 'security_group_ids') == '[]'
    assert conf.get('main', 'host_tag') == 'docker-build-ami'
    assert conf.get('main', 'host_tags') == '[]'
    assert conf.get('main', 'image_tags') == '[]'
    assert conf.get('main', 'aws_access_key_id') == ''
    assert conf.get('main', 'aws_secret_access_key') == ''
    assert conf.get('main', 'tmp_dir') == '/tmp'


def test_reads_example_config_files(config_fixture,
                                    example_config_fixture_path):
    config_fixture.read(example_config_fixture_path)
    conf = config_fixture
    assert conf.get('main', 'image_name') == 'ubuntu-test'
    assert conf.get('main', 'image_id') == 'ami-0df67e2624dedbae1'
    assert conf.get('main', 'image_user') == 'ubuntu'
    assert conf.get('main', 'region') == 'eu-east-1'
    assert conf.get('main', 'subnet_id') == 'subnet-123abc45'
    assert conf.get('main', 'instance_type'), 'm5.medium'
    assert conf.get('main', 'security_group_ids') == '["sg-1234", "sg-23456"]'
    assert conf.get('main', 'host_tag') == 'docker-build-ami-host-tag'
    assert conf.get('main', 'host_tags') == '[{"Key": "foo", "Value": "bar"}]'
    assert conf.get('main', 'image_tags') == '[{"Key": "foo", "Value": "baz"}]'
    assert conf.get('main', 'aws_access_key_id') == 'DFSDF3HGDF4SDSD1DDFF'
    assert conf.get('main', 'aws_secret_access_key') == \
        '3riljdsf5SDFSDvsdfds452sdSDFDfsdf44SDFdRA'
    assert conf.get('main', 'tmp_dir') == '/usr/tmp'


@mock.patch('docker2ami.docker2ami.logging.root')
def test_setup_non_debug_logger(root_logger):
    docker2ami.setup_logger(False)
    assert root_logger.setLevel.called_with(logging.WARN)


@mock.patch('docker2ami.docker2ami.logging.root')
def test_setup_debug_logger(root_logger):
    docker2ami.setup_logger(True)
    assert root_logger.setLevel.called_with(logging.DEBUG)


@mock.patch('docker2ami.docker2ami.logging.root')
@mock.patch('docker2ami.docker2ami.os.path.isfile')
def test_get_config_path_valid_non_user_file(isfile, logger):
    isfile.return_value = True
    assert docker2ami.get_config_path('foo.conf') == 'foo.conf'
    assert isfile.called_with('foo.conf')
    assert not logger.error.called


@mock.patch('docker2ami.docker2ami.logging.root')
@mock.patch('docker2ami.docker2ami.os.path.isfile')
def test_get_config_path_valid_user_file(isfile, logger):
    isfile.return_value = True
    assert docker2ami.get_config_path('~/foo.conf') == \
        os.path.expanduser('~/foo.conf')
    assert isfile.called_with(os.path.expanduser('foo.conf'))
    assert not logger.error.called


@mock.patch('docker2ami.docker2ami.logging.root')
@mock.patch('docker2ami.docker2ami.os.path.isfile')
def test_get_config_path_invalid_non_user_file(isfile, logger):
    isfile.return_value = False
    with pytest.raises(SystemExit):
        docker2ami.get_config_path('foo.conf')
    assert isfile.called_with('foo.conf')
    assert logger.error.called


@mock.patch('docker2ami.docker2ami.logging.root')
@mock.patch('docker2ami.docker2ami.os.path.isfile')
def test_get_config_path_invalid_user_file(isfile, logger):
    isfile.return_value = False
    with pytest.raises(SystemExit):
        docker2ami.get_config_path('~/foo.conf')
    assert isfile.called_with(os.path.expanduser('foo.conf'))
    assert logger.error.called


@mock.patch('docker2ami.docker2ami.logging.root')
@mock.patch('docker2ami.docker2ami.os.path.isfile')
def test_get_config_path_default_user_file(isfile, logger):
    isfile.side_effect = (True, False)
    assert docker2ami.get_config_path(None) == \
        os.path.expanduser('~/.docker-build-ami.conf')
    assert isfile.called_with(os.path.expanduser('~/.docker-build-ami.conf'))
    assert not logger.error.called


@mock.patch('docker2ami.docker2ami.logging.root')
@mock.patch('docker2ami.docker2ami.os.path.isfile')
def test_get_config_path_default_file(isfile, logger):
    isfile.side_effect = (False, True)
    assert docker2ami.get_config_path(None) == \
        os.path.expanduser('/etc/docker-build-ami.conf')
    isfile_calls = [mock.call('~/.docker-build-ami.conf'),
                    mock.call('/etc/docker-build-ami.conf')]
    assert isfile.has_calls(isfile_calls)
    assert not logger.error.called


@mock.patch('docker2ami.docker2ami.logging.root')
@mock.patch('docker2ami.docker2ami.os.path.isfile')
def test_get_config_path_no_default_files(isfile, logger):
    isfile.return_value = False
    assert docker2ami.get_config_path(None) is None
    isfile_calls = [mock.call('~/.docker-build-ami.conf'),
                    mock.call('/etc/docker-build-ami.conf')]
    assert isfile.has_calls(isfile_calls)
    assert not logger.error.called


class TestMain(object):
    def setup(self):
        fixture_dir = os.path.join(os.path.dirname(__file__), 'fixtures')
        self.start_dir = os.getcwd()
        os.chdir(os.path.join(fixture_dir, 'coco-dev'))

    def teardown(self):
        os.chdir(self.start_dir)

    @mock.patch('docker2ami.docker2ami.parse_dockerfile_with_delegate')
    @mock.patch('docker2ami.docker2ami.SimpleStateParserDelegate')
    @mock.patch('docker2ami.docker2ami.Docker2AmiParserDelegate')
    @mock.patch('docker2ami.docker2ami.ParserState')
    @mock.patch('docker2ami.docker2ami.AmiBuilder')
    @mock.patch('builtins.open')
    @mock.patch('docker2ami.docker2ami.AwsConfig')
    @mock.patch('docker2ami.docker2ami.create_config_parser')
    @mock.patch('docker2ami.docker2ami.get_config_path')
    @mock.patch('docker2ami.docker2ami.setup_logger')
    @mock.patch('docker2ami.docker2ami.create_arg_parser')
    def test_main_with_args(self, create_arg_parser, setup_logger,
                            get_config_path, create_config_parser, aws_config,
                            open_mock, ami_builder, parser_state,
                            docker2ami_parser_delegate,
                            simple_state_parser_delegate,
                            parse_dockerfile_with_delegate):
        get_config_path.return_value = 'config_file.conf'
        docker2ami.main_with_args(['-c', 'docker-build-ami.conf'])
        assert create_arg_parser.called_with(['-c', 'docker-build-ami.conf'])
        assert setup_logger.called_with(False)
        assert get_config_path.called_with('docker-build-ami.conf')
        assert create_config_parser.called_with('config_file.conf')
        assert aws_config.called_with(
            create_config_parser.return_value, 'main',
            create_arg_parser.return_value)
        assert open_mock.called_with('Dockerfile', 'r')
        assert open_mock.return_value.__enter__.called
        assert ami_builder.called_with(aws_config.return_value)
        assert parser_state.called
        assert docker2ami_parser_delegate.called_with(
            ami_builder.return_value, parser_state.return_value)
        assert simple_state_parser_delegate(ami_builder.return_value,
                                            parser_state.return_value)
        assert ami_builder.return_value.__enter__.return_value \
            .send_archive.called
        assert parse_dockerfile_with_delegate.called_with(
            open_mock.return_value.__enter__.return_value,
            docker2ami_parser_delegate.return_value)
        assert ami_builder.return_value.__enter__.return_value.save_ami.called
        assert ami_builder.return_value.__exit__
        assert open_mock.return_value.__exit__

    @mock.patch('docker2ami.docker2ami.main_with_args')
    @mock.patch('docker2ami.docker2ami.sys')
    def test_main(self, sys, main_with_args):
        sys.argv = ['test_main', '-c', 'docker-build-ami.conf']
        docker2ami.main()
        assert main_with_args.called_with(['-c', 'docker-build-ami.conf'])
