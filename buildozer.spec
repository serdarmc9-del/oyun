[app]
title = Oyunum
package.name = oyunum
package.domain = org.test
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
version = 0.1
requirements = python3,kivy==2.2.1
orientation = portrait
osx.kivy_version = 0.21.0

# Android SDK / NDK Sabit Sürümleri (Çakışmayı Engelleyen Ayarlar)
android.api = 31
android.minapi = 21
android.ndk = 25b
android.accept_sdk_license = True
android.archs = arm64-v8a

[buildozer]
log_level = 2
warn_on_root = 1
