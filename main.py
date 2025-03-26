# main.py
import sys
from PyQt6.QtWidgets import QApplication
from windows.main_window import MainWindow
import traceback
import os
from PyQt6 import QtCore  # 添加这行


def check_windows_compatibility():
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                           r"SOFTWARE\Microsoft\Windows NT\CurrentVersion") as key:
            version = winreg.QueryValueEx(key, "CurrentBuildNumber")[0]
            print(f"Windows Build: {version}")
            
        # 检查DPI设置
        import ctypes
        awareness = ctypes.c_int()
        ctypes.windll.shcore.GetProcessDpiAwareness(0, ctypes.byref(awareness))
        print(f"DPI Awareness: {awareness.value}")
        
        return True
    except Exception as e:
        print(f"兼容性检查失败: {e}")
        return False
    


if __name__ == '__main__':
    try:
        print("\n=== 程序启动 ===")
        app = QApplication(sys.argv)
        
        # 检查Qt环境
        print(f"Qt Version: {QtCore.QT_VERSION_STR}")
        print(f"PyQt Version: {QtCore.PYQT_VERSION_STR}")
        
        # 检查系统信息
        import platform
        print(f"OS: {platform.system()} {platform.release()}")
        print(f"Python: {sys.version}")
        
        # 检查显示器信息
        screen = app.primaryScreen()
        print(f"Screen: {screen.name()}")
        print(f"Resolution: {screen.size().width()}x{screen.size().height()}")
        
        print("\n--- 创建主窗口 ---")
        main_window = MainWindow()  # 这里会执行完整的MainWindow初始化
        
        print("\n--- 准备显示主窗口 ---")
        try:
            # 显示前检查窗口状态
            print("窗口显示前状态:")
            print(f"- 当前可见性: {main_window.isVisible()}")
            print(f"- 窗口几何信息: {main_window.geometry()}")
            print(f"- 窗口状态: {main_window.windowState()}")
            print(f"- 是否已最小化: {main_window.isMinimized()}")
            print(f"- 是否已最大化: {main_window.isMaximized()}")
            
            # 确保窗口尺寸正确
            if main_window.size().isEmpty():
                print("设置默认窗口尺寸...")
                main_window.resize(600, 200)
            
            # 尝试显示窗口
            print("调用show()...")
            main_window.show()
                
            # 显示后再次检查状态
            print("窗口显示后状态:")
            print(f"- 当前可见性: {main_window.isVisible()}")
            print(f"- 窗口几何信息: {main_window.geometry()}")
            print(f"- 窗口状态: {main_window.windowState()}")
            print(f"- 是否已最小化: {main_window.isMinimized()}")
            print(f"- 是否已最大化: {main_window.isMaximized()}")
            
            # 确保窗口真正显示
            main_window.raise_()
            main_window.activateWindow()
            
            print("窗口显示完成")
            QApplication.processEvents()  # 处理所有待处理的事件
            
        except Exception as e:
            print("\n!!! 显示窗口失败 !!!")
            print(f"错误类型: {type(e).__name__}")
            print(f"错误信息: {str(e)}")
            import traceback
            traceback.print_exc()
            raise  # 重新抛出异常
        
        print("\n--- 准备进入事件循环 ---")
        try:
            print("调用app.exec()...")
            return_code = app.exec()
            print(f"事件循环正常结束，返回码: {return_code}")
        except Exception as e:
            print(f"事件循环异常: {e}")
            return_code = 1
        
        print(f"\n--- 事件循环结束，返回码: {return_code} ---")
        sys.exit(return_code)
        
    except Exception as e:
        print("\n!!! 程序启动失败 !!!")
        print(f"错误类型: {type(e).__name__}")
        print(f"错误信息: {str(e)}")
        print("\n详细堆栈信息:")
        import traceback
        traceback.print_exc()
        sys.exit(1)