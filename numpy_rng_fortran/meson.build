project(
  'numpy_rng_fortran',
  'c', 'fortran'
)

py3 = import('python').find_installation(pure: false)

incdir_numpy = run_command(py3,
  [
    '-c',
    'import os; os.chdir(".."); import numpy; print(numpy.get_include())'
  ],
  check: true
).stdout().strip()

inc_np = include_directories(incdir_numpy)

numpy_nodepr_api = '-DNPY_NO_DEPRECATED_API=NPY_1_9_API_VERSION'

cc = meson.get_compiler('c')
npymath_path = incdir_numpy / '..' / 'lib'
npymath_lib = cc.find_library('npymath', dirs: npymath_path)
npyrandom_path = incdir_numpy / '..' / '..' / 'random' / 'lib'
npyrandom_lib = cc.find_library('npyrandom', dirs: npyrandom_path)

executable('numpy_rng_fortran',
    ['main.f90', 'src.c'],
    c_args: numpy_nodepr_api,
    include_directories: [inc_np],
    dependencies: [npyrandom_lib, npymath_lib],
)
