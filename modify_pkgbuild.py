
if __name__ == '__main__':
  with open('PKGBUILD', 'r') as f:
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
  line_contents = '/ql/codeql/codeql database create --language=cpp --command="' + line_contents + '" ./codeqldatabase\n'
  lines[line_to_modify] = line_contents

  with open('PKGBUILD', 'w') as f:
    for i in lines:
      f.write(i)
