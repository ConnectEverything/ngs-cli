#!/bin/sh
# shellcheck disable=SC2039
#   ... we use 'local' as covered below (just beneath the license)
set -eu

# Copyright 2020 The NATS Authors
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

# We are sh, not bash; we might want bash/zsh for associative arrays but some
# OSes are currently on bash3 and removing bash, while we don't want a zsh
# dependency; so we're sticking to "pretty portable shell" even if it's a
# little more convoluted as a result.
#
# We rely upon the following beyond basic POSIX shell:
#  1. A  `local`  command (built-in to shell; almost all sh does have this)
#  2. A  `curl`   command (to download files)
#  3. An `unzip`  command (to extract content from .zip files)
#  4. A  `mktemp` command (to stage a downloaded zip-file)

# We rely upon naming conventions for release assets from GitHub to avoid
# having to parse JSON from their API, to avoid a dependency upon jq(1).
#
# <https://help.github.com/en/github/administering-a-repository/linking-to-releases>
# guarantees that:
#    /<owner>/<name>/releases/latest/download/<asset-name>.zip
# will be available; going via the API we get, for 'latest':
#    https://github.com/connecteverything/ngs-cli/releases/download/v0.11.0/ngs-linux-amd64.zip
# ie:
#    /<owner>/<name>/releases/download/<release>/<asset-name>.zip
# Inspecting headers, the documented guarantee redirects to the API-returned
# URL, which redirects to the S3 bucket download URL.
#    https://github.com/connecteverything/ngs-cli/releases/latest/download/ngs-linux-amd64.zip ->
#  * https://github.com/connecteverything/ngs-cli/releases/download/v0.11.0/ngs-linux-amd64.zip ->
#    <s3-bucket-url-with-auth-query-params>

# Like the Python before us, we only support amd64 for now, and that's all that
# ngs releases.  By calling this out up top, it should make it easier to find
# the places which matter should that change in the future.
readonly RELEASE_ARCH="amd64"

# Finding the releases to download
readonly GITHUB_OWNER_REPO_NGS='connecteverything/ngs-cli'
readonly GITHUB_OWNER_REPO_NSC='nats-io/nsc'
readonly HTTP_USER_AGENT='ngs_install/0.2 (@ConnectEverything)'

# Where to install to, relative to home-dir; both nsc and ngs will go here
readonly RELATIVE_BIN_DIR='.nsc/bin'
# Binary name we are looking for (might have .exe extension on some platforms)
readonly NGS_BINARY_BASENAME='ngs'
readonly NSC_BINARY_BASENAME='nsc'
readonly NSC_PROD_COMPAT_RELEASE='0.5.0'

# Explanations for commands
readonly PURPOSE_NSC='is used to edit, view and deploy NATS security JWTS.'
readonly PURPOSE_NGS='can be used to signup for the Synadia global service and manage your billing plan.'

if [ -n "${ZSH_VERSION:-}" ]; then
  # We mostly just need to unset LOCAL_TRAPS but we might as well
  # emulate sh more fully.
  emulate sh
fi

progname="$(basename "$0" .sh)"
note() { printf >&2 '%s: %s\n' "$progname" "$*"; }
die() { note "$@"; exit 1; }

usage() {
  local ev="${1:-1}"
  [ "$ev" = 0 ] || exec >&2
  cat <<EOUSAGE
Usage: $progname [-N <tag>] [-G <tag>] [-d <dir>] [-s <dir>]
 -d dir     directory to download into [default: ~/$RELATIVE_BIN_DIR]
 -s dir     directory in which to place a symlink to the binary
            [default: ~/bin] [use '-' to forcibly not place a symlink]
 -N tag     retrieve a tagged release of NSC instead of the latest
 -G tag     retrieve a tagged release of NGS instead of the latest
EOUSAGE
  exit "$ev"
}

main() {
  parse_options "$@"
  shift $((OPTIND - 1))
  # error early if missing commands; put it after option processing
  # so that if we need to, we can add options to handle alternatives.
  check_have_external_commands

  # This makes a global $ZIPDIR_PARENT and registers an exit trap:
  make_temp_zipdir_parent

  # mkdir -m does not set permissions of parents; -v is not portable
  # We don't create anything private, so stick to inherited umask.
  mkdir -p -- "$opt_install_dir"

  download_and_install "NGS" "$NGS_BINARY_BASENAME" "$GITHUB_OWNER_REPO_NGS" "$opt_tag_ngs"
  download_and_install "NSC" "$NSC_BINARY_BASENAME" "$GITHUB_OWNER_REPO_NSC" "$opt_tag_nsc"

  show_instructions \
    "$NSC_BINARY_BASENAME" "$PURPOSE_NSC" \
    "$NGS_BINARY_BASENAME" "$PURPOSE_NGS"
}

