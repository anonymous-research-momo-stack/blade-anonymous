import os
from typing import List
from loguru import logger

from app.interface import TargetBinary, Library
from ..databases.postgres.crud import project_curd
from ..databases.postgres.entities import ProjectFeatureEntity


class FeatureMatchingDetector:
    """
    特征匹配检测器
    用于检测二进制文件与已知库的匹配度
    """

    def __init__(self,
                 top_n: int = 5,
                 feature_min_length = 5,
                 feature_max_length = 500,
                 min_match_feature_num: int = 5):
        """
        初始化特征匹配检测器

        Args:
            top_n: 返回前N个候选库
            min_match_feature_num: 最少匹配字符串数量
            min_effective_string_length: 有效字符串的最小长度
        """
        self.top_n = top_n
        self.min_match_num = min_match_feature_num
        self.feature_min_length = feature_min_length
        self.feature_max_length = feature_max_length
        self.min_effective_string_length = 10

        self.method_name = "Feature Matching"

    def detect(self, target_binary: TargetBinary) -> List[Library]:
        """
        运行特征匹配检测

        Args:
            target_binary: 目标二进制文件对象

        Returns:
            List[Library]: 匹配的候选库列表（Library接口类型）
        """
        if not target_binary.strings:
            logger.warning(f"No strings provided for binary: {target_binary.binary_name}")
            return []

        logger.info(f"Starting feature matching detection for binary: {target_binary.binary_name} with {len(target_binary.strings)} strings")

        # 筛选特征
        strings = self.filter_strings_to_match(target_binary)
        # 调用匹配逻辑
        return self.match_candidate_libraries(target_binary.binary_name, strings)

    def filter_strings_to_match(self,target_binary:TargetBinary)->List[str]:
        strings_to_match = set()
        for s in target_binary.strings:
            if not (self.feature_min_length < len(s) < self.feature_max_length):
                continue

            # 排除掉符合函数名规则的字符串，不匹配函数名
            if self._is_cpp_function_name(s):
                continue

            strings_to_match.add(s.strip())

        return list(strings_to_match)

    def _is_cpp_function_name(self, string: str) -> bool:
        """
        判断字符串是否符合C/C++函数名规则
        
        Args:
            string: 待检查的字符串
            
        Returns:
            bool: 是否为C/C++函数名
        """
        import re
        
        # 去除首尾空白
        s = string.strip()
        
        # 空字符串或太短的字符串不是函数名
        if len(s) < 2:
            return False
            
        # C/C++函数名规则：
        # 1. 只能包含字母、数字、下划线
        # 2. 不能以数字开头
        # 3. 不能是C++关键字
        # 4. 通常包含字母（纯数字不是函数名）
        
        # 检查是否只包含合法字符
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', s):
            return False
            
        # 检查是否包含字母（纯数字不是函数名）
        if not re.search(r'[a-zA-Z]', s):
            return False
            
        # 检查是否为C++关键字
        cpp_keywords = {
            'auto', 'break', 'case', 'char', 'const', 'continue', 'default', 'do',
            'double', 'else', 'enum', 'extern', 'float', 'for', 'goto', 'if',
            'int', 'long', 'register', 'return', 'short', 'signed', 'sizeof', 'static',
            'struct', 'switch', 'typedef', 'union', 'unsigned', 'void', 'volatile', 'while',
            'asm', 'bool', 'catch', 'class', 'const_cast', 'delete', 'dynamic_cast',
            'explicit', 'export', 'false', 'friend', 'inline', 'mutable', 'namespace',
            'new', 'operator', 'private', 'protected', 'public', 'reinterpret_cast',
            'static_cast', 'template', 'this', 'throw', 'true', 'try', 'typeid',
            'typename', 'using', 'virtual', 'wchar_t'
        }
        
        if s.lower() in cpp_keywords:
            return False
            
        # 检查是否为常见的函数名模式
        # 1. 包含常见的前缀/后缀
        common_prefixes = ['get', 'set', 'is', 'has', 'can', 'should', 'will', 'do', 'make', 'create', 'init', 'destroy', 'free', 'alloc', 'dealloc']
        common_suffixes = ['_t', '_ptr', '_ref', '_impl', '_base', '_derived']
        
        s_lower = s.lower()
        for prefix in common_prefixes:
            if s_lower.startswith(prefix) and len(s) > len(prefix):
                return True
                
        for suffix in common_suffixes:
            if s_lower.endswith(suffix):
                return True
                
        # 2. 检查是否为驼峰命名法或下划线命名法
        # 驼峰命名法：getValue, setValue, isEnabled
        if re.match(r'^[a-z][a-zA-Z0-9]*$', s) or re.match(r'^[A-Z][a-zA-Z0-9]*$', s):
            return True
            
        # 下划线命名法：get_value, set_value, is_enabled
        if re.match(r'^[a-z][a-z0-9_]*$', s) and '_' in s:
            return True
            
        # 3. 检查是否包含常见的函数名模式
        function_patterns = [
            r'^[a-zA-Z_][a-zA-Z0-9_]*$',  # 基本函数名模式
            r'.*[A-Z].*',  # 包含大写字母（可能是驼峰命名）
            r'.*_.*',  # 包含下划线
        ]
        
        for pattern in function_patterns:
            if re.match(pattern, s):
                return True
                
        return False


    def match_candidate_libraries(self, file_name: str, strings: List[str]) -> List[Library]:
        """
        匹配候选库
        至少匹配 min_match_num 个字符串
        字符串必须：长度大于min_effective_string_length 或 包含空格，或者是名称相似的库

        Args:
            file_name: 文件名
            strings: 字符串列表

        Returns:
            List[Library]: 匹配的候选库列表（Library接口类型）
        """
        # 1. 数据库匹配 - 先按照字符串查询数据库, 至少匹配min_match_num个字符串
        candidate_project_entities = project_curd.list_projects_by_strings(strings, min_match_num=self.min_match_num)

        if not candidate_project_entities:
            logger.info(f"No candidate libraries found for file: {file_name}")
            return []

        def cal_effective_string_num(project_entity: ProjectFeatureEntity) -> int:
            """
            计算有效字符串数量
            有效字符串：长度大于min_effective_string_length 或 包含空格
            """
            effective_num = 0
            for s in project_entity.matched_strings:
                if " " not in s and len(s) < self.min_effective_string_length:
                    continue
                effective_num += 1
            return effective_num

        # 2. 筛选和排序
        # 先按照字符串数量排序
        candidate_project_entities = sorted(candidate_project_entities,
                                         key=lambda x: len(x.matched_strings),
                                         reverse=True)

        # 再按照有效字符串数量排序
        candidate_project_entities = sorted(candidate_project_entities,
                                         key=cal_effective_string_num,
                                         reverse=True)

        # 匹配数量最多的前 top_n 个
        filter_candidate_project_entities = candidate_project_entities[:self.top_n]

        # 名称相似的也作为候选库
        file_name_for_check = self._prepare_filename_for_check(file_name)

        for project_entity in candidate_project_entities:
            if project_entity not in filter_candidate_project_entities:
                if self._is_similar_name(file_name_for_check, project_entity.name):
                    if project_entity not in filter_candidate_project_entities:
                        filter_candidate_project_entities.append(project_entity)
                        logger.info(f"Added similar name library: {project_entity.name} for file: {file_name}")

        # 3. 转换为Library接口类型
        candidate_libraries = self._convert_to_library_interface(filter_candidate_project_entities)

        logger.info(f"Found {len(candidate_libraries)} candidate libraries for file: {file_name}")

        return candidate_libraries

    def _prepare_filename_for_check(self, file_name: str) -> str:
        """
        准备用于检查的文件名

        Args:
            file_name: 原始文件名

        Returns:
            处理后的文件名
        """
        file_name_for_check = file_name.lower().split(".")[0]
        if "lib" in file_name_for_check and len(file_name_for_check) >= 7:
            file_name_for_check = file_name_for_check[3:]
        return file_name_for_check

    def _is_similar_name(self, file_name: str, library_name: str) -> bool:
        """
        检查文件名与库名称是否相似

        Args:
            file_name: 处理后的文件名
            library_name: 库名称

        Returns:
            是否相似
        """
        return (file_name in library_name.lower() or
                library_name.lower() in file_name)

    def _convert_to_library_interface(self, project_entities: List[ProjectFeatureEntity]) -> List[Library]:
        """
        将数据库实体转换为Library接口类型

        Args:
            project_entities: 数据库项目实体列表

        Returns:
            Library接口类型列表
        """
        libraries = []
        for project_entity in project_entities:
            # 获取库的描述信息
            description = ""
            if hasattr(project_entity, 'library') and project_entity.library:
                description = project_entity.library.description or ""

            # 创建Library对象
            library = Library(
                name=project_entity.name,
                id=project_entity.id,
                description=description,
                matched_strings=project_entity.matched_strings,
                identify_methods=[self.method_name],
                reasoning=f"Based on feature matching method, it matched {len(project_entity.matched_strings)} strings. ",
            )

            libraries.append(library)

        return libraries
