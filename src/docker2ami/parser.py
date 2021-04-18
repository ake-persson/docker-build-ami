#!/usr/bin/env python

import re
from docker2ami.ami_builder import Color


# Match bash args
BASH_ARG_REGEX_STR = r'((?:[^\s"\'\`\\]|(?:\\.))+|(?:\".*(?!\\)\")' \
                     r'|(?:\'.*(?!\\)\')|(?:`.*(?!\\)`))'

# Match bash lvalues
BASH_LVALUE_REGEX_STR = r'((?:[^\s"\'\`\\=]|(?:\\.))+|(?:\".*(?!\\)\")|' \
                        r'(?:\'.*(?!\\)\')|(?:`.*(?!\\)`))'

# Matches foo=bar
ASSIGNMENT_REGEX_STR = BASH_LVALUE_REGEX_STR + r'(?:(?:\s*=\s*)|\s+)' \
                       + BASH_ARG_REGEX_STR

# Match URLs
# See (https://daringfireball.net/2010/07/improved_regex_for_matching_urls)
URL_REGEX = re.compile(
  r'(?i)\b((?:[a-z][\w-]+:(?:/{1,3}|[a-z0-9%])|www\d{0,3}[.]|[a-z0-9.\-]+[.]'
  r'[a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+'
  r'(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:\'".,<>?«»“”‘’]))')

# Matches # AWS-SKIP
AWS_SKIP_REGEX = re.compile(r'^\s*#\s*AWS-SKIP.*$')

# Matches empty lines and comments
COMMENT_REGEX = re.compile(r'^(\s*#.*|)$')

# Matches multi-line lines
MULTI_LINE_REGEX = re.compile(r'(.*)\\\s*$')

# Matches begining of ENV lines
ENV_START_REGEX_STR = r'^\s*(ENV)\s+'

# Matches ENV commands
ENV_REGEX = re.compile(ENV_START_REGEX_STR + r'(' + ASSIGNMENT_REGEX_STR
                       + r'(\s+' + ASSIGNMENT_REGEX_STR + r')*)\s*$',
                       re.IGNORECASE)

# Separate ENV from assigments
ENV_COMMAND_ASSIGNMENTS_REGEX = re.compile(ENV_START_REGEX_STR + r'(.+)$',
                                           re.IGNORECASE)

# Matches FOO=BAR
ASSIGNMENT_REGEX = re.compile(ASSIGNMENT_REGEX_STR, re.IGNORECASE)

# Matches COPY src dst
COPY_REGEX = re.compile(r'\s*(COPY)\s+' + BASH_ARG_REGEX_STR + r'\s+'
                        + BASH_ARG_REGEX_STR + r'\s*\\?\s*$', re.IGNORECASE)

# Matches ADD src dst
ADD_REGEX = re.compile(r'^\s*(ADD)\s+' + BASH_ARG_REGEX_STR + r'\s+'
                       + BASH_ARG_REGEX_STR + r'\s*\\?\s*$', re.IGNORECASE)

# Matches WORKDIR path
WORKDIR_REGEX = re.compile(r'^\s*(WORKDIR)\s+' + BASH_ARG_REGEX_STR
                           + r'\s*\\?\s*$', re.IGNORECASE)

# Matches the beinging of RUN lines
RUN_START_REGEX_STR = r'^\s*(RUN)\s+'

# Mathes RUN do some command now
RUN_REGEX = re.compile(RUN_START_REGEX_STR + r'([^\s]+(?:[^s]+[^\s]+)*)\s*$',
                       re.IGNORECASE)

# Separates RUN from commands to be run
RUN_COMMAND_COMMANDS_REGEX = re.compile(RUN_START_REGEX_STR + r'(.+)$',
                                        re.IGNORECASE)


def is_quoted(str):
    """ whether or not str is quoted """
    return ((len(str) > 2)
            and ((str[0] == "'" and str[-1] == "'")
                 or (str[0] == '"' and str[-1] == '"')))


def is_url_arg(str):
    """ whether or not str is a URL argument """
    return (True if URL_REGEX.match(str[1:-1] if is_quoted(str) else str)
            else False)


