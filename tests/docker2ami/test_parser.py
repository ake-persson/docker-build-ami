import os
import pytest
import re
from unittest import mock

from docker2ami import parser
from docker2ami.ami_builder import Color


def test_bash_arg_regex_str():
    target = re.compile(parser.BASH_ARG_REGEX_STR)
    assert ('FoO12x',) == target.match('FoO12x').groups()
    assert None is target.match(' FoO12x')
    assert ('FoO12x',) == target.match('FoO12x ').groups()
    assert ('foo=bar',) == target.match('foo=bar').groups()
    assert ('"foo"',) == target.match('"foo"').groups()
    assert ('"f \'o\'o"',) == target.match('"f \'o\'o"').groups()
    assert ("'f \"o\"o'",) == target.match("'f \"o\"o'").groups()
    assert ("`'f \"o\"o'`",) == target.match("`'f \"o\"o'`").groups()
    assert (('http://www.me.com?foo=bar',)
            == target.match("http://www.me.com?foo=bar").groups())
    assert (('`http://www.me.com?foo=bar`',)
            == target.match("`http://www.me.com?foo=bar`").groups())


def test_bash_lvalue_regex_str():
    target = re.compile(parser.BASH_LVALUE_REGEX_STR)
    assert ('FoO12x',) == target.match('FoO12x').groups()
    assert None is target.match(' FoO12x')
    assert ('FoO12x',) == target.match('FoO12x ').groups()
    assert ('foo',) == target.match('foo=bar').groups()
    assert ('"foo"',) == target.match('"foo"').groups()
    assert ('"f \'o\'o"',) == target.match('"f \'o\'o"').groups()
    assert ("'f \"o\"o'",) == target.match("'f \"o\"o'").groups()
    assert ("`'f \"o\"o'`",) == target.match("`'f \"o\"o'`").groups()
    assert (('`http://www.me.com?foo=bar`',)
            == target.match("`http://www.me.com?foo=bar`").groups())
    assert (('http://www.me.com?foo',) ==
            target.match("http://www.me.com?foo=bar").groups())


def test_assignment_regex_str():
    target = re.compile(parser.ASSIGNMENT_REGEX_STR)
    assert ('foo', 'bar') == target.match('foo=bar').groups()
    assert ('foo', '"b A r"') == target.match('foo="b A r"').groups()
    assert ('foo', '"b A r"') == target.match('foo "b A r"').groups()
    assert None is not target.match('foo equals bar')


def test_url_regex():
    target = parser.URL_REGEX
    assert None is not target.match('http://www.ginkgobiowors.com/foo?x=y')
    assert None is not target.match('fTp://www.ginkgobiowors.com/foo?x=y')
    assert (None is not
            target.match('twitter://jamie@www.ginkgobiowors.com/foo?x=y'))
    assert (None is not target.match(
              'twitter://jamie:password@www.ginkgobiowors.com/foo?x=y'))
    assert None is target.match('http/foo.bar.baz')


def test_aws_skip_regex():
    target = parser.AWS_SKIP_REGEX
    assert None is not target.match('# AWS-SKIP')
    assert None is not target.match('#AWS-SKIP')
    assert None is not target.match('#    AWS-SKIP   ')
    assert None is not target.match('  #    AWS-SKIP   ')
    assert None is not target.match('  #    AWS-SKIP   \\')
    assert None is target.match('AWS-SKIP')
    assert None is target.match('#aWS-SKIP')


def test_comment_regex():
    target = parser.COMMENT_REGEX
    assert None is not target.match('# AWSSKIP')
    assert None is not target.match('#AWIP')
    assert None is not target.match('#    AP   ')
    assert None is not target.match('  #    AIP   \\')


def test_env_start_regex_str():
    target = re.compile(parser.ENV_START_REGEX_STR, re.IGNORECASE)
    assert None is not target.match('ENV foo=bar')
    assert None is not target.match('ENV foo=bar bar=baz boo=bobby')
    assert None is not target.match(' env foo=bar bar=baz boo=bobby')
    assert None is target.match('ENVx foo=bar')


def test_env_regex():
    target = parser.ENV_REGEX
    assert None is not target.match('ENV foo=bar')
    assert None is not target.match('ENV foo=bar bar=baz boo=bobby')
    assert None is not target.match(' env foo=bar bar=baz boo=bobby')
    assert None is target.match('ENV fo')


