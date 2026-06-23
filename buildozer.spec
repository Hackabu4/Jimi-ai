[app]

# Қолданба атауы
title = Jimi AI
package.name = jimi
package.domain = org.jimi
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,txt

# Нұсқасы
version = 1.0

# Негізгі талаптар (requirements)
# python3,kivy - міндетті, requests - API үшін, openssl - қауіпсіз байланыс үшін
requirements = python3,kivy,requests,certifi,idna,urllib3

# Бағыты және Fullscreen
orientation = portrait
fullscreen = 0

# Рұқсаттар
android.permissions = INTERNET

# API деңгейлері (Ең тұрақты нұсқалар)
android.api = 33
android.minapi = 21

# Архитектура
android.archs = arm64-v8a, armeabi-v7a

# Android SDK лицензиясын автоматты қабылдау (GitHub Actions үшін маңызды!)
android.accept_sdk_license = True

# Қосымша баптаулар
android.allow_backup = True
android.enable_androidx = True

[buildozer]
# Лог деңгейі: 2 - егжей-тегжейлі (қатені табу үшін)
log_level = 2
warn_on_root = 1

# Қолданылатын NDK және SDK нұсқалары (buildozer өзі жүктейді)
# Егер қате берсе, осы бөлікті өзгертпей қалдыр
