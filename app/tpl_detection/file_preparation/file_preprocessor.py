from typing import List
import os
import subprocess
import platform
import traceback
from pathlib import Path
from loguru import logger

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
                logger.debug(f"strings命令执行失败: {result.stderr}")
                return []

        except subprocess.TimeoutExpired:
            logger.debug(f"strings命令执行超时: {file_path}")
            return []
        except FileNotFoundError:
            logger.debug("strings命令未找到，请确保系统已安装strings工具")
            return []
        except Exception as e:
            logger.error(f"提取字符串时发生错误: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return []

    def _extract_dynamic_libraries(self, file_path: str) -> List[str]:
        """
        提取二进制文件的动态链接库信息

        Args:
            file_path: 二进制文件路径

        Returns:
            List[str]: 动态链接库列表
        """
        system = platform.system().lower()

        try:
            if system == "linux":
                return self._extract_dynamic_libraries_linux(file_path)
            elif system == "darwin":
                return self._extract_dynamic_libraries_macos(file_path)
            elif system == "windows":
                return self._extract_dynamic_libraries_windows(file_path)
            else:
                logger.debug(f"不支持的操作系统: {system}")
                return []
        except Exception as e:
            logger.error(f"提取动态链接库信息时发生错误: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return []

    def _extract_dynamic_libraries_linux(self, file_path: str) -> List[str]:
        """
        在Linux系统上提取动态链接库信息
        """
        try:
            # 使用ldd命令
            result = subprocess.run(
                ['ldd', file_path],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                libraries = []
                for line in result.stdout.split('\n'):
                    line = line.strip()
                    if line and '=>' in line:
                        # 解析ldd输出格式: libname.so => /path/to/libname.so
                        parts = line.split('=>')
                        if len(parts) == 2:
                            lib_name = parts[0].strip()
                            # 提取库名（去掉版本号）
                            if '.so' in lib_name:
                                lib_name = lib_name.split('.so')[0] + '.so'
                            libraries.append(lib_name)
                return libraries
            else:
                logger.debug(f"ldd命令执行超时: {file_path}")
                return []

        except subprocess.TimeoutExpired:
            logger.debug(f"ldd命令执行超时: {file_path}")
            return []
        except Exception as e:
            logger.error(f"Linux动态链接库提取失败: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return []

    def _extract_dynamic_libraries_macos(self, file_path: str) -> List[str]:
        """
        在macOS系统上提取动态链接库信息
        """
        try:
            # 使用otool命令
            result = subprocess.run(
                ['otool', '-L', file_path],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                libraries = []
                for line in result.stdout.split('\n'):
                    line = line.strip()
                    if line and not line.startswith(file_path) and not line.startswith('/System/'):
                        # 解析otool输出格式: /path/to/libname.dylib
                        if '.dylib' in line:
                            lib_name = line.split('/')[-1]  # 提取文件名
                            libraries.append(lib_name)
                return libraries
            else:
                logger.debug(f"otool命令执行超时: {file_path}")
                return []

        except FileNotFoundError:
            logger.debug("otool命令未找到，请确保已安装Xcode命令行工具")
            return []
        except subprocess.TimeoutExpired:
            logger.debug(f"otool命令执行超时: {file_path}")
            return []
        except Exception as e:
            logger.error(f"macOS动态链接库提取失败: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return []

    def _extract_dynamic_libraries_windows(self, file_path: str) -> List[str]:
        """
        在Windows系统上提取动态链接库信息
        """
        try:
            # 使用dumpbin命令
            result = subprocess.run(
                ['dumpbin', '/dependents', file_path],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                libraries = []
                in_dependencies = False
                for line in result.stdout.split('\n'):
                    line = line.strip()
                    if 'Dump of file' in line:
                        in_dependencies = False
                    elif 'Image has the following dependencies:' in line:
                        in_dependencies = True
                    elif in_dependencies and line and not line.startswith('Summary'):
                        # 解析dumpbin输出格式
                        if '.dll' in line.lower():
                            lib_name = line.strip()
                            libraries.append(lib_name)
                return libraries
            else:
                logger.debug(f"dumpbin命令执行超时: {file_path}")
                return []

        except FileNotFoundError:
            logger.debug("dumpbin命令未找到，跳过Windows DLL依赖分析")
            return []
        except subprocess.TimeoutExpired:
            logger.debug(f"dumpbin命令执行超时: {file_path}")
            return []
        except Exception as e:
            logger.error(f"Windows动态链接库提取失败: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return []