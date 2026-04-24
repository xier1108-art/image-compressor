@echo off
echo ================================================
echo  사진 압축기 - 단일 .exe 빌드
echo ================================================
echo.

pip install pyinstaller pillow pillow-heif pyoxipng PyQt6 --quiet

pyinstaller --onefile --windowed ^
    --name "사진압축기" ^
    --collect-all PyQt6 ^
    --collect-all pillow_heif ^
    --collect-all oxipng ^
    --hidden-import PIL.JpegImagePlugin ^
    --hidden-import PIL.PngImagePlugin ^
    --hidden-import PIL.WebPImagePlugin ^
    --hidden-import PIL.TiffImagePlugin ^
    --hidden-import PIL.BmpImagePlugin ^
    app.py

if %errorlevel% neq 0 (
    echo.
    echo [오류] 빌드 실패
    pause
    exit /b 1
)

echo.
echo ================================================
echo  빌드 완료!
echo  실행 파일: dist\사진압축기.exe
echo ================================================
pause
