@echo off
title EnpaiManage

echo [*] Gerekli kutuphaneler denetleniyor...
python -m pip install customtkinter >nul 2>&1

echo [*] Uygulama baslatiliyor...
python enpai_manage.py

if %errorlevel% neq 0 (
    echo [!] Uygulama baslatilamadi. 
    echo     Eger kütüphaneler eksikse kurulum.bat dosyasini calistirin.
    pause
)
