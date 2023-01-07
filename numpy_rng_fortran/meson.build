project(
  'numpy_rng_fortran',
  'cpp', 'fortran',
  default_options: [
    'cpp_std=c++14',
    'fortran_std=legacy',
  ],
)

py = import('python').find_installation(pure: false)

incdir_numpy = run_command(py,
  [
    '-c',
    'import os; os.chdir(".."); import numpy; print(numpy.get_include())'
  ],
  check: true
).stdout().strip()

inc_np = include_directories(incdir_numpy)

incdir_pybind11 = run_command(py, 
  [
    '-c',
    'import os; os.chdir(".."); import pybind11; print(pybind11.get_include())'
  ],
  check: true
).stdout().strip()

inc_pybind11 = include_directories(incdir_pybind11)

numpy_nodepr_api = '-DNPY_NO_DEPRECATED_API=NPY_1_9_API_VERSION'

cpp = meson.get_compiler('cpp')
npyrandom_path = incdir_numpy / '..' / '..' / 'random' / 'lib'
npyrandom_lib = cpp.find_library('npyrandom', dirs: npyrandom_path)

fortran = meson.get_compiler('fortran')

add_project_arguments(
  fortran.get_supported_arguments([
    # '-fall-intrinsics',
    '-Wno-unused-dummy-argument'
  ]),
  language: 'fortran'
)

py.extension_module('rangen',
    ['rangen.fpp', 'rangen.cpp'],
    c_args: numpy_nodepr_api,
    include_directories: [inc_np, inc_pybind11],
    dependencies: [npyrandom_lib],
)
