import hashlib
from typing import List, Dict, Any
import os
import subprocess
import traceback
from pathlib import Path

import lief
from loguru import logger

from ....interface import TargetBinary
from ..agent_analysis.string_filter import StringFilter


def calculate_file_sha256(file_path):
    """
    计算指定文件的SHA256哈希值

    Args:
        file_path (str): 文件路径

    Returns:
        str: 文件的SHA256哈希值（十六进制字符串）

    Raises:
        FileNotFoundError: 如果文件不存在
        PermissionError: 如果没有读取文件的权限
        OSError: 其他文件操作错误
    """
    # 检查文件是否存在
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")

    # 检查是否为文件（而不是目录）
    if not os.path.isfile(file_path):
        raise ValueError(f"路径不是文件: {file_path}")

    # 创建SHA256哈希对象
    sha256_hash = hashlib.sha256()

    try:
        # 以二进制模式打开文件
        with open(file_path, 'rb') as file:
            # 分块读取文件内容，避免大文件占用过多内存
            for chunk in iter(lambda: file.read(4096), b""):
                sha256_hash.update(chunk)
    except PermissionError:
        raise PermissionError(f"没有读取文件的权限: {file_path}")
    except OSError as e:
        raise OSError(f"读取文件时发生错误: {e}")

    # 返回十六进制格式的哈希值
    return sha256_hash.hexdigest()

class FilePreprocessor:

    def __init__(self,
                 # StringFilter相关参数
                 max_copyright: int = 15,  # 版权信息最大显示数量
                 max_paths: int = 20,  # 路径URL最大显示数量
                 max_function_prefixes: int = 15,  # 函数前缀最大显示数量
                 max_logs: int = 10,  # 日志消息最大显示数量
                 max_versions: int = 8,  # 版本信息最大显示数量
                 max_string_length: int = 200,  # 单个字符串最大长度
                 ):
        # StringFilter配置
        self.string_filter = StringFilter(
            max_copyright=max_copyright,
            max_paths=max_paths,
            max_function_prefixes=max_function_prefixes,
            max_logs=max_logs,
            max_versions=max_versions,
            max_string_length=max_string_length
        )
        pass


    def basic_analyze(self, file_path, root_path=None,

                      ) -> TargetBinary:
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

        # Filter and categorize strings
        filtered_strings = self.string_filter.filter_strings(strings_list)

        # 创建TargetBinary对象
        target_binary = TargetBinary(
            binary_name=file_path_obj.name,
            hash_sha256= calculate_file_sha256(file_path),
            relative_path=relative_path,
            absolute_path=str(file_path_absolute),
            file_size_kb=file_size_kb,
            strings=strings_list,
            classified_strings=filtered_strings,
            dynamic_libraries=dynamic_linked_libraries,
            imported_symbols=imported_symbols,
            exported_symbols=exported_symbols,
            imported_symbol_analysis=self._analyze_imported_symbols(imported_symbols),
            exported_symbol_analysis=self._analyze_exported_symbols(exported_symbols),
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

    # TODO tpl_analyzer 里面也实现了一份，改成一样的。
    def _analyze_exported_symbols(self, exported_symbols: list) -> Dict[str, Any]:
        """按函数前缀分类分析导出符号"""
        if not exported_symbols:
            return {}

        prefix_categories = {}

        for symbol in exported_symbols:
            # 提取前缀（到第一个下划线）
            if '_' in symbol:
                prefix = symbol.split('_')[0]
            else:
                # 如果没有下划线，取前几个字符作为前缀
                import re
                match = re.match(r'^[a-zA-Z]+', symbol)
                prefix = match.group()[:4] if match else 'other'

            # 只统计有意义的前缀（长度>=2）
            if len(prefix) >= 2:
                if prefix not in prefix_categories:
                    prefix_categories[prefix] = []
                prefix_categories[prefix].append(symbol)

        # 整理结果：每个前缀类别给几个例子
        result = {
            'total_exported': len(exported_symbols),
            'prefix_categories': {}
        }

        for prefix, symbols in prefix_categories.items():
            if len(symbols) >= 1:  # 至少有1个符号
                result['prefix_categories'][prefix] = {
                    'count': len(symbols),
                    'examples': symbols[:3]  # 每个前缀给3个例子
                }

        return result

    def _analyze_imported_symbols(self, imported_symbols: list) -> Dict[str, Any]:
        """分析导入符号的前缀模式"""
        if not imported_symbols:
            return {}

        prefix_categories = {}

        for symbol in imported_symbols:
            # 提取前缀（到第一个下划线）
            if '_' in symbol:
                prefix = symbol.split('_')[0]
            else:
                # 如果没有下划线，取前几个字符作为前缀
                import re
                match = re.match(r'^[a-zA-Z]+', symbol)
                prefix = match.group()[:4] if match else 'other'

            # 只统计有意义的前缀（长度>=2）
            if len(prefix) >= 2:
                if prefix not in prefix_categories:
                    prefix_categories[prefix] = []
                prefix_categories[prefix].append(symbol)

        # 只保留有多个符号的前缀
        significant_prefixes = {k: v for k, v in prefix_categories.items() if len(v) >= 2}

        result = {
            'total_imported': len(imported_symbols),
            'significant_prefixes': {}
        }

        for prefix, symbols in significant_prefixes.items():
            result['significant_prefixes'][prefix] = {
                'count': len(symbols),
                'examples': symbols[:2]  # 每个前缀给2个例子
            }

        return result