opt_tag_nsc="$NSC_PROD_COMPAT_RELEASE"
opt_tag_ngs=''
opt_install_dir=''
opt_symlink_dir=''
parse_options() {
  while getopts ':d:hs:G:N:' arg; do
    case "$arg" in
      (h) usage 0 ;;

      (d) opt_install_dir="$OPTARG" ;;
      (s) opt_symlink_dir="$OPTARG" ;;
      (N) opt_tag_nsc="$OPTARG" ;;
      (G) opt_tag_ngs="$OPTARG" ;;

      (:) die "missing required option for -$OPTARG; see -h for help" ;;
      (\?) die "unknown option -$OPTARG; see -h for help" ;;
      (*) die "unhandled option -$arg; CODE BUG" ;;
    esac
  done

  if [ "$opt_install_dir" = "" ]; then
    opt_install_dir="${HOME:?}/${RELATIVE_BIN_DIR}"
  fi
  if [ "$opt_symlink_dir" = "" ] && [ -d "$HOME/bin" ]; then
    opt_symlink_dir="$HOME/bin"
  elif [ "$opt_symlink_dir" = "-" ]; then
    opt_symlink_dir=""
  fi
}

download_and_install() {
  local bin_label bin_basename github_owner_repo explicit_release_tag
  bin_label="${1:?}"
  bin_basename="${2:?}"
  github_owner_repo="${3:?}"
  # the release tag can be empty, so '?' not ':?' :
  explicit_release_tag="${4?}"

  zipfile_url="$(determine_zip_download_url "$bin_basename" "$github_owner_repo" "$explicit_release_tag")"
  [ -n "${zipfile_url}" ] || die "unable to determine a download URL"
  want_filename="$(exe_filename_per_os "$bin_basename")"

  # The unzip command does not work well with piped stdin, we need to have
  # the complete zip-file on local disk.

  zip_dir="$ZIPDIR_PARENT/$bin_basename"
  mkdir -- "$zip_dir"

  stage_zipfile="${zip_dir}/$(zip_filename_per_os "$bin_basename")"

  note "Downloading <${zipfile_url}>"
  curl_cmd --progress-bar --location --output "$stage_zipfile" "$zipfile_url"

  note "Extracting ${want_filename} from $stage_zipfile"
  # But unzip(1) does not let us override permissions and it does not obey
  # umask so the file might now exist with overly broad permissions, depending
  # upon whether or not the local environment has a per-user group which was
  # used.  We don't know that the extracting user wants everyone else in their
  # current group to be able to write to the file.
  # So: extract into the temporary directory, which we've forced via umask to
  # be self-only, chmod while it's safe in there, and then move it into place.
  #   -b is not in busybox, so we rely on unzip handling binary safely
  #   -j junks paths inside the zipfile; none expected, enforce that
  unzip -j -d "$zip_dir" "$stage_zipfile" "$want_filename"
  chmod 0755 "$zip_dir/$want_filename"
  # prompt the user to overwrite if need be
  mv -i -- "$zip_dir/$want_filename" "$opt_install_dir/./"

  link_one_command "$bin_label" "$want_filename"
}

# SIDE-EFFECTS:
# 1. Sets $ZIPDIR_PARENT global
# 2. Registers traps to clean up that directory
make_temp_zipdir_parent() {
  old_umask="$(umask)"
  umask 077

  # This is about as sane as can be managed to be as portable as possible:
  ZIPDIR_PARENT="$(mktemp -d 2>/dev/null || mktemp -d -t 'ziptmpdir')" || \
    die "failed to create a temporary directory with mktemp(1)"

  umask "$old_umask"

  # POSIX does not give rm(1) a `-v` flag.
  # We explicitly want to expand the variable now, shellcheck
  # shellcheck disable=SC2064
  trap "rm -rf -- '${ZIPDIR_PARENT}'" EXIT
}


check_have_external_commands() {
  local cmd

  # Only those commands which take --help :
  for cmd in curl unzip
  do
    "$cmd" --help >/dev/null || die "missing command: $cmd"
  done

  # Our invocation of mktemp has to handle multiple variants; if that's not
  # installed, let it fail later.

  test -e /dev/stdin || die "missing device /dev/stdin"
}

normalized_ostype() {
  local ostype
  # We only need to worry about ASCII here
  # shellcheck disable=SC2018,SC2019
  ostype="$(uname -s | tr A-Z a-z)"
  case "$ostype" in
    (*linux*)  ostype="linux" ;;
    (win32)    ostype="windows" ;;
    (ming*_nt) ostype="windows" ;;
  esac
  printf '%s\n' "$ostype"
}

