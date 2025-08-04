import dataclasses
import traceback
from dataclasses import asdict, fields
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, Type, Any
from typing import List
from loguru import logger

from .services.tpl_detection.agent_analysis.response_models import BinaryInformation, LibraryValidationResult, \
    RedundancyAnalysisResult, SoftwareContext


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
class TargetBinary(Serializable):
    """
    the input binary
    """
    # name
    binary_name: str
    hash_sha256: str = None  # SHA-256 hash of the binary file

    # path
    relative_path: str = ""
    absolute_path: str = ""

    # metadata
    file_size_kb: int = 0

    # strings
    strings: List[str] = dataclasses.field(default_factory=list)
    # 分类的字符串
    classified_strings:Dict[str, List[str]] = dataclasses.field(default_factory=dict)  # e.g., {"function": ["func1", "func2"], "variable": ["var1"]}

    # dynamic libraries
    dynamic_libraries: List[str] = dataclasses.field(default_factory=list)

    # symbols
    imported_symbols: List[str] = dataclasses.field(default_factory=list)
    exported_symbols: List[str] = dataclasses.field(default_factory=list)

    # symbol analysis
    exported_symbol_analysis:Dict[str, Any] = dataclasses.field(default_factory=dict)  # e.g., {"symbol_name": {"type": "function", "size": 64}}
    imported_symbol_analysis:Dict[str, Any] = dataclasses.field(default_factory=dict)  # e.g., {"symbol_name": {"type": "function", "size": 64}}

    # Binary Information
    information: BinaryInformation = None

    def preview(self):
        print("\n" + "="*60)
        print("📊 目标二进制文件预览")
        print("="*60)
        print(f"\tname: {self.binary_name}")
        print(f"\tpath: {self.absolute_path}")
        print(f"\tinformation: {self.information.description if self.information else 'N/A'}")
        print(f"\tSource TPL: {self.information.source_library.name + ':' + self.information.source_library.description if self.information and self.information.source_library else 'N/A'}")


@dataclass
class Library(Serializable):
    """
    the output library
    """
    # name
    name: str

    # meta
    id: int = None
    version:str = ""
    description: str = ""

    # identify method
    identify_methods: List[str] = dataclasses.field(default_factory=list)

    # feature match information
    matched_strings: List[str] = dataclasses.field(default_factory=list)

    # evidence
    evidence_type: str = ""  # Explicit, Implicit, Mixed
    evidences: List[str] = dataclasses.field(default_factory=list)

    reasoning: str = ""

    # validation results
    is_reasonable:bool=True
    reasonable_reasoning: str = ""

    is_redundant: bool = False
    redundancy_reasoning: str = ""

    validation_passed: bool = True
    src_relative_path:str = ''



@dataclass
class AnalysisConfig(Serializable):
    # LLM相关
    llm_provider: str = "openai"  # e.g., "openai", "anthropic", "ollama"
    model_id: str = "gpt-4.1"  # e.g., "gpt-4.1", "claude-2", "llama-3"

    # 特征匹配参数
    feature_matching_min_string_length: int = 5
    feature_matching_max_string_length: int = 500
    feature_matching_min_match_feature_num: int = 5
    feature_matching_return_top_n: int = 3

    # 是否使用agent
    use_agent:bool = True

    # 二进制信息分析
    enable_bin_info_analysis: bool = True
    enable_bin_info_analysis_web_search: bool = False
    enable_bin_info_analysis_knowledge_base: bool = False

    # TPL分析
    enable_tpl_analysis: bool = True
    enable_tpl_analysis_web_search: bool = False
    enable_tpl_analysis_knowledge_base: bool = False

    # 库验证
    enable_library_validation_web_search: bool = False
    enable_library_validation_knowledge_base: bool = False
    enable_library_validation_db_verification: bool = False

    debug_mode: bool = False


