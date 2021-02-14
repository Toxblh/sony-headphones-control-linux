project('sony',
  version: '1.0.0',
  meson_version: '>= 0.40.0'
)

# i18n = import('i18n')
python3 = import('python3')
python = import('python3')
prefix = get_option('prefix')
pkgdatadir = join_paths(prefix, get_option('datadir'), meson.project_name())
DATA_DIR = pkgdatadir
pythondir = join_paths(prefix, python.sysconfig_path('purelib'))
python_dir = pythondir

install_subdir('sony', install_dir: pythondir)