def parse_dockerfile_with_delegate(fp, delegate):
    """
    Parses the Dockerfile which is referenced in f, invoking the appropriate
    methods in delegate
    """
    mline = False
    line = ''
    for line0 in fp.read().splitlines():
        # Skip next instruction
        if AWS_SKIP_REGEX.match(line0):
            delegate.run_skip()
            continue

        # Skip empty lines and  comments
        elif COMMENT_REGEX.match(line0):
            delegate.run_nop()
            continue

        # accumulate lines
        append_line = mline
        mline_match = MULTI_LINE_REGEX.match(line0)
        mline = not (mline_match is None)
        line0 = mline_match.groups()[0] if mline else line0
        line = f'{line} {line0}' if append_line else line0
        if mline:
            continue

        # Environment variable
        if ENV_REGEX.match(line):
            assignments_str = \
              ENV_COMMAND_ASSIGNMENTS_REGEX.match(line).groups()[1]
            assignments = ASSIGNMENT_REGEX.findall(assignments_str)
            for (key, value) in assignments:
                delegate.run_env(key, value)

        # Run command
        elif RUN_REGEX.match(line):
            cmds = RUN_COMMAND_COMMANDS_REGEX.match(line).groups()[1]
            delegate.run_run(cmds)

        # Copy command
        elif COPY_REGEX.match(line):
            (op, src, dst) = COPY_REGEX.match(line).groups()
            delegate.run_copy(src, dst)

        # Add command
        elif ADD_REGEX.match(line):
            (op, src, dst) = ADD_REGEX.match(line).groups()
            delegate.run_add(src, dst)

        # Workdir command
        elif WORKDIR_REGEX.match(line):
            (op, path) = WORKDIR_REGEX.match(line).groups()
            delegate.run_workdir(path)

        # Unknown command
        else:
            delegate.run_unknown(line)


class AbstractParserDelegate(object):
    """
    Class responsible for processing on behalf of
    parse_dockerfile_with_delegate
    """
    def run_skip(self):
        """ Invoked when the AWS-SKIP tag is encountered """
        pass

    def run_nop(self):
        """ Invoked when a COMMENT or blank linke is encountered """
        pass

    def run_env(self, key, value):
        """ Invoked when the ENV variable key is assigned value """
        pass

    def run_run(self, cmds):
        """ Invoked when cmds should be run """
        pass

    def run_copy(self, src, dst):
        """ Invoked when src should be copied to dst """
        pass

    def run_add(self, src, dst):
        """ Invoked when src should be added to dst """
        pass

    def run_workdir(self, path):
        """ Invoked when working directory should be changed to path """
        pass

    def run_unknown(self, line):
        """ Invoked when an unknown command is run """
        pass


class ParserState(object):
    """
    Object that holds simple state information such as the step
    number, the skip state and the environment state
    """
    def __init__(self):
        self.step = 0
        self.skip = False
        self.env = ''


class SimpleStateParserDelegate(AbstractParserDelegate):
    """
    ParserDelegate that updates a ParserState object and invokes another
    ParserDelegate.
    """
    def __init__(self, parser_delegate, parser_state):
        self._parser_delegate = parser_delegate
        self._parser_state = parser_state

    def run_skip(self):
        self._parser_state.skip = True
        self._parser_delegate.run_skip()

    def run_nop(self):
        self._parser_delegate.run_nop()

    def run_env(self, key, value):
        if (not self._parser_state.skip):
            self._parser_state.step = self._parser_state.step + 1
            print(f'Step {self._parser_state.step}: ENV {key} {value}')
            self._parser_state.env += f'{key}={value};'
            self._parser_delegate.run_env(key, value)
        else:
            print(f'{Color.DARK_GREY}Skipping for AWS: '
                  f'ENV {key} {value}{Color.CLEAR}')
            self._parser_state.skip = False

    def run_run(self, cmds):
        if (not self._parser_state.skip):
            self._parser_state.step = self._parser_state.step + 1
            print(f'Step {self._parser_state.step}: RUN {cmds}')
            self._parser_delegate.run_run(cmds)
        else:
            print(f'{Color.DARK_GREY}Skipping for AWS: '
                  f'RUN {cmds}{Color.CLEAR}')
            self._parser_state.skip = False

    def run_copy(self, src, dst):
        if (not self._parser_state.skip):
            self._parser_state.step = self._parser_state.step + 1
            print(f'Step {self._parser_state.step}: COPY {src} {dst}')
            self._parser_delegate.run_copy(src, dst)
        else:
            print(f'{Color.DARK_GREY}Skipping for AWS: '
                  f'COPY {src} {dst}{Color.CLEAR}')
            self._parser_state.skip = False

    def run_add(self, src, dst):
        if (not self._parser_state.skip):
            self._parser_state.step = self._parser_state.step + 1
            print(f'Step {self._parser_state.step}: ADD {src} {dst}')
            self._parser_delegate.run_add(src, dst)
        else:
            print(f'{Color.DARK_GREY}Skipping for AWS: '
                  f'ADD {src} {dst}{Color.CLEAR}')
            self._parser_state.skip = False

    def run_workdir(self, path):
        if (not self._parser_state.skip):
            self._parser_state.step = self._parser_state.step + 1
            print(f'Step {self._parser_state.step}: WORKDIR {path}')
            self._parser_state.env += f'cd {path};'
            self._parser_delegate.run_workdir(path)
        else:
            print(f'{Color.DARK_GREY}Skipping for AWS: '
                  f'WORKDIR {path}{Color.CLEAR}')
            self._parser_state.skip = False

    def run_unknown(self, line):
        self._parser_delegate.run_unknown(line)
