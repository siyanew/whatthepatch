# -*- coding: utf-8 -*-

import subprocess

from . import patch, exceptions
from .snippets import which, remove


def apply_patch(diffs):
    """ Not ready for use yet """
    pass

    if isinstance(diffs, patch.diff):
        diffs = [diffs]

    for diff in diffs:
        if diff.header.old_path == '/dev/null':
            text = []
        else:
            with open(diff.header.old_path) as f:
                text = f.read()

        new_text = apply_diff(diff, text)
        with open(diff.header.new_path, 'w') as f:
            f.write(new_text)


def _apply_diff_with_subprocess(diff, lines):
    # call out to patch program
    patchexec = which('patch')
    if not patchexec:
        raise exceptions.SubprocessException('patch program does not exist')

    filepath = '/tmp/wtp-' + str(hash(diff.header))
    oldfilepath = filepath + '.old'
    newfilepath = filepath + '.new'
    rejfilepath = filepath + '.rej'
    patchfilepath = filepath + '.patch'
    with open(oldfilepath, 'w') as f:
        f.write('\n'.join(lines) + '\n')

    with open(patchfilepath, 'w') as f:
        f.write(diff.text)

    args = [patchexec,
            '--quiet',
            '-o', newfilepath,
            '-i', patchfilepath,
            '-r', rejfilepath,
            oldfilepath
            ]
    ret = subprocess.call(args)

    with open(newfilepath) as f:
        lines = f.read().splitlines()

    try:
        with open(rejfilepath) as f:
            rejlines = f.read().splitlines()
    except IOError:
        rejlines = None

    remove(oldfilepath)
    remove(newfilepath)
    remove(rejfilepath)
    remove(patchfilepath)

    # do this last to ensure files get cleaned up
    if ret != 0:
        raise exceptions.SubprocessException('patch program failed', code=ret)

    return lines, rejlines


def apply_diff(diff, text, use_patch=False):
    try:
        lines = text.splitlines()
    except AttributeError:
        lines = list(text)

    if use_patch:
        return _apply_diff_with_subprocess(diff, lines)

    n_lines = len(lines)
    # check that the source text matches the context of the diff
    for old, new, hunk, line in diff.changes:
        # might have to check for line is None here for ed scripts
        if old is not None and line is not None:
            if old > n_lines:
                raise exceptions.HunkApplyException(
                    'context line {n}, "{l}" does not exist in source'.format(
                        n=old,
                        l=line,
                    ),
                    hunk=hunk,
                )
            if lines[old-1] != line:
                raise exceptions.HunkApplyException(
                    'context line {n}, "{l}" does not match "{sl}"'.format(
                        n=old,
                        l=line,
                        sl=lines[old-1]
                    ),
                    hunk=hunk,
                )

    # for calculating the old line
    r = 0
    i = 0

    for old, new, hunk, line in diff.changes:
        if old is not None and new is None:
            del lines[old-1-r+i]
            r += 1
        elif old is None and new is not None:
            lines.insert(new-1, line)
            i += 1
        elif old is not None and new is not None:
            # are we crazy?
            # assert new == old - r + i

            # Sometimes, people remove hunks from patches, making these
            # numbers completely unreliable. Because they're jerks.
            pass

    return lines
