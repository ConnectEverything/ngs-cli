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

NGS_REPO_URL = "https://github.com/connecteverything/ngs-cli"
NGS_LATEST_RELEASE_URL = NGS_REPO_URL + "/releases/latest"
NGS_TAG_URL = NGS_REPO_URL + "/releases/tag/"
NGS_FILENAME_LOOKUP = {
    "darwin": "ngs-darwin-amd64.zip",
    "linux": "ngs-linux-amd64.zip",
    "linux2": "ngs-linux-amd64.zip",
    "win32": "ngs-windows-amd64.zip"
}


NSC_REPO_URL = "https://github.com/nats-io/nsc"
NSC_LATEST_RELEASE_URL = NSC_REPO_URL + "/releases/latest"
# NSC_PROD_RELEASE_URL = NSC_REPO_URL + "/releases/tag/0.5.0"
NSC_TAG_URL = NSC_REPO_URL + "/releases/tag/"
NSC_FILENAME_LOOKUP = {
    "darwin": "nsc-darwin-amd64.zip",
    "linux": "nsc-linux-amd64.zip",
    "win32": "nsc-windows-amd64.zip"
}

def ngs_release_url(platform, tag):
    try:
        filename = NGS_FILENAME_LOOKUP[platform]
    except KeyError:
        print("Unable to locate appropriate filename for", platform)
        sys.exit(1)

    url = NGS_TAG_URL + tag if tag else NGS_LATEST_RELEASE_URL

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

def nsc_release_url(platform, tag):
    try:
        filename = NSC_FILENAME_LOOKUP[platform]
    except KeyError:
        print("Unable to locate appropriate filename for", platform)
        sys.exit(1)

    url = NSC_TAG_URL + tag if tag else NSC_PROD_RELEASE_URL

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

def download_with_progress(msg, url):
    print(msg, url)

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

def mkdir(d):
    if not os.path.exists(d):
        os.mkdir(d)

def add_env(bin_dir):
    home = os.path.expanduser("~")
    ngs_home = os.path.join(home, ".nsc")
    env = os.path.join(ngs_home, "env")
    env_cmd = 'export PATH=' + bin_dir + ':$PATH  #Add NGS utility to the path'
    with open(env, 'w+') as env_file:
        env_file.write(env_cmd + '\n')
    os.chmod(env, 0o744)

def make_bin_dir():
    home = os.path.expanduser("~")
    toolhome = os.path.join(home, ".nsc")
    mkdir(toolhome)
    bin_dir = os.path.join(toolhome, "bin")
    mkdir(bin_dir)
    return bin_dir

def main():

    platform = sys.platform
    if "linux" in platform:
            # convert any linux regardless of version reported to "linux"
            platform = "linux"

    print()
    print("Installing NGS tools for platform: " + platform)

    url = ngs_release_url(platform, sys.argv[1] if len(sys.argv) > 1 else None)
    bin_dir = make_bin_dir()

    ngs_exe_path = os.path.join(bin_dir, "ngs")
    if "windows" in url:
        ngs_exe_path = os.path.join(bin_dir, "ngs.exe")

    compressed = download_with_progress("Downloading NGS installer: ", url)

    if url.endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(compressed), 'r') as z:
            with open(ngs_exe_path, 'wb+') as exe:
                if "windows" not in url:
                    exe.write(z.read('ngs'))
                else:
                    exe.write(z.read('ngs.exe'))
    else:
        # Note: gzip.decompress is not available in python2.
        content = zlib.decompress(compressed, 15 + 32)
        with open(ngs_exe_path, 'wb+') as exe:
            exe.write(content)
    os.chmod(ngs_exe_path, 0o744)

    nsc_exe_path = os.path.join(bin_dir, "nsc")
    if "windows" in url:
        nsc_exe_path = os.path.join(bin_dir, "nsc.exe")

    url = nsc_release_url(platform, sys.argv[1] if len(sys.argv) > 1 else None)
    compressed = download_with_progress("Downloading NSC installer: ", url)

    if url.endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(compressed), 'r') as z:
            with open(nsc_exe_path, 'wb+') as exe:
                if "windows" not in url:
                    exe.write(z.read('nsc'))
                else:
                    exe.write(z.read('nsc.exe'))
    else:
        # Note: gzip.decompress is not available in python2.
        content = zlib.decompress(compressed, 15 + 32)
        with open(nsc_exe_path, 'wb+') as exe:
            exe.write(content)
    os.chmod(nsc_exe_path, 0o744)

    # Add the env helper.
    add_env(bin_dir)

    env_tool = os.path.join('$HOME', '.nsc', 'env')

    print()
    print("The NSC and NGS tools have been installed.")
    print()
    print(nsc_exe_path + " is used to edit, view and deploy NATS security JWTS.")
    print(ngs_exe_path + " can be used to signup for the Synadia global service and manage your billing plan.")
    print()
    print("To add these commands to your $PATH")
    print()
    print("Bash:")
    print("  echo 'export PATH=\"$PATH:%s\"' >> $HOME/.bash_profile" % bin_dir)
    print("  source $HOME/.bash_profile")
    print()
    print("zsh:")
    print("  echo 'export PATH=\"$PATH:%s\"' >> $HOME/.zshrc" % bin_dir)
    print("  source $HOME/.zshrc")
    print()
    print("windows:")
    print("  setx path %%path;\"%s\"" % bin_dir)
    print()
    print("If successful, 'ngs -h' and 'nsc -h' will show the help options.")
    print()
    print("Learn more about signing up at synadia.com.")
    print()


if __name__ == '__main__':
    main()
