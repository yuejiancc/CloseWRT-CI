# 高质量<免费>交流群

[IPQ技术讨论群](https://qm.qq.com/q/v7nMhzB4oU)

# 高质量<付费>中转站

[LiBwrt-Ai](https://api.zipimg.cn/register?aff=FFPS3UMJ8HJD)

# 本地编译器

https://github.com/VIKINGYFY/OWRT-Tools.git

# 自用修改版插件

https://github.com/VIKINGYFY/packages.git

# CloseWRT-CI

源码：

https://github.com/chasey-dev/immortalwrt-mt798x-rebase.git

https://github.com/Yuzhii0718/immortalwrt-mt798x-6.6-padavanonly.git

# U-BOOT

全新版：

https://github.com/VIKINGYFY/UBOOT-CI/releases

# 注意

本项目仅支持编译带有defconfig目录的MTK SDK闭源项目。

# 固件简要说明

固件每周一早上5点自动编译。

固件信息里的时间为编译开始的时间，方便核对上游源码提交时间。

# 目录简要说明

workflows——自定义CI配置

Scripts——自定义脚本

Config——自定义配置

## Star History

<a href="https://www.star-history.com/?repos=vikingyfy%2Fclosewrt-ci&type=date&legend=top-left">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/chart?repos=vikingyfy/closewrt-ci&type=date&theme=dark&legend=top-left" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/chart?repos=vikingyfy/closewrt-ci&type=date&legend=top-left" />
   <img alt="Star History Chart" src="https://api.star-history.com/chart?repos=vikingyfy/closewrt-ci&type=date&legend=top-left" />
 </picture>
</a>
# KONKA KOMI A31 专用构建

工作流 **KONKA A31** 沿用本项目原有的 Yuzhii 24.10 / Linux 6.6 与
chasey 25.12 两套源码，仅构建 MT7981B / 256 MiB RAM / 128 MiB NAND 的 A31。
配置与版本依据位于 [`Config/KONKA-A31`](Config/KONKA-A31)，每次构建保存配置审计、
源码及 feeds 版本、软件包清单、镜像校验和；可手动选择 `config_only` 只检查配置。
现机为 21.02 的 NMBM、独立 kernel/rootfs 卷布局，而新源码为原生 FIT/DSA 布局，
**产物不能直接视为现系统可保留配置升级的固件**。
安装前请阅读 [兼容与迁移说明](Config/KONKA-A31/COMPATIBILITY.md)。
此工作流不刷写路由器、不清理旧发布，也不将私有运维配置写入公开固件。

