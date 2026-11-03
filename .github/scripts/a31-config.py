#!/usr/bin/env python3
"""Resolve legacy intent against the original CI source and audit the result."""
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
    # Do not force an obsolete target/toolchain or kernel library ABI.
    values.update({k: v for k, v in old.items()
                   if not k.startswith(('CONFIG_TARGET_', 'CONFIG_TOOLCHAIN'))})
    values.update(parse((PROFILE / 'profile.config').read_text()))
    values.update(source_overrides())
    write_config(values)
    (REPORT / 'requested.config').write_text(Path('.config').read_text())


def packages():
    metadata = Path('tmp/.config-package.in').read_text()
    symbols = set(re.findall(r'^\s*(?:menu)?config (PACKAGE_[\w+.-]+)', metadata, re.M))
    values = parse(Path('.config').read_text())
    # Library ABI suffixes are installed names, not always Kconfig package names.
    aliases = {'iptables': 'iptables-zz-legacy', 'ip6tables': 'ip6tables-zz-legacy',
               'miniupnpd': 'miniupnpd-iptables'}
    if SOURCE == 'chasey-25.12':
        aliases.update({'mtwifi-cfg': 'mtwifi-cfg-ucode', 'iwinfo': 'iwinfo-ucode'})
    requested, unavailable = {}, []
    excluded = {'kernel', 'libc', 'libgcc', 'swconfig', 'switch', 'libiwinfo-lua',
                'luci-app-chinadns-ng'}
    for line in (PROFILE / 'running-packages.txt').read_text().splitlines():
        name = line.split(' - ')[0].strip()
        if not name or name in excluded:
            continue
        mapped = aliases.get(name, name)
        if 'PACKAGE_' + mapped not in symbols:
            lib = re.sub(r'\d+(?:-\d+)*$', '', mapped)
            if mapped.startswith('lib') and 'PACKAGE_' + lib in symbols:
                mapped = lib
            else:
                unavailable.append(name)
                continue
        values['CONFIG_PACKAGE_' + mapped] = 'y'
        requested[name] = mapped
    # Existing ChinaDNS UI uses a different schema; custom service UCI stays canonical.
    values.update(parse((PROFILE / 'profile.config').read_text()))
    values.update(source_overrides())
    write_config(values)
    (REPORT / 'package-resolution.json').write_text(json.dumps({
        'requested': requested, 'unavailable': unavailable,
        'excluded_legacy_components': sorted(excluded),
        'chinadns_ui': 'service UCI retained; stock UI schema is incompatible',
    }, indent=2) + '\n')


CRITICAL = ['firewall', 'iptables-zz-legacy', 'ip6tables-zz-legacy', 'kmod-ipt-nat6',
            'kmod-ipt-tproxy', 'ipset', 'dnsmasq-full', 'chinadns-ng', 'ca-bundle',
            'UAmask', 'ddns-go', 'socat', 'sqm-scripts', 'luci', 'luci-app-mtwifi-cfg',
            'luci-app-turboacc-mtk', 'luci-app-eqos-mtk', 'kmod-mt_wifi', 'opkg']
FORBIDDEN = ['firewall4', 'iptables-nft', 'ip6tables-nft', 'nftables-json',
             'nftables-nojson', 'miniupnpd-nftables', 'apk', 'adguardhome']


def audit():
    actual = parse(Path('.config').read_text())
    old = parse((PROFILE / 'running-build.config').read_text())
    missing = [p for p in CRITICAL if actual.get('CONFIG_PACKAGE_' + p) != 'y']
    unexpected = [p for p in FORBIDDEN if actual.get('CONFIG_PACKAGE_' + p, 'n') != 'n']
    assert actual.get('CONFIG_TARGET_mediatek_filogic_DEVICE_konka_komi-a31') == 'y'
    assert actual.get('CONFIG_TARGET_MULTI_PROFILE', 'n') == 'n'
    assert actual.get('CONFIG_USE_APK', 'n') == 'n'
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
    images = list(target.glob('*konka-komi-a31*-sysupgrade.itb'))
    assert len(images) == 1, f'Expected one A31 FIT, found {images}'
    manifests = list(target.glob('*konka-komi-a31*.manifest'))
    assert manifests, 'Missing per-device manifest'
    installed = {line.split(' - ')[0] for line in manifests[0].read_text().splitlines()}
    missing = set(CRITICAL) - installed
    assert not missing, f'Firmware manifest missing: {missing}'
    assert not set(FORBIDDEN) & installed
    roots = list(Path('build_dir').glob('target-*/root-mediatek'))
    assert len(roots) == 1, roots
    root = roots[0]
    binary = root / 'usr/bin/chinadns-ng'
    binary_hash = hashlib.sha256(binary.read_bytes()).hexdigest()
    assert binary_hash == '3fe0217615dd7060b7287d2b6b31d2a0b364137398bfb335a03bead322eac716'
    domain_hash = hashlib.sha256((root / 'etc/chinadns-ng/chinalist.txt').read_bytes()).hexdigest()
    assert domain_hash == '375424eb7909a83238359a59f56b15abd0fb18bdd47c13347b8da6e1befeb611'
    modules = list(root.glob('lib/modules/*/mt_wifi.ko'))
    assert len(modules) == 1, modules
    module = modules[0]
    assert module.read_bytes()[:4] == b'\x7fELF'
    for path in [*images, *target.glob('*konka-komi-a31*-recovery.itb'),
                 *manifests, *target.glob('*.buildinfo'), *target.glob('profiles.json')]:
        shutil.copy2(path, out / path.name)
    shutil.copytree(REPORT, out / 'reports', dirs_exist_ok=True)
    result = {'build_verified': True, 'runtime_verified': False,
              'direct_sysupgrade_from_running_system_supported': False,
              'chinadns_sha256': binary_hash, 'chinalist_sha256': domain_hash,
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
