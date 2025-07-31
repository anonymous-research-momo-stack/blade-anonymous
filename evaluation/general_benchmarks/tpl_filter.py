import json
from dataclasses import asdict, fields, dataclass, field
from enum import Enum
from typing import List, Dict, Type, Any

from environs import Env
import subprocess
from tqdm import tqdm


# =====================
# 数据结构定义
# =====================
@dataclass
class Serializable:
    def customer_serialize(self) -> Dict[str, Any]:
        serialized_data = asdict(self)
        for field in fields(self):
            value = getattr(self, field.name)
            if hasattr(value, 'customer_serialize'):
                serialized_data[field.name] = value.customer_serialize()
            elif isinstance(value, list) and value and hasattr(value[0], 'customer_serialize'):
                serialized_data[field.name] = [item.customer_serialize() for item in value]
        return serialized_data

    @classmethod
    def init_from_dict(cls: Type['Serializable'], data: Dict[str, Any]) -> 'Serializable':
        init_args = {}
        for field in fields(cls):
            try:
                field_value = data.get(field.name)
                if hasattr(field.type, 'init_from_dict') and isinstance(field_value, dict):
                    init_args[field.name] = field.type.init_from_dict(field_value)
                elif (isinstance(field_value, list) and
                      field.type.__args__ and
                      hasattr(field.type.__args__[0], 'init_from_dict') and
                      all(isinstance(i, dict) for i in field_value)):
                    init_args[field.name] = [field.type.__args__[0].init_from_dict(item) for item in field_value]
                else:
                    init_args[field.name] = field_value
            except Exception as e:
                print(cls.__name__, field.name, field.type)
                raise e
        return cls(**init_args)

class ChangeType(Enum):
    ADD = 'ADD'
    UPDATE = 'UPDATE'
    DELETE = 'DELETE'

@dataclass
class GitTag(Serializable):
    commit_id: str  # git commit id
    names: List[str]  # tag names, 可能有多个tag指向同一个commit
    tag_datetime: str = None  # tag的ISO 8601格式时间字符串
    commit_datetime: str = None  # commit的ISO 8601格式时间字符串

@dataclass
class SourceCode(Serializable):
    version_source: str  # tag, branch, commit, or other version source
    commit_id: str
    original_version_strs: List[str]
    semantic_version_str: str
    commit_datetime: str = None  # commit的ISO 8601格式时间字符串
    tag_datetime: str = None  # tag的ISO 8601格式时间字符串
    change_type: ChangeType = None

@dataclass
class LibraryStatus(Serializable):
    is_src_downloaded: bool = False  # 是否成功下载了源代码
    download_failed_reason: str = None # 下载失败的原因
    is_version_analyzed: bool = False  # 是否成功分析了版本信息
    no_version_reason: str = None  # 没有版本信息的原因

@dataclass
class Library(Serializable):
    name: str
    source: List[str]  # 收集来源，vcpkg
    vendor: str
    collected_by: str
    homepage: str = None # 主页，来源上提供的原始主页
    repo_link: str = None # github repo link e.g.: https://github.com/FFmpeg/FFmpeg
    repo_link_human_reviewed: bool = False  #是否人工确认过 repo_link
    alias: str = None# 别名
    source_codes: List[SourceCode] = field(default_factory=list)  # 源代码列表
    change_type: ChangeType = None  # meta 变更类型，ADD, UPDATE, DELETE
    status: LibraryStatus = field(default_factory=lambda: LibraryStatus())
    tags: str = None

    def get_key(self) -> str:
        """获取库的唯一标识符"""
        return f"{self.name}-{self.repo_link}"

class LibrarySource(Enum):
    awesome_cpp = 'awesome_cpp'
    awesome_modern_cpp = 'awesome_modern_cpp'
    awesome_c = 'awesome_c'
    meson = "meson"
    clibs = 'clibs'
    spack = 'spack'
    xmake = 'xmake'
    hunter = 'hunter'
    github = 'github'
    gnu = 'gnu'
    nvd = 'nvd'
    vcpkg = 'vcpkg'
    conan = 'conan'
    manual_label = 'manual_label'
    debian = 'debian'

# =====================
# 常量与环境变量
# =====================
env = Env()
env.read_env(".env")

# Conan Binaries
Conan_benchmark_meta = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/evaluation/general_benchmarks/benchmark_meta/conan_library_benchmark.json"
Conan_test_case_dir = "/Users/liuchengyue/Desktop/BinarySCA Platform/Data/Test_Cases/TPL_Test_Cases/conan_test_cases"

tpl_meta = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/knowledge_jsons/tpl_metas/v1.0.1.json"
with open(tpl_meta) as json_file:
    json_data = json.load(json_file)['libraries']

tpls = [Library.init_from_dict(tpl) for tpl in json_data]

GIT_HOSTS = [
    "github.com", "gitlab.com", "gitee.com", "bitbucket.org"
]
OBVIOUS_INVALID_KEYWORDS = [
    "sourceforge.net", "ftp://", "svn://", ".zip", ".tar.gz", ".7z", ".rar", "http://download", "pypi.org", "npmjs.com", "nuget.org", "crates.io", "cpan.org", "pecl.php.net", "rubygems.org", "apk add", "apt-get", "yum install", "brew install", "docker pull", "manual", "无", "none", "n/a", "not available", "不适用", "不可用", "无链接"
]


# =====================
# 工具函数
# =====================
def is_common_git_host(repo_link):
    if not repo_link:
        return False
    for host in GIT_HOSTS:
        if host in repo_link:
            return True
    return False

def is_obviously_invalid(repo_link):
    if not repo_link:
        return True
    if not (repo_link.startswith("http") or repo_link.startswith("git@")):
        return True
    for kw in OBVIOUS_INVALID_KEYWORDS:
        if kw in repo_link.lower():
            return True
    return False

# =====================
# 主流程
# =====================
"""
改成用命令：git ls-remote 验证
"""
index = 0
for tpl in tqdm(tpls, desc="检查TPL的repo链接有效性"):
    if tpl.source ==['vcpkg', 'conan'] or tpl.source == ['conan''vcpkg']:
        if tpl.homepage.endswith('/'):
            tpl.homepage = tpl.homepage[:-1]
        if tpl.repo_link.endswith('/'):
            tpl.repo_link = tpl.repo_link[:-1]
        if tpl.repo_link != tpl.homepage:
            print(tpl.name)
            print(f"\t homepage: {tpl.homepage}")
            print(f"\t repolink: {tpl.repo_link}")


    # if is_obviously_invalid(repo):
    #     index += 1
    #     print(f"{index}: {tpl.name} - {repo} [明显无效]")
    #     continue
    # if is_common_git_host(repo):
    #     # 直接通过
    #     continue
    # # 其他情况再用 git ls-remote 检查
    # try:
    #     result = subprocess.run(
    #         ['git', 'ls-remote', '--heads', repo],
    #         stdout=subprocess.PIPE,
    #         stderr=subprocess.PIPE,
    #         timeout=10
    #     )
    #     if result.returncode != 0:
    #         index += 1
    #         print(f"{index}: {tpl.name} - {repo} [无效或无法访问]")
    # except Exception as e:
    #     index += 1
    #     print(f"{index}: {tpl.name} - {repo} [检测异常: {e}]")