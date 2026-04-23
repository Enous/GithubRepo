@echo off
title EnpaiManage Kurulum
echo ============================================
echo      EnpaiManage Kurulum Sihirbazi
echo ============================================
echo.
echo [*] Gerekli kutuphaneler kontrol ediliyor...

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [X] Python bulunamadi! Lutfen Python yukleyin ve PATH'e ekleyin.
    pause
    exit
)

echo [*] CustomTkinter yukleniyor...
python -m pip install customtkinter

echo [*] Git kontrol ediliyor...
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Git bulunamadi. Repolari klonlamak icin Git gereklidir.
    echo     Lutfen https://git-scm.com adresinden Git yukleyin.
)

echo.
echo [✔] Kurulum tamamlandi!
echo Artik baslat.bat dosyasini kullanabilirsiniz.
echo.
pause