zip_filename_per_os() {
  local binname="${1:?}"
  printf '%s\n' "${binname}-$(normalized_ostype)-${RELEASE_ARCH}.zip"
}

exe_filename_per_os() {
  local fn="${1:?}"
  case "$(normalized_ostype)" in
    (windows) fn="${fn}.exe" ;;
  esac
  printf '%s\n' "$fn"
}

curl_cmd() {
  curl --user-agent "$HTTP_USER_AGENT" "$@"
}

determine_zip_download_url() {
  local binname owner_repo
  binname="${1:?}"
  owner_repo="${2:?}"
  explicit_tag="${3:-}"
  local want_filename

  want_filename="$(zip_filename_per_os "$binname")"
  if [ -n "$explicit_tag" ]; then
    printf 'https://github.com/%s/releases/download/%s/%s\n' \
      "$owner_repo" "$explicit_tag" "$want_filename"
  else
    printf 'https://github.com/%s/releases/latest/download/%s\n' \
      "$owner_repo" "$want_filename"
  fi
}

dir_is_in_PATH() {
  local needle="$1"
  local oIFS="$IFS"
  local pathdir
  case "$(normalized_ostype)" in
    (windows) IFS=';' ;;
    (*)       IFS=':' ;;
  esac
  # We are explicitly doing splitting to the only array available in portable
  # shell, so yes shellcheck, unquoted is correct
  # shellcheck disable=SC2086
  set $PATH
  IFS="$oIFS"
  for pathdir
  do
    if [ "$pathdir" = "$needle" ]; then
      return 0
    fi
  done
  return 1
}

# Returns true if no further installation instructions are needed;
# Returns false otherwise.
maybe_make_symlink() {
  local target="${1:?need a file to link to}"
  local symdir="${2:?need a directory within which to create a symlink}"
  local linkname="${3:?need a name to give the symlink}"

  if ! [ -d "$symdir" ]; then
    note "skipping symlink because directory does not exist: $symdir"
    return 1
  fi
  # ln(1) `-v` is busybox but is not POSIX
  if ! ln -sf -- "$target" "$symdir/$linkname"
  then
    note "failed to create a symlink in: $symdir"
    return 1
  fi
  ls -ld -- "$symdir/$linkname"
  if dir_is_in_PATH "$symdir"; then
    note "Symlink dir '$symdir' is already in your PATH"
    echo
    return 0
  fi
  note "Symlink dir '$symdir' is not in your PATH?"
  echo
  return 1
}

link_one_command() {
  local label="${1:?need a label}"
  local new_cmd="${2:?need a command which has been installed}"

  local target="$opt_install_dir/$new_cmd"

  echo
  note "${label}: ${target}"
  ls -ld -- "$target"
  echo

  if [ -n "$opt_symlink_dir" ]; then
    if maybe_make_symlink "$target" "$opt_symlink_dir" "$new_cmd"
    then
      return 0
    fi
  fi
}

show_instructions() {
  local cmd purpose
  local show_symlink_alternative=false
  local show_path_bits=true

  printf '\nThe following commands have been installed to %s:\n\n' "$opt_install_dir"
  while [ $# -gt 0 ]; do
    cmd="${1:?}"
    purpose="${2:?}"
    shift 2
    printf ' %s %s\n' "$cmd" "$purpose"
  done

  if [ -n "$opt_symlink_dir" ] && [ -d "$opt_symlink_dir" ]; then
    if dir_is_in_PATH "$opt_symlink_dir"; then
      printf '\nNo PATH manipulation should be needed: symlinks have been put into\n'
      printf 'a dir already in your PATH: %s\n' "$opt_symlink_dir"
      show_path_bits=false
    else
      show_symlink_alternative=true
    fi
  fi

  if $show_path_bits; then
    # We explicitly don't want to expand the $ sign
    # shellcheck disable=SC2016
    printf '\nTo add these commands to your $PATH:\n'

    case "$(normalized_ostype)" in
      (windows) cat <<EOWINDOWS ;;
Windows Cmd Prompt Example:
  setx path %path;"${opt_install_dir}"
EOWINDOWS

      (*) cat <<EOOTHER ;;
Bash Example:
  echo 'export PATH="\${PATH}:${opt_install_dir}"' >> ~/.bashrc
  source ~/.bashrc

Zsh Example:
  echo 'path+=("${opt_install_dir}")' >> ~/.zshrc
  source ~/.zshrc
EOOTHER

    esac
  fi

  if $show_symlink_alternative; then
    printf '\nAlternatively, ensure that %s is in your PATH\nas symlinks has been placed there.' \
      "$opt_symlink_dir"
  fi

  cat <<'EOTRAILER'

If successful, invoke each command with -h to see help options.

Learn more about signing up at synadia.com.
EOTRAILER
}

main "$@"