def test_env_command_assignments_regex():
    target = parser.ENV_COMMAND_ASSIGNMENTS_REGEX
    assert (('EnV', 'foo=bar bar=baz boo=bobby ')
            == target.match('  EnV  foo=bar bar=baz boo=bobby ').groups())


def test_assignment_regex():
    target = parser.ASSIGNMENT_REGEX
    assert ('foo', 'bar') == target.match('foo=bar').groups()
    assert ('foo', '"b A r"') == target.match('foo="b A r"').groups()
    assert ('foo', '"b A r"') == target.match('foo "b A r"').groups()
    assert ('foo', '"b A r"') == target.match('foo "b A r"').groups()
    assert None is not target.match('foo equals bar')


def test_run_start_regex_str():
    target = re.compile(parser.RUN_START_REGEX_STR, re.IGNORECASE)
    assert None is not target.match('RUN echo hello')
    assert None is not target.match(' run echo hello && goodbye')
    assert None is target.match('RUNNING echo hello')


def test_run_regex():
    target = parser.RUN_REGEX
    assert ('RUN', 'foo=bar',) == target.match('RUN foo=bar').groups()
    assert ('RuN', 'foo=bar',) == target.match(' RuN foo=bar ').groups()
    assert (('RuN', 'foo = bAr && baz=boop',)
            == target.match(' RuN foo = bAr && baz=boop ').groups())


def test_copy_regex():
    target = parser.COPY_REGEX
    assert ('foo', 'bar') == target.match('COPY foo bar').groups()[1:]
    assert (('foo.bar', '/bar/bar')
            == target.match(' CopY foo.bar   /bar/bar  ').groups()[1:])
    assert None is target.match('copying foo.bar   /bar/bar  ')


def test_run_command_commands_regex():
    target = parser.RUN_COMMAND_COMMANDS_REGEX
    assert (('RuN', 'echo hello world  ')
            == target.match('  RuN  echo hello world  ').groups())


def test_add_regex():
    target = parser.ADD_REGEX
    assert ('foo', 'bar') == target.match('ADD foo bar').groups()[1:]
    assert (('foo.bar', '/bar/bar')
            == target.match(' aDd foo.bar   /bar/bar  ').groups()[1:])
    assert (('foo.bar', 'http://www.foo.com/foo?x=y')
            == target.match(' aDd foo.bar  http://www.foo.com/foo?x=y')
            .groups()[1:])
    assert None is target.match('adding foo.bar   /bar/bar  ')


def test_workdir_regex():
    target = parser.WORKDIR_REGEX
    assert ('WORKDIR', '/foo/bar') == \
        target.match('WORKDIR /foo/bar').groups()
    assert ('Workdir', '/foo/bar') == \
        target.match('Workdir /foo/bar  ').groups()
    assert None is target.match('CD /bar/bar  ')


@pytest.fixture(scope='function')
def dockerfile_fixtures(request):
    fixture_dir = os.path.join(os.path.dirname(__file__), 'fixtures')
    request.cls.example_dockerfile_stream = open(
      os.path.join(fixture_dir, 'example_dockerfile'))
    request.cls.env_dockerfile_stream = open(
      os.path.join(fixture_dir, 'env_dockerfile'))
    request.cls.copy_dockerfile_stream = open(
      os.path.join(fixture_dir, 'copy_dockerfile'))
    request.cls.add_dockerfile_stream = open(
      os.path.join(fixture_dir, 'add_dockerfile'))
    request.cls.run_dockerfile_stream = open(
      os.path.join(fixture_dir, 'run_dockerfile'))
    request.cls.workdir_dockerfile_stream = open(
      os.path.join(fixture_dir, 'workdir_dockerfile'))
    request.cls.misc_dockerfile_stream = open(
      os.path.join(fixture_dir, 'misc_dockerfile'))

    yield
    request.cls.example_dockerfile_stream.close()
    request.cls.env_dockerfile_stream.close()
    request.cls.copy_dockerfile_stream.close()
    request.cls.add_dockerfile_stream.close()
    request.cls.run_dockerfile_stream.close()
    request.cls.workdir_dockerfile_stream.close()
    request.cls.misc_dockerfile_stream.close()


