# KONKA KOMI A31 — build and migration notes

Baseline inspected 2026-11-03: MT7981B, 256 MiB RAM, 128 MiB SPI NAND;
ImmortalWrt 21.02 / Linux 5.4.284, MTK 7.6.7.3 with the header-translated
port-security fix, fw3 + legacy iptables, dnsmasq -> ChinaDNS-NG 127.0.0.1:5335.

This profile keeps both source repositories from the original CloseWRT-CI.
The source revisions, feed revisions, resolved configuration, package differences
and checksums are included with each build. The default MT7981/MT7986 workflows
are independent and are not invoked by this dedicated workflow.

## Flash compatibility is NOT yet established

The running system uses NMBM and UBI at 0x580000, length 0x7000000,
with separate `kernel`, `rootfs`, `rootfs_data` volumes. Both new sources use
their native fixed-partition DTS, UBI length 0x7a80000, a `fit` volume and DSA.
The old sysupgrade implementation does not support this image layout.
**Do not install the resulting .itb with the old system's sysupgrade or keep its
entire network configuration.** Bootloader support, NMBM mapping and the UBI
layout need a separate migration plan and recovery path. CI does not modify the
device DTS, write the router, or publish bootloader/NOR/eMMC binaries as firmware.

## Differences required by source compatibility

- chasey 25.12: newer kernel; selects MTK 7.6.7.3 and requires source patch
  `041-fix-cmm_data-header-translated-port-security.patch`. Its ucode Wi-Fi
  configuration component replaces the conflicting Lua implementation.
- Yuzhii 24.10 / 6.6: source only supplies MTK 7.6.6.1. The old patched 7.6.7.3
  binary cannot be reused across kernel ABIs. The vulnerable second
  `MacTableLookup` path is absent in the bundled 7.6.6.1 function; hardware
  iPhone reconnect validation is still required after a separately approved install.
- Switch ports use DSA names rather than the old eth0 switch setup. Discover WAN
  and LAN names from the new board defaults before migrating NAT6/Sunshine scripts.
- fw3, legacy IPv4/IPv6 iptables, NAT6 modules and opkg are deliberately retained.
  Firewall4 and nft iptables providers are excluded to preserve existing scripts.
- ChinaDNS-NG uses the same checksum-pinned official static binary and domain
  list as the inspected live system, including the tested Chongqing IPv4/IPv6
  DNS groups. NAS/AdGuard is not required and is not configured as upstream.
- First-boot defaults preserve LAN IP, hostname, timezone and DNS forwarding.
  Radios stay disabled until private Wi-Fi credentials are configured/restored.
  Private SSIDs, passwords, keys, certificates, DDNS tokens and full operational
  backups are not part of this public repository or cloud build artifacts.
- Private NAT6/Sunshine, DDNS, uhttpd certificates/port and UA-Mask settings must
  be migrated individually after interface and firewall checks. Compilation
  success alone does not establish their runtime acceptance on new firmware.

Use `configuration-audit.json` to review unavailable/changed legacy symbols and
packages. Kernel/library ABI package names are resolved against the new source;
unavailable optional old UI utilities are reported rather than silently claimed.
