import sys
import json
from datetime import datetime

from environs import Env
from loguru import logger

env = Env()
env.read_env()
logger.remove()
logger.add(sys.stderr, level="INFO")


import dataclasses
import traceback
from dataclasses import asdict, fields
from dataclasses import dataclass
from typing import Dict, Type, Any
from typing import List

from loguru import logger


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
                logger.error(f"Error in {cls.__name__}, field: {field.name}, type: {field.type}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                raise e
        return cls(**init_args)





@dataclass
class Library(Serializable):
    # meta
    name: str
    version: str
    description: str = ""
    license: str = ""
    homepage: str = ""
    url: str = ""
    topics: List[str] = dataclasses.field(default_factory=list)

    def __hash__(self):
        return hash((self.name, self.version))

    def __eq__(self, other):
        if not isinstance(other, Library):
            return NotImplemented
        return self.name == other.name and self.version == other.version

@dataclass
class LibraryReuse(Serializable):

    # library
    library:Library

    # reuse
    is_real_used: bool = True  # Whether the library is actually used in the binary
    link_type: str = "shared"  # e.g., "static", "shared"
    level: str = 1  # e.g., "local", "global"
    reuse_paths: List[str] = dataclasses.field(default_factory=list)  # Paths to the reused libraries

@dataclass
class CompileConfig(Serializable):
    conan_version:str
    profile:str

@dataclass
class Binary(Serializable):
    # under what tpl dir
    tpl_name: str


    # meta
    name: str
    type: str  # e.g., "bin", "lib"
    rel_path:str # 相对路径
    file_size_kb: float
    sha256: str

    def __hash__(self):
        return hash((self.tpl_name, self.name, self.sha256))
    def __eq__(self, other):
        if not isinstance(other, Binary):
            return NotImplemented
        return (self.tpl_name == other.tpl_name and
                self.name == other.name and
                self.sha256 == other.sha256)

@dataclass
class TestBinarySuiteStat(Serializable):
    total_reused_library:int
    total_binaries:int
    bin_binaries: int  # Number of binary files
    lib_binaries: int

@dataclass
class TestBinarySuite(Serializable):
    # stat
    stat: TestBinarySuiteStat = None

    # compile config
    compile_config: CompileConfig = None  # Compile configuration, e.g., "Release", "Debug"

    # reused_libraries
    library_reuses: List[LibraryReuse] = dataclasses.field(default_factory=list)

    # binaries
    binaries: Dict[str, List[Binary]] = dataclasses.field(default_factory=list)


@dataclass
class TestSoftware(Serializable):
    # library meta
    source_library: Library  # The source library for this test case

    test_binary_suites: List[TestBinarySuite] = dataclasses.field(default_factory=list)  # List of test binary suites


@dataclass
class Benchmark(Serializable):
    name: str
    version: str
    test_software: List[TestSoftware] = dataclasses.field(default_factory=list)

    def stat(self):
        """
        统计benchmark的基本信息，并打印。
        """
        num_software = len(self.test_software)

        # 所有真实复用的第三方库（不去重，不含自身）
        reused_lib_list = [
            (reuse.library.name, reuse.library.version)
            for ts in self.test_software
            for suite in ts.test_binary_suites
            for reuse in suite.library_reuses
            if reuse.is_real_used
        ]
        num_reused_libs = len(reused_lib_list)

        # 去重后的第三方库数量
        reused_lib_set = set(reused_lib_list)
        num_unique_reused_libs = len(reused_lib_set)

        # 统计所有二进制文件数量
        num_binaries = sum(
            len(binaries)
            for ts in self.test_software
            for suite in ts.test_binary_suites
            for binaries in suite.binaries.values()
        )

        # hash去重后的二进制文件数量
        unique_binaries = set(
            (binary.sha256)
            for ts in self.test_software
            for suite in ts.test_binary_suites
            for binaries in suite.binaries.values()
            for binary in binaries
        )
        num_unique_binaries = len(unique_binaries)

        print(f"软件数量: {num_software}")
        print(f"编译的第三方库数量: {num_reused_libs}")
        print(f"去重后的第三方库数量: {num_unique_reused_libs}")
        print(f"二进制文件数量: {num_binaries}")
        print(f"hash去重后的二进制文件数量: {num_unique_binaries}")


# ===== 新增数据结构用于评估 =====

@dataclass
class DetectedLibrary(Serializable):
    """检测到的库（聚合版本）"""
    name: str
    version: str = None
    confidence: float = 0.0
    identify_methods: List[str] = dataclasses.field(default_factory=list)
    source_binaries: List[str] = dataclasses.field(default_factory=list)  # 来源二进制文件名
    is_reasonable: bool = True
    is_redundant: bool = False
    description: str = ""


@dataclass
class ProgramAnalysisResult(Serializable):
    """程序级别的检测结果"""
    program_id: str  # 程序标识: f"{source_lib_name}_{version}_{compile_config}"
    source_library: Library  # 源程序库信息
    compile_config: CompileConfig  # 编译配置
    
    # 检测的二进制文件列表
    analyzed_binaries: List[Binary] = dataclasses.field(default_factory=list)
    
    # 聚合后的检测结果
    detected_libraries: List[DetectedLibrary] = dataclasses.field(default_factory=list)
    
    # 分析数据汇总
    total_analysis_duration: float = 0.0
    total_file_size_kb: float = 0.0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost: float = 0.0
    
    # 原始二进制检测结果（用于消融实验）
    binary_analysis_results: List = dataclasses.field(default_factory=list)  # List[AnalysisResult]


@dataclass 
class ProgramAnalysisResultCheck(Serializable):
    """程序级别的结果验证"""
    program_id: str
    source_library_name: str
    compile_config: str
    
    # Ground Truth (只包含is_real_used=True的库)
    ground_truth_lib_names: List[str] = dataclasses.field(default_factory=list)
    
    # 检测结果
    detected_lib_names: List[str] = dataclasses.field(default_factory=list)
    
    # 评估结果
    has_fn: bool = False  # 是否有漏报
    has_fp: bool = False  # 是否有误报
    tp_lib_names: List[str] = dataclasses.field(default_factory=list)
    fp_lib_names: List[str] = dataclasses.field(default_factory=list) 
    fn_lib_names: List[str] = dataclasses.field(default_factory=list)
    
    # 统计信息
    total_binaries_analyzed: int = 0
    total_file_size_kb: float = 0.0


@dataclass
class ConanBenchmarkMeta(Serializable):
    """Conan Benchmark 元数据"""
    name: str
    version: str
    test_software_num: int
    test_program_suites_num: int
    covered_library_num: int
    total_binaries: int


@dataclass
class ConanEvaluationConfig(Serializable):
    """Conan评估配置"""
    benchmark_file: str
    benchmark_data_dir: str  # conan_libs_builder_output目录
    
    # LLM配置
    llm_provider: str = 'openai'
    llm_model_id: str = 'gpt-4o'
    input_token_price_per_1M: float = 2.0
    output_token_price_per_1M: float = 8.0
    
    # 处理配置
    concurrency: int = 3
    
    # 测试用例筛选
    min_reused_lib_num: int = 3  # 最少包含的真实使用库数量
    target_software_names: List[str] = dataclasses.field(default_factory=list)  # 指定测试的软件名称，空表示全部
    target_compile_configs: List[str] = dataclasses.field(default_factory=list)  # 指定编译配置，空表示全部
    
    # 测试用例切片
    slice_start: int = 0
    slice_end: int = -1


@dataclass
class ConanEvaluationReport(Serializable):
    """Conan评估报告"""
    start_at: str = None
    finished_at: str = None
    evaluation_config: ConanEvaluationConfig = None
    benchmark_meta: ConanBenchmarkMeta = None
    
    # 评估结果
    program_analysis_results: List[ProgramAnalysisResult] = dataclasses.field(default_factory=list)
    program_results_check: List[ProgramAnalysisResultCheck] = dataclasses.field(default_factory=list)
    
    # 研究问题数据（需要导入原有的ResearchQuestionData）
    research_question_data: Dict = None  # ResearchQuestionData类型，这里用Dict避免循环导入
    
    # 软件上下文（如果分析的话）
    software_context: Dict = None  # SoftwareContext类型，这里用Dict避免循环导入
    
    # 原始benchmark数据
    benchmark: Benchmark = None

    def dump(self, file_path):
        """保存报告到文件"""
        data = self.customer_serialize()
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

        # 生成简化版本报告
        simple_report = self.get_simple_report()
        simple_report_save_path = file_path.replace('.json', '_simple.json')
        with open(simple_report_save_path, 'w', encoding='utf-8') as f:
            json.dump(simple_report.customer_serialize(), f, indent=4, ensure_ascii=False)

    @classmethod
    def load_from_file(cls, file_path: str) -> 'ConanEvaluationReport':
        """从文件加载报告"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.init_from_dict(data)

    def get_simple_report(self):
        """生成简化版报告"""
        simple_report = SimpleConanEvaluationReport(
            start_at=self.start_at,
            finished_at=self.finished_at,
            evaluation_config=self.evaluation_config,
            benchmark_meta=self.benchmark_meta,
            research_question_data=self.research_question_data,
            program_results_check=self.program_results_check,
        )
        return simple_report


@dataclass
class SimpleConanEvaluationReport(Serializable):
    """简化版Conan评估报告"""
    start_at: str = None
    finished_at: str = None
    evaluation_config: ConanEvaluationConfig = None
    benchmark_meta: ConanBenchmarkMeta = None
    research_question_data: Dict = None  # ResearchQuestionData类型
    program_results_check: List[ProgramAnalysisResultCheck] = dataclasses.field(default_factory=list)