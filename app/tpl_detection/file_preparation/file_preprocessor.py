from typing import List
import os
import subprocess
import platform
import traceback
from pathlib import Path

import lief
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

        # 提取动态链接库, 导入，到处符号表
        dynamic_linked_libraries, imported_symbols, exported_symbols = self._lief_parse(file_path)

        # 使用strings命令提取字符串
        strings_list = self._extract_strings(file_path)

        # 创建TargetBinary对象
        target_binary = TargetBinary(
            binary_name=file_path_obj.name,
            relative_path=relative_path,
            absolute_path=str(file_path_absolute),
            file_size_kb=file_size_kb,
            strings=strings_list,
            dynamic_libraries=dynamic_linked_libraries,
            imported_symbols=imported_symbols,
            exported_symbols=exported_symbols,
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


    def _lief_parse(self, file_path):
        """
        获取二进制文件的动态链接库

        Args:
            file_path (str): 二进制文件路径

        Returns:
            list: 动态链接库名称列表
        """
        try:
            binary = lief.parse(file_path)
            if binary is None:
                return [],[],[]
            dynamic_linked_libraries = list(binary.libraries)
            imported_symbols = [symbol.name for symbol in binary.imported_symbols if symbol.name]
            exported_symbols = [symbol.name for symbol in binary.exported_symbols if symbol.name]
            return dynamic_linked_libraries, imported_symbols, exported_symbols
        except:
            return [],[],[]
