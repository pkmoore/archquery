#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import subprocess
import re
import random
import argparse
import logging

WORKING_DIRECTORY = os.path.join(os.path.expanduser("~"), ".archquerywork")
CODEQL_DIR = os.path.join(os.path.expanduser("~"), "ql")


def sudo_privs_ok():
    """
    Call and parse the output from 'sudo -l' to see if the user is allowed
    to call sudo without entering a password.  Not having this capability is a
    problem because future commands use sudo to install dependencies during the
    package build process.  If a password is required, someone will have to
    manually re-enter it periodically during long-running build operations


    :returns: True if the user can call sudo without a password, otherwise False
    """

    output = (
        subprocess.check_output(["sudo", "-l"]).decode("utf-8").split("\n")
    )
    perms = output[1].strip()
    if perms != "(ALL) NOPASSWD: ALL":
        return False
    return True


def synchronize_package_databases():
    """
    Get the latest info from pacman's repos using 'pacman -Sy'.  We do to
    prevent issues when we go to install dependencies during the build
    process.

    :raises: CalledProcessError if 'pacman -Sy' fails
    """

    logging.info("Updating package databases with 'pacman -Sy'")
    subprocess.check_call(["sudo", "pacman", "-Sy"])


def get_list_of_packages(package_count):
    bad_packages = [
        "pacman-mirrorlist",  # not code
        "pacman",  # may cause problems
        "iotop",  # python
        "sqlmap",  # python
        "ansible",  # python
        "diet-ng",  # Dlang
        "poppler",  # unknown
        "utox",  # build error
        "wine",  # missing deps
        "alacritty",  # rust
        "pantheon-dpms-helper",  # no source found
    ]
    packages = os.popen("asp list-all").read().split("\n")
    # remove haskell packages
    packages = [f for f in packages if "haskell-" not in f]
    # remove python packages
    packages = [f for f in packages if "python-" not in f]
    packages = [f for f in packages if "python2-" not in f]
    # remove perl packages
    packages = [f for f in packages if "perl-" not in f]
    # remove ruby packages
    packages = [f for f in packages if "ruby-" not in f]
    # remove java packages
    packages = [f for f in packages if "java-" not in f]
    # remove rust packages
    packages = [f for f in packages if "rust-" not in f]
    # remove golang packages
    packages = [f for f in packages if "golang-" not in f]
    # remove font packages
    packages = [f for f in packages if "ttf-" not in f]
    # remove 32bit libs
    packages = [f for f in packages if "lib32" not in f]
    # remove sound fonts
    packages = [f for f in packages if "-midi" not in f]

    #existing_databases = get_existing_databases()
    #packages = [f for f in packages if f not in existing_databases]

    # remove "bad" packages we don't want to use for whatever reason
    packages = [f for f in packages if f not in bad_packages]

    random.shuffle(packages)
    return packages[:package_count]


def get_existing_databases():
  return [os.path.basename(os.path.normpath(f.path))
          for f in os.listdir(WORKING_DIRECTORY)
          if os.isdir(f)]


def check_executables():
    EXECUTABLES = ["asp", "git", "wget"]
    missing_list = []
    with open("/dev/null", "w") as f:
        for i in EXECUTABLES:
            if subprocess.call(["which", i], stdout=f, stderr=f) == 1:
                missing_list.append(i)
    if missing_list:
        print("Could not find the following required executables:")
        for i in missing_list:
            print(i)
            return False
    return True


def download_packages(packages):
    handles = []
    for i in packages:
        handles.append(subprocess.Popen(["asp", "checkout", i]))

    for i in handles:
        i.wait()


def populate_packages_from_working_directory():
    logging.info(
        "No packages specified or randomly selected.  "
        "List of packages to be built will be determined by the contents "
        "of the working directory"
    )
    return [
        f
        for f in os.listdir(WORKING_DIRECTORY)
        if os.path.isdir(os.path.join(WORKING_DIRECTORY, f))
        and f != "codeql_databases"
    ]


def pkgbuild_already_modified(line):
    return "codeql" in line


def modify_PKGBUILDS(dirs):
    for i in dirs:
        pkgbuild = os.path.join(
            os.path.join(WORKING_DIRECTORY, i), "trunk/PKGBUILD"
        )
        with open(pkgbuild, "r") as f:
            lines = f.readlines()

        buildfn_start = None
        for k, v in enumerate(lines):
            if re.match(r"^\s*build\s*\(\)\s*\{\s*$", v):
                buildfn_start = k
                break
        if not buildfn_start:
            logging.error("Could not find build function for {}".format(i))
            continue

        buildfn_end = None
        for k, v in enumerate(lines[buildfn_start::]):
            if re.match("^\s*}\s*\n$", v):
                buildfn_end = k + buildfn_start
                break

        line_to_modify = buildfn_end - 1
        line_contents = lines[line_to_modify]
        if pkgbuild_already_modified(line_contents):
            logging.warning(
                "PKGBUILD for {} seems to have already been modified. Is currently:\n{}".format(
                    i, line_contents
                )
            )
            continue
        if appears_to_be_c_or_cpp_pkg(line_contents):
            lines[line_to_modify] = line_to_generate_c_or_cpp_database(
                line_contents, i
            )
        elif appears_to_be_python_pkg(line_contents):
            lines[line_to_modify] = line_to_generate_python_database(
                line_contents, i
            )
        else:
            logging.error(
                "Package: {}\n"
                "We don't know what language this line is:\n {}".format(
                    i, line_contents
                )
            )
            continue

        logging.debug("For package: {}".format(i))
        logging.debug("build() started at: {}".format(buildfn_start))
        logging.debug("build() ended at: {}".format(buildfn_end))
        logging.debug("We modified line: {}".format(line_to_modify))
        logging.debug("To become:\n {}".format(lines[line_to_modify]))

        with open(pkgbuild, "w") as f:
            for i in lines:
                f.write(i)


