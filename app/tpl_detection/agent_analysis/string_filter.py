import re
import subprocess
import traceback
from typing import List, Dict
from collections import Counter
from loguru import logger


class StringFilter:
    """
    String filtering and categorization for binary analysis
    """

    def __init__(self,
                 max_paths: int = 20,
                 max_functions: int = 20,
                 max_logs: int = 15,
                 max_versions: int = 10,
                 max_signatures: int = 15,
                 max_string_length: int = 200):
        self.max_paths = max_paths
        self.max_functions = max_functions
        self.max_logs = max_logs
        self.max_versions = max_versions
        self.max_signatures = max_signatures
        self.max_string_length = max_string_length

        # 更宽松的 License/Copyright patterns
        self.copyright_patterns = [
            r'(?i)copyright.*',  # 任何包含copyright的
            r'(?i)©.*',  # 任何包含版权符号的
            r'(?i)\(c\).*',  # (c) 版权标记
            r'(?i)license.*',  # 任何包含license的
            r'(?i)licensed.*',  # 任何包含licensed的
            r'(?i)permission.*granted.*',  # 许可授权相关
            r'(?i)redistribution.*',  # 重新分发条款
            r'(?i)all rights reserved.*',  # 版权保留声明
            r'(?i)author.*:.*',  # 作者信息
            r'(?i)maintainer.*:.*',  # 维护者信息
            r'(?i)contributor.*',  # 贡献者信息
            r'(?i).*project.*',  # 项目信息
            r'(?i).*foundation.*',  # 基金会信息
        ]

        # Path/URL patterns
        self.path_patterns = [
            r'/usr/lib/[^/\s]+',
            r'/opt/[^/\s]+',
            r'/usr/share/[^/\s]+',
            r'/usr/include/[^/\s]+',
            r'C:\\Program Files\\[^\\]+',
            r'C:\\Windows\\[^\\]+',
            r'github\.com/[^/\s]+/[^/\s]+',
            r'gitlab\.com/[^/\s]+/[^/\s]+',
            r'https?://[^\s]+',
            r'[a-zA-Z]:/[^/\s]+/[^/\s]+',
            r'/[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+',
            r'\.\.\/[^/\s]+',  # 相对路径
            r'src/[^/\s]+',  # 源码路径
        ]

        # Version patterns
        self.version_patterns = [
            r'(?i)version\s+v?\d+[\.\d]*',  # version 1.2.3
            r'(?i)v\d+\.\d+[\.\d]*',  # v1.2.3
            r'\d+\.\d+\.\d+[\.\d]*',  # 1.2.3.4
            r'(?i)build\s+\d+',  # build 1234
            r'(?i)release\s+[\d\.]+',  # release 2024.1
            r'(?i)rev\s+\d+',  # rev 123
            r'(?i)commit\s+[a-f0-9]+',  # commit hash
        ]

        # Library signature keywords
        self.lib_keywords = [
            'openssl', 'libssl', 'libcrypto', 'boringssl', 'libressl',
            'zlib', 'libz', 'gzip', 'compress',
            'sqlite', 'libsqlite', 'database',
            'curl', 'libcurl', 'http', 'https',
            'xml', 'libxml', 'libxml2', 'expat',
            'json', 'libjson', 'cjson', 'jansson',
            'png', 'libpng', 'jpeg', 'libjpeg',
            'thread', 'pthread', 'mutex',
            'crypto', 'ssl', 'tls', 'cipher',
            'parser', 'regex', 'pcre',
        ]

        # Function name patterns
        self.function_patterns = [
            r'^[a-zA-Z_][a-zA-Z0-9_]*$',  # Simple function names
            r'^_Z\w+',  # C++ mangled names
        ]

        # Log message keywords
        self.log_keywords = ['error', 'warning', 'debug', 'info', 'log', 'failed', 'success', 'initialize']

    def _truncate_string(self, s: str) -> str:
        """Truncate string to max length"""
        return s[:self.max_string_length] if len(s) > self.max_string_length else s

    def extract_license_copyright(self, strings: List[str]) -> List[str]:
        """Extract license and copyright information with broader matching"""
        results = []
        for string in strings:
            for pattern in self.copyright_patterns:
                if re.search(pattern, string):
                    results.append(self._truncate_string(string))
                    break
        return list(set(results))  # Remove duplicates

    def extract_version_info(self, strings: List[str]) -> List[str]:
        """Extract version and build information"""
        results = []
        for string in strings:
            for pattern in self.version_patterns:
                if re.search(pattern, string):
                    results.append(self._truncate_string(string))
                    break

        # Sort by relevance (longer version strings first)
        results = sorted(set(results), key=len, reverse=True)
        return results[:self.max_versions]

    def extract_library_signatures(self, strings: List[str]) -> List[str]:
        """Extract strings containing library-specific keywords"""
        results = []
        for string in strings:
            string_lower = string.lower()
            for keyword in self.lib_keywords:
                if keyword in string_lower and len(string) <= self.max_string_length:
                    results.append(string)
                    break

        # Remove duplicates and sort by relevance
        results = list(set(results))
        # Prioritize shorter, more specific strings
        results = sorted(results, key=lambda x: (len(x), x))
        return results[:self.max_signatures]

    def extract_paths_urls(self, strings: List[str]) -> List[str]:
        """Extract file paths and URLs"""
        results = []
        for string in strings:
            for pattern in self.path_patterns:
                if re.search(pattern, string):
                    results.append(self._truncate_string(string))
                    break

        # Sort by information content and limit
        results = sorted(set(results), key=len, reverse=True)
        return results[:self.max_paths]

    def extract_function_names(self, strings: List[str]) -> Dict[str, List[str]]:
        """Extract function names and analyze prefixes"""
        function_names = []
        mangled_names = []

        for string in strings:
            # Simple function names
            if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', string) and 3 <= len(string) <= 50:
                function_names.append(string)
            # C++ mangled names
            elif re.match(r'^_Z\w+', string):
                mangled_names.append(string)

        # Extract prefixes from simple function names
        prefixes = []
        for func in function_names:
            if '_' in func:
                prefix = func.split('_')[0]
                if len(prefix) >= 2:
                    prefixes.append(prefix)
            elif len(func) > 3:
                # For camelCase, extract first part
                parts = re.findall(r'^[a-z]+', func)
                if parts:
                    prefixes.append(parts[0])

        # Count prefixes and get top ones
        prefix_counts = Counter(prefixes)
        top_prefixes = []

        # Include high-frequency prefixes and library-specific ones
        for prefix, count in prefix_counts.most_common():
            # Always include known library prefixes regardless of frequency
            if prefix.lower() in ['ssl', 'tls', 'bn', 'evp', 'rsa', 'aes', 'sha', 'md5', 'x509', 'pem', 'asn1',
                                  'crypto', 'bio', 'err', 'obj', 'pkcs', 'ec', 'dh', 'dsa', 'hmac',
                                  'zlib', 'inflate', 'deflate', 'gzip', 'sqlite', 'curl', 'xml', 'json']:
                top_prefixes.append(f"{prefix} (count: {count})")
            # Include other high-frequency prefixes
            elif count >= 3 and len(top_prefixes) < self.max_functions // 2:
                top_prefixes.append(f"{prefix} (count: {count})")

        # Limit total count
        top_prefixes = top_prefixes[:self.max_functions // 2]

        # Demangle C++ names (simplified)
        demangled = self._demangle_cpp_names(mangled_names[:self.max_functions // 2])

        return {
            'function_prefixes': top_prefixes,
            'mangled_functions': mangled_names[:self.max_functions // 2],
            'demangled_functions': demangled
        }

    def _demangle_cpp_names(self, mangled_names: List[str]) -> List[str]:
        """Attempt to demangle C++ function names"""
        demangled = []
        for name in mangled_names:
            try:
                # Try using c++filt if available
                result = subprocess.run(['c++filt', name],
                                        capture_output=True, text=True, timeout=1)
                if result.returncode == 0 and result.stdout.strip() != name:
                    demangled.append(self._truncate_string(result.stdout.strip()))
                else:
                    demangled.append(self._truncate_string(name))
            except Exception as e:
                # Fallback: simple pattern extraction
                logger.error(f"Failed to demangle C++ name '{name}': {e}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                demangled.append(self._truncate_string(name))
        return demangled

    def extract_log_messages(self, strings: List[str]) -> List[str]:
        """Extract potential log messages"""
        candidates = []

        for string in strings:
            # Length filter
            if not (20 <= len(string) <= self.max_string_length):
                continue

            # Check for log indicators
            has_log_keyword = any(keyword in string.lower() for keyword in self.log_keywords)
            has_format_specifier = bool(re.search(r'%[sdxo]', string))
            looks_like_sentence = bool(re.search(r'[A-Z][a-z]+.*[a-z]', string))

            if has_log_keyword or has_format_specifier or looks_like_sentence:
                candidates.append(string)

        # Sort by relevance and limit
        candidates = sorted(set(candidates), key=lambda x: (
            sum(keyword in x.lower() for keyword in self.log_keywords),
            len(x)
        ), reverse=True)

        return candidates[:self.max_logs]

    def filter_strings(self, strings: List[str]) -> Dict[str, any]:
        """Main string filtering method"""
        return {
            'license_copyright': self.extract_license_copyright(strings),
            'version_info': self.extract_version_info(strings),
            'library_signatures': self.extract_library_signatures(strings),
            'paths_urls': self.extract_paths_urls(strings),
            'functions': self.extract_function_names(strings),
            'log_messages': self.extract_log_messages(strings)
        }