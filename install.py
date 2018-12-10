#!/usr/bin/env python

# Copyright 2018 Synadia Communications, Inc
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# This installer mostly inspired by
# https://github.com/denoland/deno_install/blob/master/install.py

from __future__ import print_function

import io
import os
import re
import sys
import time
import zipfile
import zlib

try:
    from urllib.request import urlopen
except ImportError:
    from urllib2 import urlopen

REPO_URL = "https://github.com/connecteverything/ngs-cli"
LATEST_RELEASE_URL = REPO_URL + "/releases/latest"
TAG_URL = REPO_URL + "/releases/tag/"
FILENAME_LOOKUP = {
    "darwin": "ngs-darwin-amd64.zip",
    "linux": "ngs-linux-amd64.zip",
    "linux2": "ngs-linux-amd64.zip",
    "win32": "ngs-windows-amd64.zip"
}


def release_url(platform, tag):
    try:
        filename = FILENAME_LOOKUP[platform]
    except KeyError:
        print("Unable to locate appropriate filename for", platform)
        sys.exit(1)

    url = TAG_URL + tag if tag else LATEST_RELEASE_URL

    try:
        html = urlopen(url).read().decode('utf-8')
    except:
        print("Unable to find release page for", tag)
        sys.exit(1)

    urls = re.findall(r'href=[\'"]?([^\'" >]+)', html)
    matching = [u for u in urls if filename in u]

    if len(matching) != 1:
        print("Unable to find download url for", filename)
        sys.exit(1)

    return "https://github.com" + matching[0]


def download_with_progress(url):
    print("Downloading NGS installer: ", url)

    remote_file = urlopen(url)
    total_size = int(remote_file.headers['Content-Length'].strip())

    data = []
    bytes_read = 0.0

    while True:
        d = remote_file.read(8192)

        if not d:
            print()
            break

        bytes_read += len(d)
        data.append(d)
        sys.stdout.write('\r%2.2f%% downloaded' % (bytes_read / total_size * 100))
        sys.stdout.flush()

    return b''.join(data)


def main():
    bin_dir = ngs_bin_dir()
    exe_fn = os.path.join(bin_dir, "ngs")

    print()
    print("Installing NGS tools for platform: " + sys.platform)

    url = release_url(sys.platform, sys.argv[1] if len(sys.argv) > 1 else None)
    compressed = download_with_progress(url)

    if url.endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(compressed), 'r') as z:
            with open(exe_fn, 'wb+') as exe:
                if "windows" not in url:
                    exe.write(z.read('ngs'))
                else:
                    exe.write(z.read('ngs.exe'))
    else:
        # Note: gzip.decompress is not available in python2.
        content = zlib.decompress(compressed, 15 + 32)
        with open(exe_fn, 'wb+') as exe:
            exe.write(content)
    os.chmod(exe_fn, 0o744)

    # Add the env helper.
    ngs_add_env()

    p_exe_dir = os.path.join('$HOME','.ngs','bin','ngs')
    env_tool = os.path.join('$HOME', '.ngs', 'env')

    print()
    print("The NGS tool has been installed: " + p_exe_dir)
    print()
    print("You will need to extend your $PATH. Place the ")
    print("contents of "+ env_tool + " in your shell setup of choice.")
    print("e.g. 'cat " + env_tool + " >> " + os.path.join('$HOME', '.bashrc') + "'")
    print()
    print("To get started, try 'source " + env_tool + "'")
    print("If successful, 'ngs -h' will show the help options.")
    print()
    print("Signup for a  free account using 'ngs signup --free'.")
    print("When complete, use 'ngs demo echo <msg>' to send your first secure message to the NGS global system.")
    print()

def mkdir(d):
    if not os.path.exists(d):
        os.mkdir(d)

def ngs_add_env():
    home = os.path.expanduser("~")
    ngs_home = os.path.join(home, ".ngs")
    env = os.path.join(ngs_home, "env")
    bin_dir = os.path.join('$HOME', '.ngs','bin')
    env_cmd = 'export PATH=' + bin_dir + ':$PATH  #Add NGS utility to the path'
    with open(env, 'w+') as env_file:
        env_file.write(env_cmd + '\n')
    os.chmod(env, 0o744)

def ngs_bin_dir():
    home = os.path.expanduser("~")
    toolhome = os.path.join(home, ".ngs")
    mkdir(toolhome)
    bin_dir = os.path.join(toolhome, "bin")
    mkdir(bin_dir)
    return bin_dir


if __name__ == '__main__':
    main()