@pytest.mark.usefixtures('dockerfile_fixtures')
class TestParseDockerfileWithDelegate(object):
    def test_can_parse(self):
        parser.parse_dockerfile_with_delegate(
          self.example_dockerfile_stream, parser.AbstractParserDelegate())

    @mock.patch('docker2ami.parser.AbstractParserDelegate')
    def test_parses_env(self, mock_delegate):
        parser.parse_dockerfile_with_delegate(
          self.env_dockerfile_stream, mock_delegate)
        assert mock_delegate.has_calls(
          [mock.call.run_env('FOO', 'BAR'),
           mock.call.run_env('HOME', '/root'),
           mock.call.run_env('TZ', ':America/New_York'),
           mock.call.run_env('LANG', 'EN.UTF-8'),
           mock.call.run_env('ME_BASE_HOME', '/usr/src/me-base')])

    @mock.patch('docker2ami.parser.AbstractParserDelegate')
    def test_parses_copy(self, mock_delegate):
        parser.parse_dockerfile_with_delegate(
          self.copy_dockerfile_stream, mock_delegate)
        assert mock_delegate.has_calls(
          [mock.call.run_copy('foo', 'bar'),
           mock.call.run_copy('foo', '.')])

    @mock.patch('docker2ami.parser.AbstractParserDelegate')
    def test_parses_add(self, mock_delegate):
        parser.parse_dockerfile_with_delegate(
          self.add_dockerfile_stream, mock_delegate)
        assert mock_delegate.has_calls(
          [mock.call.run_add('foo', 'bar'),
           mock.call.run_add('foo', '.'),
           mock.call.run_add('http://www.me.com?foo=bar', 'hello.txt')])

    @mock.patch('docker2ami.parser.AbstractParserDelegate')
    def test_parses_workdir(self, mock_delegate):
        parser.parse_dockerfile_with_delegate(
          self.workdir_dockerfile_stream, mock_delegate)
        assert mock_delegate.has_calls(
          [mock.call.run_workdir('/home/docker/app')],
          [mock.call.run_workdir('/home/docker/app')])

    @mock.patch('docker2ami.parser.AbstractParserDelegate')
    def test_parses_run(self, mock_delegate):
        parser.parse_dockerfile_with_delegate(
          self.run_dockerfile_stream, mock_delegate)
        assert mock_delegate.has_calls(
          [mock.call.run_run('apt-get update'),
           mock.call.run_run(
            'apt-get upgrade --assume-yes --verbose-versions '
            '--option Dpkg::Options::="--force-confold"  && apt-get install '
            '--assume-yes --verbose-versions        apt-utils        '
            'binfmt-support        build-essential        curl        '
            'dnsutils        git        htop        iftop        '
            'iotop        iputils-ping        libssl-dev        lsof        '
            'man        mlocate        netcat        pkg-config        '
            'rsync        strace        sudo        tcpdump        '
            'telnet        tzdata        vim        wget')])

    @mock.patch('docker2ami.parser.AbstractParserDelegate')
    def test_parses_misc(self, mock_delegate):
        parser.parse_dockerfile_with_delegate(
          self.misc_dockerfile_stream, mock_delegate)
        assert mock_delegate.has_calls(
          [mock.call.run_nop(),
           mock.call.run_nop(),
           mock.call.run_unknown('FROM phusion/passenger-full:1.0.6'),
           mock.call.run_unknown('LABEL maintainer "Me <me@me.com>"'),
           mock.call.run_nop(),
           mock.call.run_unknown('ARG DEBIAN_FRONTEND=noninteractive'),
           mock.call.run_nop(),
           mock.call.run_unknown('VOLUME $PIP_OVERRIDE_DIR'),
           mock.call.run_unknown('CMD ["/sbin/my_init"]'),
           mock.call.run_nop(),
           mock.call.run_nop(),
           mock.call.run_skip()])


def test_parser_state_initializes_with_right_state():
    target = parser.ParserState()
    assert target.step == 0
    assert target.skip is False
    assert target.env == ''


def test_parser_state_updates_state():
    target = parser.ParserState()
    target.step = target.step + 1
    target.skip = True
    target.env = target.env + 'foo = bar;'
    assert target.step == 1
    assert target.skip is True
    assert target.env == 'foo = bar;'
    target.step = target.step + 1
    target.skip = False
    target.env = target.env + 'foo2 = bar2;'
    assert target.step == 2
    assert target.skip is False
    assert target.env == 'foo = bar;foo2 = bar2;'


