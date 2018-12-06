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
    print("Downloading", url)

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

    now = int(time.time())
    json = "{\"last_update\":" + str(now) +"}"
    home = os.path.expanduser("~")
    toolhome = os.path.join(home, ".ngs")
    json_fn = os.path.join(toolhome, "ngs.json")
    with open(json_fn, "w") as text_file:
        text_file.write(json)

    print()
    print("NGS installed at: " + exe_fn)
    print()
    print()
    print("Now manually add %s to your $PATH" % bin_dir)
    print()
    print("Bash Example:")
    print("  echo 'export PATH=\"$PATH:%s\"' >> $HOME/.bash_profile" % bin_dir)
    print("  source $HOME/.bash_profile")
    print()
    print("Zsh Example:")
    print("  echo 'export PATH=\"$PATH:%s\"' >> $HOME/.zshrc" % bin_dir)
    print("  source $HOME/.zshrc")
    print()

def mkdir(d):
    if not os.path.exists(d):
        print("mkdir", d)
        os.mkdir(d)


def ngs_bin_dir():
    home = os.path.expanduser("~")
    toolhome = os.path.join(home, ".ngs")
    mkdir(toolhome)
    bin_dir = os.path.join(toolhome, "bin")
    mkdir(bin_dir)
    return bin_dir


if __name__ == '__main__':
    main()