@dataclass
class AnalysisData(Serializable):
    analysis_datetime: str = dataclasses.field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    config: AnalysisConfig = None
    error_message: str = None  # 分析过程中可能出现的错误信息
    context: SoftwareContext=None
    target_binary: TargetBinary = None
    all_candidate_libraries: List[Library] = dataclasses.field(default_factory=list)  # 所有候选库列表
    feature_matching_results: List[Library] = dataclasses.field(default_factory=list)
    tpl_analysis_results: List[Library] = dataclasses.field(default_factory=list)
    validation_step_1_results: List[LibraryValidationResult] = dataclasses.field(default_factory=list)  # e.g., {"libpng": True, "openssl": False}
    validation_step_2_results: List[RedundancyAnalysisResult] = dataclasses.field(default_factory=list)  # e.g., {"libpng": True, "openssl": False}
    durations: Dict[str, Any] = dataclasses.field(default_factory=dict)  # e.g., {"tpl_detection": 0.1, "binary_analysis": 0.2}
    costs: Dict[str, Any] = dataclasses.field(default_factory=dict)  # e.g., {"tpl_detection": 0.01, "binary_analysis": 0.02}

    def preview(self):
        """预览分析结果"""
        print("\n" + "=" * 60)
        print(f"错误日志：{self.error_message}" if self.error_message else "无错误日志")
        print("\n" + "="*60)
        print("📊 分析结果预览 for {}".format(self.target_binary.binary_name))
        print("="*60)
        # 0. 二年制文件预览
        self.target_binary.preview()

        # 1. 预览特征匹配结果
        print("\n🔍 特征匹配结果:")
        print(f"   匹配到的TPL数量: {len(self.feature_matching_results)}")
        if self.feature_matching_results:
            for i, lib in enumerate(self.feature_matching_results, 1):
                print(f"   {i}. {lib.name} - 匹配特征数量: {len(lib.matched_strings)}")
        else:
            print("   未找到匹配的TPL")
        
        # 2. 预览TPL分析结果
        print("\n🤖 TPL分析结果:")
        print(f"   Agent识别的TPL数量: {len(self.tpl_analysis_results)}")
        if self.tpl_analysis_results:
            for i, lib in enumerate(self.tpl_analysis_results, 1):
                print(f"   {i}. {lib.name}")
                print(f"      描述: {lib.description}")
                print(f"      推理过程: {lib.reasoning}")
                print(f"      证据类型: {lib.evidence_type}")
                print(f"      证据数量: {len(lib.evidences)}")
                print(f"      证据例子: {lib.evidences[:5]}")
        else:
            print("   Agent未识别到TPL")
        
        # 3. 预览验证步骤1结果
        print("\n✅ 验证步骤1: 验证识别结果的合理性")
        print(f"   验证的TPL数量: {len(self.validation_step_1_results)}")
        if self.validation_step_1_results:
            passed_count = sum(1 for result in self.validation_step_1_results if result.is_reasonable)
            print(f"   通过验证: {passed_count}/{len(self.validation_step_1_results)}")
            for i, result in enumerate(self.validation_step_1_results, 1):
                status = "✅" if result.is_reasonable else "❌"
                print(f"   {i}. {status} {result.library_name}")
                print(f"      置信度: {result.confidence}")
                print(f"      分析: {result.reasoning}")
        else:
            print("   无验证步骤1数据")
        
        # 4. 预览验证步骤2结果
        print("\n🔍 验证步骤2: 验证所有合理结果的冗余性")
        print(f"   冗余分析的TPL数量: {len(self.validation_step_2_results)}")
        if self.validation_step_2_results:
            kept_count = sum(1 for result in self.validation_step_2_results if result.should_keep)
            print(f"   保留的TPL: {kept_count}/{len(self.validation_step_2_results)}")
            for i, result in enumerate(self.validation_step_2_results, 1):
                status = "✅" if result.should_keep else "❌"
                print(f"   {i}. {status} {result.library_name}")
                print(f"      分析: {result.reasoning}")
        else:
            print("   无验证步骤2数据")
        print("="*60)
        print(f"效率与成本分析")
        print("="*60)
        # 5. 打印时间开销
        print("\n⏱️  时间开销:")
        if self.durations:
            for step, duration in self.durations.items():
                print(f"   {step}: {duration}秒")
        else:
            print("   无时间开销数据")
        
        # 6. 打印token成本
        print("\n💰 Token成本:")

        if self.costs:
            total_input = 0
            total_output = 0

            for step, cost_data in self.costs.items():
                print(f"   {step}:")
                for key, value in cost_data.items():
                    if key in ["input_tokens", "output_tokens", "total_tokens"]:
                        print(f"      {key}: {value} tokens")
                        total_input += value[0] if key == "input_tokens" else 0
                        total_output += value[0] if key == "output_tokens" else 0

            total_tokens = total_input + total_output
            print(f"   总输入Token: {total_input} tokens, 总输出Token: {total_output} tokens, 总Token: {total_tokens} tokens")

            total_cost = total_input * 2/1_000_000 + total_output * 8/1_000_000
            print(f"   总成本: ${total_cost:.6f} (假设单价为输入Token $2/百万, 输出Token $8/百万)")
        else:
            print("   无成本数据")
        
        print("\n" + "="*60)