def line_to_generate_c_or_cpp_database(line, pkg):
    codeql_bin = os.path.join(CODEQL_DIR, 'codeql/codeql')
    return (
        codeql_bin + ' database create --language=cpp --command="'
        + line.strip()
        + '" '
        + os.path.join(
            os.path.join(WORKING_DIRECTORY, "codeql_databases"), pkg
        )
        + "\n"
    )


def line_to_generate_python_database(line, pkg):
    codeql_bin = os.path.join(CODEQL_DIR, 'codeql/codeql')
    return (
        codeql_bin + ' database create --language=python --command="'
        + line.strip()
        + '" '
        + os.path.join(
            os.path.join(WORKING_DIRECTORY, "codeql_databases"), pkg
        )
        + "\n"
    )


def appears_to_be_python_pkg(line):
    if re.search(r"^.*python.*setup\.py.*$", line):
        return True
    else:
        return False


def appears_to_be_c_or_cpp_pkg(line):
    if (
        re.search(r"^.*make.*$", line)
        or re.search(r"^.*ninja.*$", line)
        or re.search(r"^.*Build.*$", line)
        or re.search(r"^.*autogen.*$", line)
    ):
        return True
    else:
        return False


def build_databases(dirs):
    build_log = os.path.join(WORKING_DIRECTORY, "build.log")
    try:
        os.unlink(build_log)
    except FileNotFoundError:
        pass

    codeql_database_directory = os.path.join(
        WORKING_DIRECTORY, "codeql_databases"
    )
    if not os.path.exists(codeql_database_directory):
        os.mkdir(codeql_database_directory)

    # TODO figure out how to do this in parallel.
    # Problem is pacman being in use by multiple processes at a time.
    failures = []
    for i in dirs:
        logging.info("Building and generating database for {}".format(i))
        with open(build_log, "a") as build_log_fd:
            pkgbuild_dir = os.path.join(
                os.path.join(WORKING_DIRECTORY, i), "trunk"
            )
            os.chdir(pkgbuild_dir)
            result = subprocess.Popen(
                [
                    "makepkg",
                    "--noconfirm",
                    "--nocheck",
                    "--nosign",
                    "--noarchive",
                    "--syncdeps",
                    "--skipchecksums",
                    "--skipinteg",
                    "--skippgpcheck",
                    "--rmdeps",
                ],
                stdout=build_log_fd,
                stderr=build_log_fd,
            ).wait()
        if result != 0:
            failures.append(i)
    print("=== Build process completed ===")
    if failures:
        print("The following packages failed to build: ")
        for i in failures:
            print(i)


def parse_args():
    """ Parse command line arguments

    @Notes: This is where the default value (5) for args.package_count comes from
    """
    parser = argparse.ArgumentParser(
        description="Download Arch pkgbuilds and use them to generate codeql databases"
    )
    parser.add_argument(
        "--no-download",
        help="Don't download new pkgbuilds",
        action="store_true",
        required=False,
        default=False,
    )
    parser.add_argument(
        "--package-count",
        help="How many packages should we download",
        required=False,
        type=int,
        default=-1,
    )
    parser.add_argument(
        "--no-modify",
        help="Don't modify pkgbuilds",
        action="store_true",
        required=False,
        default=False,
    )
    parser.add_argument(
        "--no-build",
        help="Dont build packages/codeql databases.",
        action="store_true",
        required=False,
        default=False,
    )
    args = parser.parse_args()
    if args.package_count != -1 and args.no_download:
        parser.error(
            "It is an error to specify --package-count and --no-download at the same time."
        )
    if args.package_count == -1:
        logging.warning("No --package-count specified. Defaulting to 5")
        args.package_count = 5
    return args


if __name__ == "__main__":
    if not check_executables():
        sys.exit(1)
    if not sudo_privs_ok():
        logging.warning(
            "The current user does not have permission to use sudo without a password."
            "This will cause problems when installing dependencies."
            "You will need to monitor the tool and re-enter the users's password periodically!"
        )
    args = parse_args()
    os.chdir(WORKING_DIRECTORY)
    if not args.no_download:
        logging.info("Downloading PKGBUILDs")
        synchronize_package_databases()
        packages = get_list_of_packages(args.package_count)
        download_packages(packages)
    if not packages:
        packages = populate_packages_from_working_directory()
    if not args.no_modify:
        logging.info("Modifying PKGBUILDs")
        modify_PKGBUILDS(packages)
    if not args.no_build:
        logging.info("Building PKGBUILDs and databases")
        build_databases(packages)
