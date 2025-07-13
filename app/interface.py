import dataclasses
import traceback
from dataclasses import asdict, fields
from dataclasses import dataclass
from typing import Dict, Type, Any
from typing import List
from loguru import logger

from app.tpl_detection.agent_analysis.response_models import BinaryInformation, LibraryValidationResult, \
    RedundancyAnalysisResult


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

    # path
    relative_path: str = ""
    absolute_path: str = ""

    # metadata
    file_size_kb: int = 0

    # strings
    strings: List[str] = dataclasses.field(default_factory=list)

    # dynamic libraries
    dynamic_libraries: List[str] = dataclasses.field(default_factory=list)

    # Binary Information
    information: BinaryInformation = None




@dataclass
class Library(Serializable):
    """
    the output library
    """
    # name
    name: str

    # meta
    id: int = None
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
    validation_passed: bool = True
    validation_reasoning: str = ""



@dataclass
class AnalysisData(Serializable):
    feature_matching_results: List[Library] = dataclasses.field(default_factory=list)
    tpl_analysis_results: List[Library] = dataclasses.field(default_factory=list)
    validation_step_1_results: List[LibraryValidationResult] = dataclasses.field(default_factory=list)  # e.g., {"libpng": True, "openssl": False}
    validation_step_2_results: List[RedundancyAnalysisResult] = dataclasses.field(default_factory=list)  # e.g., {"libpng": True, "openssl": False}
    durations: Dict[str, Any] = dataclasses.field(default_factory=dict)  # e.g., {"tpl_detection": 0.1, "binary_analysis": 0.2}
    costs: Dict[str, Any] = dataclasses.field(default_factory=dict)  # e.g., {"tpl_detection": 0.01, "binary_analysis": 0.02}

    def preview(self):
        """预览分析结果"""
        print("\n" + "="*60)
        print("📊 分析结果预览")
        print("="*60)
        
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
                print(f"      证据类型: {lib.evidence_type}")
                print(f"      证据数量: {len(lib.evidences)}")
        else:
            print("   Agent未识别到TPL")
        
        # 3. 预览验证步骤1结果
        print("\n✅ 验证步骤1结果:")
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
        print("\n🔍 验证步骤2结果:")
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
            for step, cost_data in self.costs.items():
                print(f"   {step}: {cost_data}")
        else:
            print("   无成本数据")
        
        print("\n" + "="*60)


    
@dataclass
class AnalysisResult(Serializable):
    target_binary: TargetBinary
    detected_libraries: List[Library] = dataclasses.field(default_factory=list)
    analysis_data: AnalysisData = None

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













