import os

import sys
import subprocess
import re
import argparse
import logging

WORKING_DIRECTORY = '/home/preston/.archquerywork'
CODEQL_DIR = '/home/preston/ql/'

def get_list_of_packages():
  bad_packages = ['pacman-mirrorlist', 'pacman']
  return [f for f in os.popen('asp list-all | shuf | head -n 5').read().split('\n') if f not in bad_packages]

def check_executables():
  EXECUTABLES = ['asp', 'git', 'wget']
  missing_list = []
  with open('/dev/null', 'w') as f:
    for i in EXECUTABLES:
      if subprocess.call(['which', i], stdout=f, stderr=f) == 1:
        missing_list.append(i)
  if missing_list:
    print('Could not find the following required executables:')
    for i in missing_list:
      print(i)
      return False
  return True


def download_packages(packages):
  handles = []
  for i in packages:
    handles.append(subprocess.Popen(['asp', 'checkout', i]))

  for i in handles:
    i.wait()


def get_package_dirs():
  return [f for f in os.listdir(WORKING_DIRECTORY) if os.path.isdir(os.path.join(WORKING_DIRECTORY, f)) and f != 'codeql_databases']


def pkgbuild_already_modified(line):
  return 'codeql' in line


def modify_PKGBUILDS(dirs):
  for i in dirs:
    pkgbuild = os.path.join(os.path.join(WORKING_DIRECTORY, i), 'trunk/PKGBUILD')
    with open(pkgbuild, 'r') as f:
      lines = f.readlines()

    buildfn_start = None
    for k, v in enumerate(lines):
      if re.match(r'^\s*build\s*\(\)\s*\{\s*$', v):
        buildfn_start = k
        break
    if not buildfn_start:
      raise RuntimeError('Could not find build function for {}'
                         .format(i))

    buildfn_end = None
    for k,v in enumerate(lines[buildfn_start::]):
      if re.match('^\s*}\s*\n$', v):
        buildfn_end = k + buildfn_start
        break

    line_to_modify = buildfn_end - 1
    line_contents = lines[line_to_modify]
    if pkgbuild_already_modified(line_contents):
      raise RuntimeError('PKGBUILD for {} seems to have already been modified'
                         .format(line_contents))
    if appears_to_be_c_or_cpp_pkg(line_contents):
      lines[line_to_modify] = line_to_generate_c_or_cpp_database(line_contents, i)
    elif appears_to_be_python_pkg(line_contents):
      lines[line_to_modify] = line_to_generate_python_database(line_contents, i)
    else:
      raise RuntimeError('We don\'t know what language this line is:\n {}'
                         .format(line_contents))

    print('For package:', i)
    print('build() started at:', buildfn_start)
    print('build() ended at:', buildfn_end)
    print('We modified line:', line_to_modify)
    print('To become:\n', lines[line_to_modify])

    with open(pkgbuild, 'w') as f:
      for i in lines:
        f.write(i)

def line_to_generate_c_or_cpp_database(line, pkg):
  return CODEQL_DIR + 'codeql/codeql database create --language=cpp --command="' + line.strip() + '" ' +  os.path.join(os.path.join(WORKING_DIRECTORY, 'codeql_databases'), pkg) + '\n'


def line_to_generate_python_database(line, pkg):
  return CODEQL_DIR + 'codeql/codeql database create --language=python --command="' + line.strip() + '" ' +  os.path.join(os.path.join(WORKING_DIRECTORY, 'codeql_databases'), pkg) + '\n'


def appears_to_be_python_pkg(line):
  if re.search(r'^.*python.*setup\.py.*$', line):
    return True
  else:
    return False


def appears_to_be_c_or_cpp_pkg(line):
  if re.search(r'^.*make.*$', line) or \
     re.search(r'^.*ninja.*$', line) or \
     re.search(r'^.*Build.*$', line): # put in place for libmilter
    return True
  else:
    return False


def build_databases(dirs):
  build_log = os.path.join(WORKING_DIRECTORY, 'build.log')
  try:
    os.unlink(build_log)
  except FileNotFoundError:
    pass

  codeql_database_directory = os.path.join(WORKING_DIRECTORY, 'codeql_databases')
  if not os.path.exists(codeql_database_directory):
    os.mkdir(codeql_database_directory)

  # TODO figure out how to do this in parallel.
  # Problem is pacman being in use by multiple processes at a time.
  failures = []
  for i in dirs:
    with open(build_log, 'a') as build_log_fd:
      pkgbuild_dir = os.path.join(os.path.join(WORKING_DIRECTORY, i), 'trunk')
      os.chdir(pkgbuild_dir)
      result = subprocess.Popen(['makepkg',
                                 '--noconfirm',
                                 '--nocheck',
                                 '--nosign',
                                 '--noarchive',
                                 '--syncdeps',
                                 '--skipchecksums',
                                 '--skipinteg',
                                 '--skippgpcheck',
                                 '--rmdeps'],
                                 stdout=build_log_fd,
                                 stderr=build_log_fd).wait()
    if result != 0:
      failures.append(i)
  print('=== Build process completed ===')
  if failures:
    print('The following packages failed to build: ')
    for i in failures:
      print(i)


def parse_args():
  parser = argparse.ArgumentParser(description="Download Arch pkgbuilds and use them to generate codeql databases")
  parser.add_argument('--no-download',
                      help="Don't download new pkgbuilds",
                      action='store_true',
                      required=False,
                      default=False)
  parser.add_argument('--no-modify',
                      help="Don't modify pkgbuilds",
                      action='store_true',
                      required=False,
                      default=False)
  parser.add_argument('--no-build',
                      help='Dont build packages/codeql databases.',
                      action='store_true',
                      required=False,
                      default=False)
  return parser.parse_args()


# FIXME: Fails if arch repos haven't been synced recently. Auto sync?
# FIXME: Installing deps before build requires sudo creds
if __name__ == '__main__':
  if not check_executables():
    sys.exit(1)
  args = parse_args()
  os.chdir(WORKING_DIRECTORY)
  if not args.no_download:
    logging.info('Downloading PKGBUILDs')
    download_packages(get_list_of_packages())
  pkg_dirs = get_package_dirs()
  if not args.no_modify:
    logging.info('Modifying PKGBUILDs')
    modify_PKGBUILDS(pkg_dirs)
  if not args.no_build:
    logging.info('Building PKGBUILDs and databases')
    build_databases(pkg_dirs)
