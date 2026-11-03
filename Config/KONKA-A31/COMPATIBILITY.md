# KONKA KOMI A31 native-source firmware

Hardware verified 2026-11-03: MT7981B, 256 MiB RAM, 128 MiB SPI NAND,
board `konka,komi-a31`. Both repositories and branches are from the original CI;
each build records its exact source/feed revisions and resolved configuration.
Per the user's revised requirement, this profile prioritizes complete native
firmware over reproducing the old installed packages or disk layout.

## Firmware and migration

The new source's FIT image, fixed NAND partition table, DSA networking, firewall4
and package manager are retained. No legacy fw3, old kernel settings, private
service scripts or AdGuard/NAS dependency is imposed on the image. DNS uses
native dnsmasq/upstreams until services are manually migrated.

The running 21.02 system uses NMBM, UBI at 0x580000 of length 0x7000000, and
separate kernel/rootfs/rootfs_data volumes. The new native layout uses a FIT
volume and UBI length 0x7a80000. **The resulting sysupgrade.itb is not a direct
in-place upgrade from the old system.** Verify the bootloader, NMBM mapping,
partition transition and recovery method before installation. CI does not flash
the router or package bootloader/NOR/eMMC images as ready-to-flash firmware.
Later migration must account for DSA names and fw4/nftables semantics.

## Components and defaults

- Includes LuCI, HTTPS, Chinese language, IPv6, native firewall, MTK Wi-Fi,
  acceleration/QoS and UPnP. Available native utility packages are added without
  requiring the old ABI/package roster.
- chasey 25.12 selects driver 7.6.7.3 with upstream patch 041 fixing the known
  header-translated port-security/iPhone crash path, and uses ucode Wi-Fi tools.
- Yuzhii 24.10 / Linux 6.6 uses bundled driver 7.6.6.1. Its checked function
  lacks the second vulnerable MacTableLookup path. Runtime reconnect validation
  remains necessary after installation; the old 5.4 module cannot be reused.
- LAN 192.168.0.1, hostname imm, timezone Asia/Shanghai. Native board defaults
  determine port mapping. Radios are initially disabled: configure private SSID
  and key through Ethernet/LuCI before enabling. CN, HE40/HE160 and 5G channel 36
  follow the inspected radio settings where supported.
- ChinaDNS-NG, NAT6/Sunshine, DDNS credentials, certificates, UA-Mask and other
  private services will be configured after the firmware transition. Their old
  state is reference material rather than a build acceptance requirement.
- Public artifacts contain no private Wi-Fi/SSH keys, DDNS tokens or full router
  backups. CI does not modify the router or the unavailable NAS.

`verification.json` distinguishes build acceptance from runtime validation.
Firmware metadata, package manifest, source revisions and SHA256 checksums are
included. Compilation success does not establish migration/boot acceptance.
