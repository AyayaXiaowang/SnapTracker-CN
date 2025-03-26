@echo off
chcp 65001 >nul
echo ===== 开始构建漫威终极逆转记牌器 =====

echo [1/4] 清理旧的构建文件...
if exist "build" rd /s /q "build"
if exist "dist" rd /s /q "dist"

echo [2/4] 检查并安装依赖...
python -m pip install -r requirements.txt

echo [3/4] 检查 PyInstaller...
python -c "import pyinstaller" 2>nul
if errorlevel 1 (
    echo PyInstaller 未安装，正在安装...
    python -m pip install pyinstaller
)

echo [4/4] 开始打包程序...
python -m PyInstaller --clean --noconfirm snap_tracker.spec

if errorlevel 1 (
    echo 打包失败！请检查错误信息。
    pause
    exit /b 1
)

echo ===== 打包完成！=====
echo 程序已生成在 dist 文件夹中
pause