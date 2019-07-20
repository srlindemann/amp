#!/usr/bin/env python
"""
Given a notebook specified as
    - a ipynb file, e.g.,
        data/web_path_two/Minute_distribution_20180802_182656.ipynb
    - a jupyter url, e.g.,
        https://github.com/...ipynb
    - or a github url

- backup a notebook and publish notebook on shared space;
    > publish_notebook.py --file Task11_Simple_model_for_1min_futures_data.ipynb --action publish
- open a notebook in Chrome
    > publish_notebook.py --file Task11_Simple_model_for_1min_futures_data.ipynb --action open
"""

import argparse
import logging
import os
import sys
from datetime import datetime

import helpers.dbg as dbg
import helpers.system_interaction as si

_LOG = logging.getLogger(__name__)


def get_server_name():
    cmd = "uname -n"
    txt = os.popen(cmd).read().rstrip("\n")
    if txt == "gpmac.local":
        res = txt
    else:
        raise ValueError(
                "Invalid server name='%s'. " % txt +
                "Probably you need to customize the script")
    return res


def add_tag(file_path, tag=None):
    """
    By default add timestamp in filename
    :param file_path:
    :param tag:
    :return: file na
    """
    name, extension = os.path.splitext(os.path.basename(file_path))
    if not tag:
        tag = datetime.now().strftime("_%Y%m%d_%H%M%S")
    return ''.join([name, tag, extension])


def export_html(path_to_notebook):
    """
    Accept ipynb, exports to html, adds a timestamp to the file name, and
    returns the name of the created file
    :param path_to_notebook: The path to the file of the notebook e.g.:
        _data/relevance_and_event_relevance_exploration.ipynb
    :return: The name of the html file with a timestamp e.g.:
        test_notebook_20180802_162438.html
    """
    # Get file name and path to file.
    dir_path = os.path.dirname(os.path.realpath(path_to_notebook))
    file_name = os.path.splitext(os.path.basename(path_to_notebook))[0]
    # Create file name and timestamp.
    file_name_html = file_name + ".html"
    file_name_html = add_tag(file_name_html)
    dst_path = os.path.join(dir_path, file_name_html)
    # Export ipynb to html format.
    cmd = ("jupyter nbconvert {path_to_file} --to html"
           " --output {dst_path}".format(
               path_to_file=path_to_notebook, dst_path=dst_path))
    si.system(cmd, log_level=_LOG.getEffectiveLevel())
    _LOG.debug("Export {file_name} to html".format(file_name=file_name_html))
    return dst_path


def copy_to_folder(path_to_notebook, dst_dir):
    """
    Copy file to another directory
    :param path_to_notebook: The path to the file of the notebook
        e.g.: _data/relevance_and_event_relevance_exploration.ipynb
    :param dst_dir: The folder in which the file will be copied e.g.: _data/
    :return: None
    """
    # file_name = os.path.basename(path_to_notebook)
    dst_f_name = os.path.join(dst_dir, add_tag(path_to_notebook))
    # If there is no such directory, create it.
    if not os.path.isdir(dst_dir):
        os.makedirs(dst_dir)
    # File copying.
    cmd = 'cp {src} {dst}'.format(src=path_to_notebook, dst=dst_f_name)
    si.system(cmd, log_level=_LOG.getEffectiveLevel())
    _LOG.debug("Copy '{nootebook}' to '{dst_dir}'".format(
        nootebook=os.path.basename(path_to_notebook), dst_dir=dst_dir))


def export_to_webpath(path_to_notebook, dst_dir):
    """
    Create a folder if it does not exist. Export ipynb to html, to add a
    timestamp, moves to dst_dir
    :param path_to_notebook: The path to the file of the notebook
        e.g.: _data/relevance_and_event_relevance_exploration.ipynb
    :param dst_dir: destination folder to move
    :return: None
    """
    html_src_path = export_html(path_to_notebook)
    html_name = os.path.basename(html_src_path)
    html_dst_path = os.path.join(dst_dir, html_name)
    # If there is no such directory, create it.
    if not os.path.isdir(dst_dir):
        os.makedirs(dst_dir)
    # Move html.
    _LOG.debug("Export '{html_dst}' to '{dst_dir}'".format(
        html_dst=html_src_path, dst_dir=html_dst_path))
    cmd = 'mv {src} {dst}'.format(src=html_src_path, dst=html_dst_path)
    si.system(cmd, log_level=_LOG.getEffectiveLevel())
    return html_dst_path


