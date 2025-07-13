from typing import List
import os
import subprocess
import platform
from pathlib import Path

from app.interface import TargetBinary



class FilePreprocessor:

    def __init__(self):
        pass


    def basic_analyze(self, file_path, root_path=None) -> TargetBinary:
        """
        对二进制文件进行基础分析，提取字符串信息和动态链接信息

        Args:
            file_path: 二进制文件路径
            root_path: 根目录路径，用于计算相对路径。如果为None，则使用file_path作为根目录

        Returns:
            TargetBinary: 包含分析结果的对象
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")

        # 获取文件基本信息
        file_path_obj = Path(file_path)
        file_size_kb = file_path_obj.stat().st_size // 1024  # 转换为KB

        # 计算相对路径
        if root_path is None:
            root_path = file_path

        root_path_obj = Path(root_path)
        file_path_absolute = file_path_obj.absolute()
        root_path_absolute = root_path_obj.absolute()

        # 如果根目录和文件路径一致，使用根目录
        if file_path_absolute == root_path_absolute:
            relative_path = root_path_obj.name
        else:
            # 计算相对于根目录的路径
            try:
                relative_path = str(file_path_absolute.relative_to(root_path_absolute))
            except ValueError:
                # 如果文件不在根目录下，使用文件名
                relative_path = file_path_obj.name

        # 使用strings命令提取字符串
        strings_list = self._extract_strings(file_path)

        # 提取动态链接库信息
        dynamic_libraries = self._extract_dynamic_libraries(file_path)

        # 创建TargetBinary对象
        target_binary = TargetBinary(
            binary_name=file_path_obj.name,
            relative_path=relative_path,
            absolute_path=str(file_path_absolute),
            file_size_kb=file_size_kb,
            strings=strings_list,
            dynamic_libraries=dynamic_libraries
        )

        return target_binary

    def _extract_strings(self, file_path: str) -> List[str]:
        """
        使用strings命令提取二进制文件中的字符串

        Args:
            file_path: 二进制文件路径

        Returns:
            List[str]: 提取的字符串列表
        """
        try:
            # 使用strings命令，设置最小长度为4的字符串
            result = subprocess.run(
                ['strings', '-n', '4', file_path],
                capture_output=True,
                text=True,
                timeout=30  # 设置超时时间
            )

            if result.returncode == 0:
                # 分割输出并过滤空字符串
                strings = [line.strip() for line in result.stdout.split('\n') if line.strip()]
                return strings
            else:
                print(f"strings命令执行失败: {result.stderr}")
                return []

        except subprocess.TimeoutExpired:
            print(f"strings命令执行超时: {file_path}")
            return []
        except FileNotFoundError:
            print("strings命令未找到，请确保系统已安装strings工具")
            return []
        except Exception as e:
            print(f"提取字符串时发生错误: {e}")
            return []

    def _extract_dynamic_libraries(self, file_path: str) -> List[str]:
        """
        提取二进制文件的动态链接库信息

        Args:
            file_path: 二进制文件路径

        Returns:
            List[str]: 动态链接库列表
        """
        try:
            system = platform.system().lower()

            if system == 'linux':
                return self._extract_dynamic_libraries_linux(file_path)
            elif system == 'darwin':  # macOS
                return self._extract_dynamic_libraries_macos(file_path)
            elif system == 'windows':
                return self._extract_dynamic_libraries_windows(file_path)
            else:
                print(f"不支持的操作系统: {system}")
                return []

        except Exception as e:
            print(f"提取动态链接库信息时发生错误: {e}")
            return []

    def _extract_dynamic_libraries_linux(self, file_path: str) -> List[str]:
        """
        Linux系统下提取动态链接库信息
        """
        dynamic_libs = []

        try:
            # 首先尝试使用 ldd
            result = subprocess.run(
                ['ldd', file_path],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    line = line.strip()
                    if '=>' in line:
                        # 格式: libname.so => /path/to/lib (0x...)
                        lib_name = line.split('=>')[0].strip()
                        if lib_name and not lib_name.startswith('linux-vdso'):
                            dynamic_libs.append(lib_name)
                    elif line.endswith(')') and '(0x' in line:
                        # 格式: /lib64/ld-linux-x86-64.so.2 (0x...)
                        lib_path = line.split('(0x')[0].strip()
                        if lib_path:
                            lib_name = os.path.basename(lib_path)
                            dynamic_libs.append(lib_name)
            else:
                # ldd失败，尝试使用 objdump
                return self._extract_dynamic_libraries_objdump(file_path)

        except FileNotFoundError:
            # ldd命令不存在，尝试使用 objdump
            return self._extract_dynamic_libraries_objdump(file_path)
        except subprocess.TimeoutExpired:
            print(f"ldd命令执行超时: {file_path}")

        return list(set(dynamic_libs))  # 去重

    def _extract_dynamic_libraries_objdump(self, file_path: str) -> List[str]:
        """
        使用objdump提取动态链接库信息 (作为ldd的备用方案)
        """
        dynamic_libs = []

        try:
            result = subprocess.run(
                ['objdump', '-p', file_path],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                in_needed_section = False
                for line in result.stdout.split('\n'):
                    line = line.strip()
                    if 'NEEDED' in line:
                        # 格式: NEEDED libname.so.1
                        parts = line.split()
                        if len(parts) >= 2:
                            lib_name = parts[-1]
                            dynamic_libs.append(lib_name)

        except FileNotFoundError:
            print("objdump命令未找到")
        except subprocess.TimeoutExpired:
            print(f"objdump命令执行超时: {file_path}")

        return dynamic_libs

    def _extract_dynamic_libraries_macos(self, file_path: str) -> List[str]:
        """
        macOS系统下提取动态链接库信息
        """
        dynamic_libs = []

        try:
            result = subprocess.run(
                ['otool', '-L', file_path],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                lines = result.stdout.split('\n')[1:]  # 跳过第一行（文件名）
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith(file_path):
                        # 格式: /path/to/lib.dylib (compatibility version x.x.x, current version x.x.x)
                        lib_path = line.split('(')[0].strip()
                        if lib_path:
                            lib_name = os.path.basename(lib_path)
                            dynamic_libs.append(lib_name)

        except FileNotFoundError:
            print("otool命令未找到，请确保已安装Xcode命令行工具")
        except subprocess.TimeoutExpired:
            print(f"otool命令执行超时: {file_path}")

        return dynamic_libs

    def _extract_dynamic_libraries_windows(self, file_path: str) -> List[str]:
        """
        Windows系统下提取动态链接库信息
        """
        dynamic_libs = []

        try:
            # 尝试使用 dumpbin (如果安装了 Visual Studio)
            result = subprocess.run(
                ['dumpbin', '/dependents', file_path],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                in_dependencies = False
                for line in result.stdout.split('\n'):
                    line = line.strip()
                    if 'Image has the following dependencies:' in line:
                        in_dependencies = True
                        continue
                    elif in_dependencies and line.endswith('.dll'):
                        dynamic_libs.append(line)
                    elif in_dependencies and not line:
                        break

        except FileNotFoundError:
            # dumpbin不存在，可以尝试其他工具或跳过
            print("dumpbin命令未找到，跳过Windows DLL依赖分析")

        return dynamic_libs