@dataclass
class SimpleResult(Serializable):
    target_binary_name: str = None
    target_binary_size_kb:float = None
    target_binary_sha256: str = None
    target_binary_path: str = None
    detected_library_names: List[str] = dataclasses.field(default_factory=list)

@dataclass
class AnalysisResult(Serializable):
    binary_name: str
    binary_sha256: str
    binary_path: str
    detected_libraries: List[Library] = dataclasses.field(default_factory=list)
    analysis_data: AnalysisData = None
    succeed: bool = True  # 分析是否成功
    error_message: str = None

    def dump_to_file(self, file_path: str):
        """
        将分析结果序列化并保存到文件
        """
        import json
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self.customer_serialize(), f, ensure_ascii=False, indent=4)

    @classmethod
    def init_from_file(cls, file_path: str):
        """
        从文件中加载分析结果
        """
        import json
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return cls.init_from_dict(data)

    def get_simple_result(self) -> SimpleResult:
        """
        获取简化的分析结果
        """
        return SimpleResult(
            target_binary_name=self.binary_name,
            target_binary_size_kb=self.analysis_data.target_binary.file_size_kb,
            target_binary_sha256=self.binary_sha256,
            target_binary_path=self.binary_path,
            detected_library_names=[lib.name for lib in self.detected_libraries]
        )

@dataclass
class BinaryContext(Serializable):
    """
    Binary file context information (预留接口)
    """
    # 项目基本信息
    project_root_path: str = ""
    project_type: str = ""  # web应用、桌面软件、库等
    project_description: str = ""  # 从README等提取的项目描述

    # 文件位置信息
    file_relative_path: str = ""  # 相对于项目根目录的路径
    directory_context: str = ""  # 所在目录的文件类型和用途

    # 项目结构信息
    key_files: List[str] = dataclasses.field(default_factory=list)  # 关键文件列表
    build_system: str = ""  # CMake, Makefile, npm等

    # 功能推断
    likely_purpose: str = ""  # 这个二进制文件可能的用途
    related_binaries: List[str] = dataclasses.field(default_factory=list)  # 相关的其他二进制文件


class TPLDetectionTaskStatus(Enum):
    """
    任务状态
    """
    PENDING = "pending"  # 任务正在等待执行
    FILE_DOWNLOADING = "file_downloading"  # 文件下载中
    ANALYZING = "analyzing"  # 任务正在分析中
    RESULT_UPLOADING = "result_uploading"  # 结果上传中
    SUCCESS = "success"  # 任务执行成功
    FAILED = "failed"

    def customer_serialize(self) -> str:
        return self.value

    @classmethod
    def init_from_dict(cls, data: str) -> 'TPLDetectionTaskStatus':
        return cls(data)

@dataclass
class TPLDetectionTask(Serializable):
    task_id: str
    file_minio_path: str # minio 路径
    file_local_path: str = None  # 本地临时路径
    workspace_dir: str = None  # 任务专用工作目录路径

    start_at: str = dataclasses.field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    end_at: str = None
    
    # 各个步骤的时间
    file_download_start_at: str = None
    file_download_end_at: str = None
    analysis_start_at: str = None
    analysis_end_at: str = None
    result_upload_start_at: str = None
    result_upload_end_at: str = None

    # result
    result_local_path: str = None
    result_minio_path: str = None

    status: TPLDetectionTaskStatus = TPLDetectionTaskStatus.PENDING
    error_message: str = None



