import os
import sys
import subprocess

WORKING_DIRECTORY = '/home/preston/.archquerywork'

def get_list_of_packages():
  return os.popen('asp list-all | shuf | head -n 5').read().split('\n')


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
  return [f for f in os.listdir(WORKING_DIRECTORY) if os.path.isdir(os.path.join(WORKING_DIRECTORY, f))]


def modify_PKGBUILDS(dirs):
  for i in dirs:
    pkgbuild = os.path.join(os.path.join(WORKING_DIRECTORY, i), 'trunk/PKGBUILD')
    print(pkgbuild)
    input()
    with open(pkgbuild, 'r') as f:
      lines = f.readlines()

    buildfn_start = None
    for k, v in enumerate(lines):
      if 'build() {\n' in v:
        buildfn_start = k
        break

    buildfn_end = None
    for k,v in enumerate(lines[buildfn_end:]):
      if v == '}\n':
        buildfn_end = k
        break

    line_to_modify = buildfn_end - 1
    line_contents = lines[line_to_modify]
    line_contents = '/ql/codeql/codeql database create --language=cpp --command="' + line_contents.strip() + '" ./codeqldatabase\n'
    lines[line_to_modify] = line_contents

    print('For package:', i)
    print('build() started at:', buildfn_start)
    print('build() ended at:', buildfn_end)
    print('We modified line:', line_to_modify)
    print('To become:\n', lines[line_to_modify])

    with open(pkgbuild, 'w') as f:
      for i in lines:
        f.write(i)


if __name__ == '__main__':
  if not check_executables():
    sys.exit(1)
  os.chdir(WORKING_DIRECTORY)
  download_packages(get_list_of_packages())
  modify_PKGBUILDS(get_package_dirs())

