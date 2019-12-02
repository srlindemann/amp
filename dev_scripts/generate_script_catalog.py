#!/usr/bin/env python

"""
Find all the
"""
import os

import argparse
import logging

import helpers.dbg as dbg
import helpers.io_ as io_
import helpers.parser as prsr

import helpers.system_interaction as si

_LOG = logging.getLogger(__name__)

# ##############################################################################

def _get_docstring(file_name):
    _LOG.debug("file_name=%s", file_name)
    txt = io_.from_file(file_name, split=False).split("\n")
    docstring = []
    found = False
    for line in txt:
        _LOG.debug("%s: line='%s'", found, line)
        if any(line.startswith(c) for c in ['"""', '# """', 'r"""']):
            _LOG.debug("-> Found")
            if not found:
                found = True
                continue
            else:
                # Done.
                break
        if found:
            if line.startswith("# "):
                line = line.replace("# ", "")
            docstring.append(line)
    docstring_as_str = "\n".join(docstring)
    _LOG.debug("docstring=%s", docstring_as_str)
    return docstring_as_str


def _parse():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--src_dir", action="store", default=".")
    parser.add_argument("--src_file", action="store", default=None)
    parser.add_argument("--dst_file", action="store",
                        default="documentation/general/script_catalog.md")
    prsr.add_verbosity_arg(parser)
    return parser

import helpers.printing as prnt

def _main(parser):
    args = parser.parse_args()
    dbg.init_logger(verbosity=args.log_level)
    cmd = "find %s -perm +111 -type f" % args.src_dir
    _, output = si.system_to_string(cmd)
    file_names = output.split("\n")
    file_names = sorted(file_names)
    res = {}
    if args.src_file is not None:
        file_names = [args.src_file]
    #file_names = ["dev_scripts/git/gb"]
    #file_names = ["./dev_scripts/_setenv_amp.py"]
    _LOG.info("Files selected: %d", len(file_names))
    num_docstring = 0
    for file_name in file_names:
        docstring = _get_docstring(file_name)
        res[file_name] = docstring
        if docstring:
            num_docstring += 1
    # Compose the catalog.
    last_dir = None
    md_text = []
    for file_name, docstring in res.items():
        file_name = file_name.replace("./", "")
        curr_dir = os.path.dirname(file_name)
        if last_dir is None or last_dir != curr_dir:
            md_text.append("\n# `%s`\n" % curr_dir)
            last_dir = curr_dir
        md_text.append("\n## `%s`\n" % file_name)
        if docstring:
            md_text.append("```\n%s\n```" % docstring)
    # Save in a file.
    md_text_as_str = "\n".join(md_text)
    io_.to_file(args.dst_file, md_text_as_str)
    _LOG.info("File '%s' saved", args.dst_file)
    _LOG.info("Number of scripts with docstring: %s", prnt.perc(
        num_docstring, len(res)))
    # Format the md.
    _LOG.info("Formatting")
    cmd = "linter.py -f %s" % args.dst_file
    si.system(cmd)


if __name__ == "__main__":
    _main(_parse())