@pytest.fixture(scope='function')
def simple_state_parser_delegate_fixtures(request):
    request.cls.parser_delegate = parser.AbstractParserDelegate()
    request.cls.parser_state = parser.ParserState()


@pytest.mark.usefixtures(
  'simple_state_parser_delegate_fixtures', 'dockerfile_fixtures')
class TestSimpleStateParserDelegate(object):
    def setup(self):
        self.target = parser.SimpleStateParserDelegate(
          self.parser_delegate, self.parser_state)

    def test_can_parse(self):
        parser.parse_dockerfile_with_delegate(
          self.example_dockerfile_stream, self.target)

    @mock.patch('docker2ami.parser.AbstractParserDelegate')
    def test_invokes_delegate_when_skip_is_false(self, mock_parser_delegate):
        target = parser.SimpleStateParserDelegate(
          mock_parser_delegate, self.parser_state)
        target.run_nop()
        assert mock_parser_delegate.run_nop.called_with()
        target.run_env('key', 'val')
        assert mock_parser_delegate.run_env.called_with('key', 'val')
        target.run_run('echo hello world')
        assert mock_parser_delegate.run_run.called_with('echo hello world')
        target.run_copy('src', 'dst')
        assert mock_parser_delegate.run_copy.called_with('src', 'dst')
        target.run_add('src', 'dst')
        assert mock_parser_delegate.run_add.called_with('src', 'dst')
        target.run_workdir('/foo/bar')
        assert mock_parser_delegate.run_workdir.called_with('/foo/bar')
        target.run_unknown('FROM foo:jamie')
        assert mock_parser_delegate.run_unknown.called_with('FROM foo:jamie')
        assert self.parser_state.skip is False
        target.run_skip()
        mock_parser_delegate.run_skip_called_with()

    @mock.patch('docker2ami.parser.AbstractParserDelegate')
    def test_invokes_delegate_when_skip_is_true(self, mock_parser_delegate):
        target = parser.SimpleStateParserDelegate(
          mock_parser_delegate, self.parser_state)
        self.parser_state.skip = True
        target.run_nop()
        assert mock_parser_delegate.run_nop.called_with()
        target.run_unknown('FROM foo:jamie')
        assert mock_parser_delegate.run_unknown.called_with('FROM foo:jamie')
        assert self.parser_state.skip
        target.run_skip()
        assert mock_parser_delegate.run_skip.called_with()
        assert self.parser_state.skip

    @mock.patch('docker2ami.parser.AbstractParserDelegate')
    def test_does_not_invoke_delegate_when_skip_is_true(
      self, mock_parser_delegate):
        target = parser.SimpleStateParserDelegate(
          mock_parser_delegate, self.parser_state)

        self.parser_state.skip = True
        target.run_env('key', 'val')
        assert not mock_parser_delegate.run_env.called
        assert self.parser_state.skip is False

        self.parser_state.skip = True
        target.run_run('echo hello world')
        assert not mock_parser_delegate.run_run.called
        assert self.parser_state.skip is False

        self.parser_state.skip = True
        target.run_copy('src', 'dst')
        assert not mock_parser_delegate.run_copy.called
        assert self.parser_state.skip is False

        self.parser_state.skip = True
        target.run_add('src', 'dst')
        assert not mock_parser_delegate.run_add.called
        assert self.parser_state.skip is False

        assert self.parser_state.step == 0

    def test_does_not_sets_skip(self):
        self.target.run_skip()
        assert self.parser_state.skip is True
        self.target.run_skip()
        assert self.parser_state.skip is True

    def test_increments_step(self):
        self.target.run_run('echo hello world')
        assert self.parser_state.step == 1
        self.target.run_env('key', 'val')
        assert self.parser_state.step == 2
        self.target.run_copy('src', 'dst')
        assert self.parser_state.step == 3
        self.target.run_add('src', 'dst')
        assert self.parser_state.step == 4
        self.target.run_workdir('/foo/bar')
        assert self.parser_state.step == 5

    def test_does_not_increment_step(self):
        self.target.run_nop()
        assert self.parser_state.step == 0
        self.target.run_unknown('FROM foo:jamie')
        assert self.parser_state.step == 0
        self.parser_state.skip = True
        self.target.run_run('echo hello world')
        assert self.parser_state.step == 0
        self.parser_state.skip = True
        self.target.run_copy('src', 'dst')
        assert self.parser_state.step == 0
        self.parser_state.skip = True
        self.target.run_add('src', 'dst')
        assert self.parser_state.step == 0
        self.parser_state.skip = True
        self.target.run_skip()
        assert self.parser_state.step == 0

    @mock.patch('builtins.print')
    def test_run_env_prints(self, print_mock):
        self.parser_state.step = 3
        self.target.run_env('FOO', 'BAR')
        assert print_mock.called_with('Step 4: ENV FOO BAR')
        self.parser_state.skip = True
        self.target.run_env('FOO', 'BAR')
        assert print_mock.called_with(f'{Color.DARK_GREY}Skipping for AWS: '
                                      f'ENV FOO BAR{Color.CLEAR}')

    @mock.patch('builtins.print')
    def test_run_run_prints(self, print_mock):
        self.parser_state.step = 3
        self.target.run_run('echo hello')
        assert print_mock.called_with('Step 4: RUN echo hello')
        self.parser_state.skip = True
        self.target.run_run('echo hello')
        assert print_mock.called_with(f'{Color.DARK_GREY}Skipping for AWS: '
                                      f'RUN echo hello{Color.CLEAR}')

    @mock.patch('builtins.print')
    def test_run_copy_prints(self, print_mock):
        self.parser_state.step = 3
        self.target.run_copy('src', 'dst')
        assert print_mock.called_with('Step 4: COPY src dst')
        self.parser_state.skip = True
        self.target.run_copy('src', 'dst')
        assert print_mock.called_with(f'{Color.DARK_GREY}Skipping for AWS: '
                                      f'COPY src dst{Color.CLEAR}')

    @mock.patch('builtins.print')
    def test_run_add_prints(self, print_mock):
        self.parser_state.step = 3
        self.target.run_add('src', 'dst')
        assert print_mock.called_with('Step 4: ADD src dst')
        self.parser_state.skip = True
        self.target.run_add('src', 'dst')
        assert print_mock.called_with(f'{Color.DARK_GREY}Skipping for AWS: '
                                      f'ADD src dst{Color.CLEAR}')

    @mock.patch('builtins.print')
    def test_run_workdir_prints(self, print_mock):
        self.parser_state.step = 3
        self.target.run_workdir('foo')
        assert print_mock.called_with('Step 4: WORKDIR foo')
        self.parser_state.skip = True
        self.target.run_workdir('foo')
        assert print_mock.called_with(f'{Color.DARK_GREY}Skipping for AWS: '
                                      f'WORKDIR foo{Color.CLEAR}')

    @mock.patch('docker2ami.parser.AbstractParserDelegate')
    def test_updates_step_after_invocation(self, mock_parser_delegate):
        target = parser.SimpleStateParserDelegate(
          mock_parser_delegate, self.parser_state)

        def make_step_checker(val):
            def check_step(*args):
                assert self.parser_state.step == val
            return check_step
        mock_parser_delegate.run_run.side_effect = make_step_checker(1)
        target.run_run('echo hello world')
        assert mock_parser_delegate.run_run.called
        mock_parser_delegate.run_add.side_effect = make_step_checker(2)
        target.run_add('src', 'env')
        assert mock_parser_delegate.run_add.called
        mock_parser_delegate.run_copy.side_effect = make_step_checker(3)
        target.run_copy('src', 'env')
        assert mock_parser_delegate.run_copy.called

    @mock.patch('docker2ami.parser.AbstractParserDelegate')
    def test_run_env(self, mock_parser_delegate):
        target = parser.SimpleStateParserDelegate(
          mock_parser_delegate, self.parser_state)

        target.run_env('FOO', 'BAR')
        assert self.parser_state.env == "FOO=BAR;"
        target.run_env('BAR', '`echo hello`')
        assert self.parser_state.env == "FOO=BAR;BAR=`echo hello`;"

    @mock.patch('docker2ami.parser.AbstractParserDelegate')
    def test_run_workdir(self, mock_parser_delegate):
        target = parser.SimpleStateParserDelegate(
          mock_parser_delegate, self.parser_state)

        target.run_workdir('/foo/bar')
        assert self.parser_state.env == "cd /foo/bar;"
        target.run_workdir('bar')
        assert self.parser_state.env == "cd /foo/bar;cd bar;"
