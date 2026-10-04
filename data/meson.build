gnome = import('gnome')

desktopdir = join_paths(datadir, 'applications')
icondir = join_paths(datadir, 'icons', 'hicolor', 'scalable', 'apps')
symbolicicondir = join_paths(datadir, 'icons', 'hicolor', 'symbolic', 'apps')
metainfodir = join_paths(datadir, 'metainfo')
man1dir = join_paths(mandir, 'man1')

conf = configuration_data()
conf.set('version', meson.project_version())
conf.set('version_date', version_date)
conf.set('bindir', bindir)
conf.set('exec', (prefix == '/usr' or prefix == '/app') ? 'cheddar' : join_paths(bindir, 'cheddar'))

manpage = configure_file(
     input: files('cheddar.1.in'),
     output: 'cheddar.1',
     configuration: conf,
)

install_man(
     manpage,
     install_dir: man1dir,
)

about_dialog = configure_file(input: 'ui/AboutDialog.ui.in',
                              output: 'AboutDialog.ui',
                              configuration: conf)

install_data('io.github.rilorca.Cheddar.svg', install_dir: icondir)
foreach size : ['16x16', '24x24', '32x32', '48x48', '64x64', '128x128', '256x256', '512x512']
    install_data(join_paths('icons', size, 'io.github.rilorca.Cheddar.png'),
                 install_dir: join_paths(datadir, 'icons', 'hicolor', size, 'apps'))
endforeach


# AutoPilot fork: systemd user unit for the headless daemon
systemd_service = configure_file(
    input: 'cheddar-autopilot.service.in',
    output: 'cheddar-autopilot.service',
    configuration: conf,
)
install_data(systemd_service,
             install_dir: join_paths(prefix, 'lib', 'systemd', 'user'))
install_data('io.github.rilorca.Cheddar-symbolic.svg', install_dir: symbolicicondir)
install_data('icons/tray/cheddar-tray.png',
             install_dir: join_paths(pkgdatadir, 'icons'))

desktop_in = configure_file(
    input: 'io.github.rilorca.Cheddar.desktop.in.in',
    output: 'io.github.rilorca.Cheddar.desktop.in',
    configuration: conf,
)

i18n.merge_file(input: desktop_in,
                output: 'io.github.rilorca.Cheddar.desktop',
                type: 'desktop',
                po_dir: podir,
                install: true,
                install_dir: desktopdir)

appdata = configure_file(input: 'io.github.rilorca.Cheddar.appdata.xml.in.in',
                         output: 'io.github.rilorca.Cheddar.appdata.xml.in',
                         configuration: conf)

appdata = i18n.merge_file(input: appdata,
                          output: 'io.github.rilorca.Cheddar.appdata.xml',
                          type: 'xml',
                          po_dir: podir,
                          install: true,
                          install_dir: metainfodir)

appstreamcli = find_program('appstreamcli', required: false)
if appstreamcli.found()
  test(
    'validate appdata file',
    appstreamcli,
    args: ['validate', '--no-net', '--pedantic', appdata]
  )
endif

svg_mapping = files('svgs/svg-lookup.ini')

gresource = configure_file(input: 'cheddar.gresource.xml.in',
                           output: 'cheddar.gresource.xml',
                           command: ['generate-cheddar-gresource.xml.py',
                                     join_paths(meson.current_source_dir(), 'cheddar.gresource.xml.in'),
                                     join_paths(meson.current_build_dir(), 'cheddar.gresource.xml'),
                                     join_paths(meson.current_source_dir(), 'svgs')])

gnome.compile_resources('cheddar', gresource,
                        source_dir: '.',
                        dependencies: [about_dialog],
                        gresource_bundle: true,
                        install: true,
                        install_dir: pkgdatadir)
