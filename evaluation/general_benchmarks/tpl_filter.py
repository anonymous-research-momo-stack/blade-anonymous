import json
from dataclasses import asdict, fields
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict
from typing import Type, Any

from environs import Env

from find_not_included_tpls import benchmark

env = Env()
env.read_env(".env")

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


# vcpkg package info
# @dataclass
# class VcpkgPackageInfo(Serializable):
#     """函数参数数据类"""
#     file_path: str
#     package_name: str
#     homepage: str

@dataclass
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
    """
    # 字符串转datetime对象
    from datetime import datetime
    dt = datetime.fromisoformat("2016-11-11T06:26:34+00:00")

    # datetime对象转字符串
    iso_str = dt.isoformat()

    # 转Unix时间戳
    timestamp = dt.timestamp()
    """
    version_source: str  # tag, branch, commit, or other version source
    commit_id: str
    original_version_strs: List[str]
    semantic_version_str: str

    commit_datetime: str = None  # commit的ISO 8601格式时间字符串
    tag_datetime: str = None  # tag的ISO 8601格式时间字符串
    change_type: ChangeType = None


@dataclass
class LibraryStatus(Serializable):
    # src
    is_src_downloaded:bool = False  # 是否成功下载了源代码
    download_failed_reason:str = None # 下载失败的原因

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

    # 相比于上个版本的变化 # TODO 移动到 Status 中去
    change_type: ChangeType = None  # meta 变更类型，ADD, UPDATE, DELETE
    status: LibraryStatus = field(default_factory=lambda: LibraryStatus())

    tags: str = None

    def get_key(self) -> str:
        """获取库的唯一标识符"""
        return f"{self.name}-{self.repo_link}"


# Conan Binaries
Conan_benchmark_meta = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/evaluation/general_benchmarks/benchmark_meta/conan_library_benchmark.json"
Conan_test_case_dir = "/Users/liuchengyue/Desktop/BinarySCA Platform/Data/Test_Cases/TPL_Test_Cases/conan_test_cases"

# 加载TPL meta
tpl_meta = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/knowledge_jsons/tpl_metas/v1.0.2.json"
with open(tpl_meta) as json_file:
    json_data = json.load(json_file)['libraries']

tpls =[Library.init_from_dict(tpl) for tpl in json_data]
tpl_dict = {tpl.name: tpl for tpl in tpls}

# 加载benchmark
benchmark_tpl_names = set([lib.name for tc in benchmark.test_cases for lib in tc.reused_libraries])


filtered_tpls = []
for tpl in tpls:
    if tpl.name in benchmark_tpl_names:
        filtered_tpls.append(tpl_dict.get(tpl.name))
tpl_meta_mini = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/knowledge_jsons/tpl_metas/v1.0.2_mini.json"

with open(tpl_meta_mini, 'w') as f:
    json.dump({'libraries': [tpl.customer_serialize() for tpl in filtered_tpls]}, f, indent=4, ensure_ascii=False)