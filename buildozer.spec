[app]
title = Oyunum
package.name = oyunum
package.domain = org.test
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
version = 0.1
requirements = python3,kivy==2.3.0
orientation = portrait
osx.kivy_version = 0.21.0

# Android Sürüm / NDK Sabitlemeleri (Uyumsuzluğu Çözen Kısım)
android.api = 33
android.minapi = 21
android.ndk = 25b
android.accept_sdk_license = True
android.archs = arm64-v8a

[buildozer]
log_level = 2
warn_on_root = 1
