include $(TOPDIR)/rules.mk

PKG_NAME:=chinadns-ng
PKG_VERSION:=2025.08.09
PKG_RELEASE:=3
PKG_LICENSE:=GPL-3.0-only
PKG_BUILD_DIR:=$(BUILD_DIR)/chinadns-ng-$(PKG_VERSION)

include $(INCLUDE_DIR)/package.mk

define Download/chinadns-a31
  FILE:=chinadns-ng-2025.08.09-aarch64.bin
  URL:=https://github.com/zfl9/chinadns-ng/releases/download/2025.08.09
  URL_FILE:=chinadns-ng%2Bwolfssl%40aarch64-linux-musl%40generic%2Bv8a%40fast%2Blto
  HASH:=3fe0217615dd7060b7287d2b6b31d2a0b364137398bfb335a03bead322eac716
endef
$(eval $(call Download,chinadns-a31))

define Download/chinadns-list-a31
  FILE:=chinadns-list-eb9dc5e02c20f9dbcb81e2f868c6cbfc5fc1727f.conf
  URL:=https://raw.githubusercontent.com/felixonmars/dnsmasq-china-list/eb9dc5e02c20f9dbcb81e2f868c6cbfc5fc1727f
  URL_FILE:=accelerated-domains.china.conf
  HASH:=a49ef80241e832c9e9ebfa26c2309c80fec21c19bcfa3fc9e540cd0fd00301ba
endef
$(eval $(call Download,chinadns-list-a31))

define Package/chinadns-ng
  SECTION:=net
  CATEGORY:=Network
  TITLE:=ChinaDNS-NG with verified IPv4/IPv6 upstream groups
  DEPENDS:=@aarch64 +ca-bundle
  URL:=https://github.com/zfl9/chinadns-ng
endef

define Package/chinadns-ng/conffiles
/etc/config/chinadns-ng
/etc/chinadns-ng/chinalist.txt
/etc/chinadns-ng/gfwlist.txt
endef

# Keep the checksum of the upstream static executable intact.
RSTRIP:=:

define Build/Prepare
	mkdir -p $(PKG_BUILD_DIR)
	cp $(DL_DIR)/chinadns-ng-2025.08.09-aarch64.bin $(PKG_BUILD_DIR)/chinadns-ng
	{ sed -n 's@^server=/\([^/]*\)/.*@\1@p' $(DL_DIR)/chinadns-list-eb9dc5e02c20f9dbcb81e2f868c6cbfc5fc1727f.conf; printf '%s\n' cn ntp.org time.cloudflare.com time.google.com time.windows.com; } | LC_ALL=C sort -u > $(PKG_BUILD_DIR)/chinalist.txt
	echo '375424eb7909a83238359a59f56b15abd0fb18bdd47c13347b8da6e1befeb611  $(PKG_BUILD_DIR)/chinalist.txt' | sha256sum -c -
endef

define Build/Configure
endef
define Build/Compile
endef

define Package/chinadns-ng/install
	$(INSTALL_DIR) $(1)/usr/bin $(1)/etc/init.d $(1)/etc/config $(1)/etc/chinadns-ng
	$(INSTALL_BIN) $(PKG_BUILD_DIR)/chinadns-ng $(1)/usr/bin/chinadns-ng
	$(INSTALL_BIN) ./files/chinadns-ng.init $(1)/etc/init.d/chinadns-ng
	$(INSTALL_CONF) ./files/chinadns-ng.uci $(1)/etc/config/chinadns-ng
	$(INSTALL_DATA) $(PKG_BUILD_DIR)/chinalist.txt $(1)/etc/chinadns-ng/chinalist.txt
	touch $(1)/etc/chinadns-ng/gfwlist.txt
endef

$(eval $(call BuildPackage,chinadns-ng))
