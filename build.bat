@echo off
echo ================================================
echo  사진 압축기 - onedir 빌드 (즉시 실행)
echo ================================================
echo.

pip install pyinstaller pillow pillow-heif pyoxipng PyQt6 --quiet

rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul

pyinstaller --noconfirm 사진압축기.spec

if %errorlevel% neq 0 (
    echo.
    echo [오류] 빌드 실패
    pause
    exit /b 1
)

echo.
echo ================================================
echo  빌드 완료!
echo  실행: dist\사진압축기\사진압축기.exe
echo ================================================
pause
