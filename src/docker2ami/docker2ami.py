import argparse
import colorlog
import configparser
import logging
import os
import re
import sys

from .ami_builder import AmiBuilder, AwsConfig, Color
from .parser import AbstractParserDelegate, ParserState, \
    SimpleStateParserDelegate, is_url_arg, parse_dockerfile_with_delegate


class Docker2AmiParserDelegate(AbstractParserDelegate):
    """
    ParserDelegate that creates an AMI using an AmiBuilder
    """
    def __init__(self, ami_builder, parser_state):
        self._ami_builder = ami_builder
        self._parser_state = parser_state

    def run_run(self, cmds):
        self._ami_builder.run_cmd(self._parser_state.env, cmds)

    def run_copy(self, src, dst):
        self._ami_builder.run_cmd(self._parser_state.env,
                                  f'cp -rf /tmp/docker-build-ami/{src} {dst}')

    def run_add(self, src, dst):
        if is_url_arg(src):
            dst = os.path.basename(src) if dst == '.' else dst
            self._ami_builder.run_cmd(
                self._parser_state.env, f'curl {src} -o {dst}')
        else:
            if re.match(r'.*\.(tgz|tar|tar\.gz|tar\.bz|tar\.xz)$', src):
                self._ami_builder.run_cmd(
                    self._parser_state.env,
                    f'tar -xpvf /tmp/docker-build-ami/{src} -C {dst}')
            else:
                self._ami_builder.run_cmd(
                    self._parser_state.env,
                    f'cp -rf /tmp/docker-build-ami/{src} {dst}')

    def run_unknown(self, line):
        print(f'{Color.YELLOW}Unknown Command: {line}{Color.CLEAR}')


def create_arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', help='Configuration file')
    parser.add_argument('-d', '--debug', action='store_true',
                        help='Print debug info')
    parser.add_argument('-r', '--region', help='AWS region')
    parser.add_argument('-t', '--instance-type', help='EC2 instance type')
    parser.add_argument('-s', '--subnet-id', help='AWS subnet id')
    parser.add_argument('-n', '--image-name', help='Target AMI image name')
    parser.add_argument('-i', '--image-id', help='Source AMI image ID')
    parser.add_argument('-u', '--image-user', help='AMI image user')
    return parser


def create_config_parser():
    config = configparser.ConfigParser()
    config.add_section('main')
    config.set('main', 'image_name', 'docker-build-ami')
    config.set('main', 'image_id', 'ami-e4ff5c93')
    config.set('main', 'image_user', 'centos')
    config.set('main', 'region', 'us-west-1')
    config.set('main', 'subnet_id', '')
    config.set('main', 'instance_type', 'm3.medium')
    config.set('main', 'security_group_ids', '[]')
    config.set('main', 'host_tag', 'docker-build-ami')
    config.set('main', 'host_tags', '[]')
    config.set('main', 'image_tags', '[]')
    config.set('main', 'aws_access_key_id', '')
    config.set('main', 'aws_secret_access_key', '')
    config.set('main', 'tmp_dir', '/tmp')
    return config


def setup_logger(debug):
    """ Sets up logging, putting it in debug mode if debug is True """
    # Create formatter
    formatter = colorlog.ColoredFormatter(
      '[%(log_color)s%(levelname)-8s%(reset)s] '
      '%(log_color)s%(message)s%(reset)s')
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger = logging.root
    logger.addHandler(console)
    logger.setLevel(logging.DEBUG if debug else logging.WARN)


def get_config_path(config_path):
    logger = logging.root
    if config_path:
        if os.path.isfile(os.path.expanduser(config_path)):
            cfile = os.path.expanduser(config_path)
        else:
            logger.error('Config file doesn\'t exist: {0}'.format(config_path))
            exit(1)
    elif os.path.isfile(os.path.expanduser('~/.docker-build-ami.conf')):
        cfile = os.path.expanduser('~/.docker-build-ami.conf')
    elif os.path.isfile('/etc/docker-build-ami.conf'):
        cfile = '/etc/docker-build-ami.conf'
    else:
        cfile = None

    return cfile


def main_with_args(argv):
    # get the configuration
    argparser = create_arg_parser()
    args = argparser.parse_args(argv)
    setup_logger(args.debug)
    config = create_config_parser()
    config_path = get_config_path(args.config)
    if config_path:
        config.read(config_path)
    aws_config = AwsConfig(config, 'main', args)

    # check for errors
    if not os.path.isfile('Dockerfile'):
        logging.critical(
            'There needs to be a Dockerfile in the current directory')
        exit(1)
    if not aws_config.aws_access_key_id:
        logging.critical('You need to specify an AWS Access Key ID')
        exit(1)
    if not aws_config.aws_secret_access_key:
        logging.critical('You need to specify a AWS Secret Access Key')
        exit(1)

    # Parse the Dockerfile and create the AMI
    with open('Dockerfile', 'r') as dockerfile:
        with AmiBuilder(aws_config) as ami_builder:
            parser_state = ParserState()
            ami_parser_delegate = Docker2AmiParserDelegate(
                ami_builder, parser_state)
            parser_delegate = SimpleStateParserDelegate(
                ami_parser_delegate, parser_state)
            ami_builder.send_archive()
            parse_dockerfile_with_delegate(dockerfile, parser_delegate)
            ami_builder.save_ami()


def main():
    main_with_args(sys.argv[1:])
