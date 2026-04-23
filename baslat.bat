@echo off
title EnpaiManage
python enpai_manage.py
if %errorlevel% neq 0 (
    echo [!] Uygulama baslatilamadi. 
    echo     Eger kütüphaneler eksikse kurulum.bat dosyasini calistirin.
    pause
)