def show_file_in_folder(folder_path):
    """
    Print all files in a folder
    :param folder_path:
    :return: None
    """
    # Check the correctness of the entered path
    if not folder_path.endswith('/'):
        folder_path = folder_path + "/"
    only_files = [
        _file for _file in os.listdir(folder_path)
        if os.path.isfile(os.path.join(folder_path, _file))
    ]
    for _one_file in only_files:
        print(folder_path + _one_file)


# TODO (GP): should be able parse url from git and from jupyter.
def get_path(path_or_url):
    """
    Get path from file, local link or github link
    :param path_or_url: url to notebook/github, local path,
        e.g.: https://github.com/...ipynb
    :return: Path to file
        e.g.: UnderstandingAnalysts.ipynb
    """
    ret = ""
    if "https://github" in path_or_url:
        ret = '/'.join(path_or_url.split('/')[7:])
    elif "http://" in path_or_url:
        ret = '/'.join(path_or_url.split('/')[4:])
        dbg.dassert_exists(ret)
        if not os.path.exists(path_or_url):
            # Try to find the file with find basename(ret) in the current
            # client.
            pass
    elif path_or_url.endswith(".ipynb") and os.path.exists(path_or_url):
        ret = path_or_url
    else:
        raise ValueError(
            'Incorrect link to git or local jupiter notebook or file path')
    return ret


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--file",
        action="store",
        required=True,
        type=str,
        help="The path to the file ipynb, jupyter url, or github url")
    parser.add_argument(
        "--web_path",
        type=str,
        action="store",
        help="Save a copy to the specified folder *.ipynb and html with"
        " timestamps in the name")
    parser.add_argument(
        "--project",
        action="store",
        type=str,
        default=None,
        help="An optional project that is used as sub-directory")
    parser.add_argument("--tag", action="store", type=str)
    #
    parser.add_argument(
        "--action",
        action="store",
        default="publish",
        choices=["open", "publish"],
        help="Open with Chrome without publish, or archive / publish as html")
    parser.add_argument(
        "-v",
        dest="log_level",
        default="INFO",
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        help="Set the logging level")
    #
    args = parser.parse_args()
    dbg.init_logger2(args.log_level)
    src_file_name = get_path(args.file)
    # Export to html, add timestamp, archive html.
    if args.action == "open":
        html_path = export_html(src_file_name)
        cmd = "open %s" % html_path
        si.system(cmd)
        sys.exit(0)
    elif args.action == "publish":
        SERVERS = {
            'gpmac.local': {
                'share_path': '/Users/saggese/GoogleDrive/alphamatic/Research/notebooks',
                'backup_path': '/Users/saggese/GoogleDrive/alphamatic/Research/notebooks/backup',
            }
        }
        server_name = get_server_name()
        if server_name in SERVERS:
            share_path = SERVERS[server_name]['share_path']
            backup_path = SERVERS[server_name]['backup_path']
        else:
            raise ValueError("Invalid name='%s'" % server_name)
        if args.project is not None:
            share_path = os.path.join(share_path, args.project)
            backup_path = os.path.join(backup_path, args.project)
        _LOG.info("Server name=%s", server_name)
        _LOG.info("backup path=%s", backup_path)
        _LOG.info("share_path=%s", share_path)
        #
        _LOG.info("# Backing up ipynb")
        copy_to_folder(src_file_name, backup_path)
        #
        _LOG.info("# Publishing html")
        html_file_name = export_to_webpath(src_file_name, share_path)
        _LOG.info("HTML file path is: %s", html_file_name)
        dbg.dassert_exists(html_file_name)
        #
        print("To visualize on Mac run:")
        cmd = (
            "dev_scripts/open_remote_html_mac.sh %s\n" % html_file_name +
            "FILE='%s'; scp 54.172.40.4:$FILE /tmp; open /tmp/$(basename $FILE)"
            % html_file_name)
        print(cmd)
