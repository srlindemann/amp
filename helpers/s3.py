"""
# Import as:

import helpers.s3 as hs3
"""
from typing import List

import boto3

import helpers.dbg as dbg


def get_path():
    """
    Return the path corresponding to the default s3 bucket.
    Make sure your ~/.aws/credentials uses the right key to access this bucket
    as default.
    """
    # s3_path = "s3://alphamatic"
    s3_path = "s3://default00-bucket"
    return s3_path


def is_s3_path(path):
    return path.startswith("s3://")


def _list_s3_keys(s3_bucket: str, dir_path: str) -> List[str]:
    """
    A wrapper around `list_objects_v2` method that bypasses its
    restriction for only the first 1000 of the contents.
    Returns only the `Key` fields of the `Contents` field, which contain
    file paths.

    Note:
    `list_objects_v2` `StartAfter` parameter lists more files than it
    should. That is why you will get files that are not actually in the
    `dir_path` in your query.

    :param s3_bucket: the name of the bucket
    :param dir_path: path to the directory that needs to be listed
    :return: list of paths
    """
    # Create an s3 object to query.
    s3 = boto3.client("s3")
    # Query until the response is not truncated.
    AMAZON_MAX_INT = 2147483647
    continuation_token = None
    is_truncated = True
    contents_keys = []
    while is_truncated:
        if continuation_token is not None:
            continuation_arg = {"ContinuationToken": continuation_token}
        else:
            continuation_arg = {}
        s3_objects = s3.list_objects_v2(
            Bucket=s3_bucket,
            StartAfter=dir_path,
            MaxKeys=AMAZON_MAX_INT,
            **continuation_arg
        )
        # Extract the `Key` from each element.
        keys = [content["Key"] for content in s3_objects["Contents"]]
        contents_keys.extend(keys)
        continuation_token = s3_objects.get("NextContinuationToken")
        is_truncated = s3_objects["IsTruncated"]
    return contents_keys


def listdir(s3_path: str, mode: str = "recursive") -> List[str]:
    """
    List files in s3 directory.

    :param s3_path: the path to s3 directory, e.g.,
        `s3://default00-bucket/kibot/`
    :param mode: recursive or non-recursive
        If recursive, will list all files in the directory
        recursively. If non-recursive, will list only the top-level
        contents of the directory.
    :return: list of paths
    """
    # Parse the s3_path, extracting bucket and directory.
    dbg.dassert(is_s3_path(s3_path), "s3 path should start with s3://")
    if not s3_path.endswith("/"):
        s3_path = s3_path + "/"
    split_path = s3_path.split("/")
    # For a s3://default00-bucket/kibot/All_Futures_Continuous_Contracts_daily
    # s3_path the split_path would be ['s3:', '', 'default00-bucket',
    # 'kibot', 'All_Futures_Continuous_Contracts_daily', ''].
    s3_bucket = split_path[2]
    dir_path = "/".join(split_path[3:])
    file_names = _list_s3_keys(s3_bucket, dir_path)
    # Filter file names that do not start with the initial `dir_path`,
    # remove `dir_path` from the file names.
    file_names = [
        file_name.replace(dir_path, "", 1)
        for file_name in file_names
        if file_name.startswith(dir_path)
    ]
    # In s3 file system, there is no such thing as directories (the
    # dir_path is just a part of a file name). So to extract top-level
    # components of a directory, we need to extract the first parts of
    # the file names inside this directory.
    #
    # Let's say we are trying to list the contents of `upper_dir`,
    # which contains `lower_dir1` with a `lower_dir1/file_name1` file.
    # At this point, file_names would be `[lower_dir1/file_name1]`
    # If the `mode` is `non-recursive`, we extract `lower-dir` from
    # each file name in this list. If the `mode` is `recursive`, we
    # leave the file names untouched.
    if mode == "recursive":
        paths = file_names
    elif mode == "non-recursive":
        paths = [file_name.split("/")[0] for file_name in file_names]
        paths = list(set(paths))
    else:
        raise ValueError(
            "Only recursive and non-recursive modes are supported, passed %s."
            % mode
        )
    paths.sort()
    return paths
