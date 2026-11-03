#!/usr/bin/env python3
"""Build native A31 firmware and record migration differences for later review."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

PROJECT = Path(os.environ['GITHUB_WORKSPACE'])
PROFILE = PROJECT / 'Config/KONKA-A31'
REPORT = PROJECT / 'build-reports'
SOURCE = os.environ['SOURCE_ID']
REPORT.mkdir(exist_ok=True)


def parse(text):
    result = {}
    for line in text.splitlines():
        m = re.fullmatch(r'(CONFIG_[\w+-]+)=(.*)', line)
        n = re.fullmatch(r'# (CONFIG_[\w+-]+) is not set', line)
        if m:
            result[m[1]] = m[2]
        elif n:
            result[n[1]] = 'n'
    return result


def write_config(values):
    Path('.config').write_text(''.join(
        f'# {key} is not set\n' if value == 'n' else f'{key}={value}\n'
        for key, value in values.items()))


def source_overrides():
    if SOURCE == 'chasey-25.12':
        return {
            'CONFIG_MTK_MT_WIFI_DRIVER_VERSION_7673': 'y',
            'CONFIG_MTK_MT_WIFI_DRIVER_VERSION_7672': 'n',
            'CONFIG_PACKAGE_mtwifi-cfg': 'n',
            'CONFIG_PACKAGE_iwinfo': 'n',
            'CONFIG_PACKAGE_mtwifi-cfg-ucode': 'y',
            'CONFIG_PACKAGE_iwinfo-ucode': 'y',
        }
    return {}


def seed():
    sdk = parse(Path('defconfig/mt7981-ax3000.config').read_text())
    values = {k: v for k, v in sdk.items()
              if k.startswith(('CONFIG_MTK_', 'CONFIG_CONNINFRA_', 'CONFIG_WARP_',
                               'CONFIG_WED_', 'CONFIG_first_card'))}
    old = parse((PROFILE / 'running-build.config').read_text())
    # Retain supported radio tuning, not legacy kernel/package/ABI selections.
    values.update({k: v for k, v in old.items() if k.startswith('CONFIG_MTK_')})
    values.update(parse((PROFILE / 'profile.config').read_text()))
    values.update(source_overrides())
    write_config(values)
    (REPORT / 'requested.config').write_text(Path('.config').read_text())


def packages():
    metadata = Path('tmp/.config-package.in').read_text()
    symbols = set(re.findall(r'^\s*(?:menu)?config (PACKAGE_[\w+.-]+)', metadata, re.M))
    values = parse(Path('.config').read_text())
    requested, unavailable = {}, []
    optional = ['ddns-go', 'luci-app-ddns-go', 'socat', 'luci-app-socat', 'htop',
                'nano', 'tcpdump', 'openssh-sftp-server', 'luci-app-uhttpd',
                'luci-app-package-manager', 'luci-app-opkg']
    for name in optional:
        if 'PACKAGE_' + name in symbols:
            values['CONFIG_PACKAGE_' + name] = 'y'
            requested[name] = name
        else:
            unavailable.append(name)
    values.update(parse((PROFILE / 'profile.config').read_text()))
    values.update(source_overrides())
    write_config(values)
    (REPORT / 'package-resolution.json').write_text(json.dumps({
        'requested': requested, 'unavailable': unavailable,
        'policy': 'native firmware first; old services migrate manually later',
    }, indent=2) + '\n')


CRITICAL = ['firewall4', 'dnsmasq-full', 'ca-bundle', 'luci', 'luci-app-firewall',
            'luci-app-mtwifi-cfg', 'luci-app-turboacc-mtk', 'luci-app-eqos-mtk',
            'luci-app-upnp', 'kmod-mt_wifi', 'odhcp6c', 'dropbear']
FORBIDDEN = ['firewall', 'iptables-zz-legacy', 'ip6tables-zz-legacy']


def audit():
    actual = parse(Path('.config').read_text())
    old = parse((PROFILE / 'running-build.config').read_text())
    missing = [p for p in CRITICAL if actual.get('CONFIG_PACKAGE_' + p) != 'y']
    unexpected = [p for p in FORBIDDEN if actual.get('CONFIG_PACKAGE_' + p, 'n') != 'n']
    assert actual.get('CONFIG_TARGET_mediatek_filogic_DEVICE_konka_komi-a31') == 'y'
    assert actual.get('CONFIG_TARGET_MULTI_PROFILE', 'n') == 'n'
    (REPORT / 'resolved.config').write_text(Path('.config').read_text())
    assert actual.get('CONFIG_IPV6') == 'y'
    differences = {k: {'running': v, 'build': actual.get(k, 'unsupported')}
                   for k, v in old.items() if actual.get(k) != v}
    if SOURCE == 'chasey-25.12':
        patch = Path('package/mtk/drivers/mt_wifi/patches-7673/041-fix-cmm_data-header-translated-port-security.patch')
        assert patch.is_file(), 'Missing iPhone crash fix'
        assert 'RTMPCheckWPAframe' in patch.read_text()
        assert actual.get('CONFIG_MTK_MT_WIFI_DRIVER_VERSION_7673') == 'y'
        wifi = '7.6.7.3 with upstream patch 041; ucode userspace'
    else:
        files = list(Path('package/mtk/drivers/mt_wifi').rglob('cmm_data.c'))
        assert files, 'Bundled 7.6.6.1 source missing'
        text = files[0].read_text(errors='replace')
        start = text.index('rx_802_3_data_frm_announce(')
        body = text[start:]
        # Isolate the complete function using balanced braces.
        begin = body.index('{')
        depth = 0
        for i in range(begin, len(body)):
            depth += (body[i] == '{') - (body[i] == '}')
            if depth == 0:
                body = body[:i+1]
                break
        assert body.count('MacTableLookup(') <= 1, 'Unexpected vulnerable lookup path'
        (REPORT / 'rx_802_3_data_frm_announce.c').write_text(body)
        wifi = 'native 7.6.6.1; second vulnerable MacTableLookup path absent'
    report = {
        'source': SOURCE, 'revision': os.environ['SOURCE_REVISION'],
        'board': 'konka,komi-a31', 'ram_mib': 256, 'nand_mib': 128,
        'critical_missing': missing, 'forbidden_selected': unexpected,
        'wireless': wifi, 'legacy_symbol_differences': differences,
        'package_manager': 'apk' if actual.get('CONFIG_USE_APK') == 'y' else 'opkg',
        'policy': 'native firmware first; manual migration later',
        'direct_sysupgrade_from_running_system_supported': False,
        'migration_required': ['NMBM/fixed NAND mapping', 'UBI kernel/rootfs -> FIT',
                               'bootloader FIT support', 'DSA interface names',
                               'private per-service configurations'],
    }
    (REPORT / 'configuration-audit.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'legacy_symbol_differences'}, indent=2))
    assert not missing, f'Critical packages unavailable: {missing}'
    assert not unexpected, f'Wrong firewall/package manager: {unexpected}'


def collect():
    out = PROJECT / 'a31-artifacts'
    out.mkdir(exist_ok=True)
    target = Path('bin/targets/mediatek/filogic')
    device_files = [p for p in target.iterdir() if 'konka-komi-a31' in p.name.replace('_', '-')]
    images = [p for p in device_files if p.name.endswith('-sysupgrade.itb')]
    assert len(images) == 1, f'Expected one A31 FIT, found {images}'
    manifests = [p for p in device_files if p.suffix == '.manifest']
    if not manifests:
        manifests = list(target.glob('*.manifest'))
    assert manifests, 'Missing per-device manifest'
    installed = {line.split(' - ')[0] for line in manifests[0].read_text().splitlines()}
    missing = set(CRITICAL) - installed
    assert not missing, f'Firmware manifest missing: {missing}'
    assert not set(FORBIDDEN) & installed
    roots = list(Path('build_dir').glob('target-*/root-mediatek'))
    assert len(roots) == 1, roots
    root = roots[0]
    modules = list(root.glob('lib/modules/*/mt_wifi.ko'))
    assert len(modules) == 1, modules
    module = modules[0]
    assert module.read_bytes()[:4] == b'\x7fELF'
    assert images[0].read_bytes()[:4] == bytes.fromhex('d00dfeed'), 'Invalid FIT magic'
    metadata = REPORT / 'firmware-metadata.json'
    subprocess.run(['staging_dir/host/bin/fwtool', '-i', str(metadata), str(images[0])], check=True)
    supported = json.loads(metadata.read_text())['supported_devices']
    assert 'konka,komi-a31' in supported, supported
    for path in [*images, *[p for p in device_files if p.name.endswith('-recovery.itb')],
                 *manifests, *target.glob('*.buildinfo'), *target.glob('profiles.json')]:
        shutil.copy2(path, out / path.name)
    shutil.copytree(REPORT, out / 'reports', dirs_exist_ok=True)
    result = {'build_verified': True, 'runtime_verified': False,
              'direct_sysupgrade_from_running_system_supported': False,
              'supported_devices': supported,
              'wireless_module_sha256': hashlib.sha256(module.read_bytes()).hexdigest(),
              'wireless_module_path': str(module.relative_to(root)),
              'packages': sorted(installed), 'image_bytes': images[0].stat().st_size}
    (out / 'verification.json').write_text(json.dumps(result, indent=2) + '\n')
    shutil.copy2(PROFILE / 'COMPATIBILITY.md', out / 'READ-BEFORE-FLASH.md')
    with (out / 'sha256sums').open('w') as stream:
        for path in sorted(out.rglob('*')):
            if path.is_file() and path.name != 'sha256sums':
                stream.write(f'{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(out).as_posix()}\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'packages'}, indent=2))


if __name__ == '__main__':
    {'seed': seed, 'packages': packages, 'audit': audit, 'collect': collect}[sys.argv[1]]()
