#!/usr/bin/env python
"""
Create backups of Google Drive directory.


"""

#  Configure rclone
# > rclone config
#     new_remote (n)
#     name= (symbolic name of the drive)
#     type= (drive)
#     Google Application Client Id (blank)
#     Google Application Client Secret (blank)
#     scope = (drive)
#     root_folder_id> (blank)
#     service_account_file> (blank)
#     Edit advanced config? (n)
#     Use auto config? (y)
#
#     Then the browser asks for authorizing rclone
#
#     Configure this as a team drive? (n)

import argparse
import logging
import os
import sys

import helpers.datetime_ as datetime_
import helpers.dbg as dbg
import helpers.io_ as io_
import helpers.system_interaction as si

_LOG = logging.getLogger(__name__)

# ##############################################################################


def _get_rclone_config(config_name):
    config = {}
    if config_name == "gp_alphamatic":
        # remote:path
        config["name"] = "gp_drive:alphamatic"
    elif config_name == "particle":
        config["name"] = "particle_drive:"
    else:
        raise ValueError("Invalid config_name='%s'" % config_name)
    return config


def _parse():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        '--config', action="store", help="rclone config", required=True)
    parser.add_argument(
        '--action', action="store", choices=['ls', 'backup'], required=True)
    parser.add_argument('--incremental', action="store_true")
    parser.add_argument('--dry_run', action="store_true")
    parser.add_argument(
        '--dst_dir', action="store", default=None, help="Destination dir")
    parser.add_argument(
        "-v",
        dest="log_level",
        default="INFO",
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        help="Set the logging level")
    return parser


def _main(parser):
    args = parser.parse_args()
    dbg.init_logger(verb=args.log_level, use_exec_path=True)
    #
    config = _get_rclone_config(args.config)
    if args.action == "ls":
        cmd = ["rclone ls", config["name"]]
        cmd = " ".join(cmd)
        si.system(cmd, suppress_output=False)
        sys.exit(0)
    if args.action == "backup":
        # Create temp dir.
        temp_dir = "./tmp.gdoc_backup"
        temp_dir = os.path.abspath(temp_dir)
        io_.create_dir(temp_dir, incremental=not args.incremental)
        # Create dst dir.
        dst_dir = args.dst_dir
        dbg.dassert(dst_dir, msg="Need to specify --dst_dir")
        dst_dir = os.path.abspath(dst_dir)
        io_.create_dir(dst_dir, incremental=True)
        # List files.
        timestamp = datetime_.get_timestamp()
        cmd = ["rclone ls", config["name"]]
        cmd = " ".join(cmd)
        output_file = "%s/gdoc_backup.%s.txt" % (dst_dir, timestamp)
        si.system(cmd, output_file=output_file)
        # Clone data inside the temp dir.
        cmd = [
            "rclone copy", config["name"], temp_dir, "--drive-shared-with-me"
            #"--drive-export-formats docx,xlsx,pptx,svg"
        ]
        cmd = " ".join(cmd)
        si.system(cmd, dry_run=args.dry_run)
        # Compress.
        tar_file = "%s/gdoc_backup.%s.tgz" % (dst_dir, timestamp)
        dbg.dassert_not_exists(tar_file)
        cmd = "tar -cf %s -C %s ." % (tar_file, temp_dir)
        si.system(cmd, dry_run=args.dry_run)
        si.system(cmd)
        # Clean up.
        if not args.incremental:
            cmd = "rm -rf %s" % temp_dir
            si.system(cmd, dry_run=args.dry_run)
        # Delete old ones.
        #find $base -type f -mtime +3 -delete
    if args.action == "export":
        # Create dst dir.
        dst_dir = args.dst_dir
        dbg.dassert(dst_dir, msg="Need to specify --dst_dir")
        dst_dir = os.path.abspath(dst_dir)
        io_.create_dir(dst_dir, incremental=True)
        # List files.
        timestamp = datetime_.get_timestamp()
        cmd = ["rclone ls", config["name"]]
        cmd = " ".join(cmd)
        output_file = "%s/gdoc_backup.%s.txt" % (dst_dir, timestamp)
        si.system(cmd, output_file=output_file)
        # Clone data inside the temp dir.
        cmd = [
            "rclone copy", config["name"], temp_dir, "--drive-shared-with-me"
            #"--drive-export-formats docx,xlsx,pptx,svg"
        ]
        cmd = " ".join(cmd)
        si.system(cmd, dry_run=args.dry_run)


if __name__ == '__main__':
    _main(_parse())
