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
    # classified strings
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
        print("📊 Target binary preview")
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
    # LLM related
    llm_provider: str = "openai"  # e.g., "openai", "anthropic", "ollama"
    model_id: str = "gpt-4.1"  # e.g., "gpt-4.1", "claude-2", "llama-3"

    # Feature matching parameters
    feature_matching_min_string_length: int = 5
    feature_matching_max_string_length: int = 500
    feature_matching_min_match_feature_num: int = 5
    feature_matching_return_top_n: int = 3

    # Whether to use agent
    use_agent:bool = True

    # Binary information analysis
    enable_bin_info_analysis: bool = True
    enable_bin_info_analysis_web_search: bool = False
    enable_bin_info_analysis_knowledge_base: bool = False

    # TPL analysis
    enable_tpl_analysis: bool = True
    enable_tpl_analysis_web_search: bool = False
    enable_tpl_analysis_knowledge_base: bool = False

    # Library validation
    enable_library_validation_web_search: bool = False
    enable_library_validation_knowledge_base: bool = False
    enable_library_validation_db_verification: bool = False

    debug_mode: bool = False


@dataclass
class AnalysisData(Serializable):
    analysis_datetime: str = dataclasses.field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    config: AnalysisConfig = None
    error_message: str = None  # Possible error message during analysis
    context: SoftwareContext=None
    target_binary: TargetBinary = None
    all_candidate_libraries: List[Library] = dataclasses.field(default_factory=list)  # All candidate libraries
    feature_matching_results: List[Library] = dataclasses.field(default_factory=list)
    tpl_analysis_results: List[Library] = dataclasses.field(default_factory=list)
    validation_step_1_results: List[LibraryValidationResult] = dataclasses.field(default_factory=list)  # e.g., {"libpng": True, "openssl": False}
    validation_step_2_results: List[RedundancyAnalysisResult] = dataclasses.field(default_factory=list)  # e.g., {"libpng": True, "openssl": False}
    durations: Dict[str, Any] = dataclasses.field(default_factory=dict)  # e.g., {"tpl_detection": 0.1, "binary_analysis": 0.2}
    costs: Dict[str, Any] = dataclasses.field(default_factory=dict)  # e.g., {"tpl_detection": 0.01, "binary_analysis": 0.02}

    def preview(self):
        """Preview analysis results"""
        print("\n" + "=" * 60)
        print(f"Error log: {self.error_message}" if self.error_message else "No error logs")
        print("\n" + "="*60)
        print("📊 Analysis result preview for {}".format(self.target_binary.binary_name))
        print("="*60)
        # 0. Binary file preview
        self.target_binary.preview()

        # 1. Preview feature matching results
        print("\n🔍 Feature matching results:")
        print(f"   Number of matched TPLs: {len(self.feature_matching_results)}")
        if self.feature_matching_results:
            for i, lib in enumerate(self.feature_matching_results, 1):
                print(f"   {i}. {lib.name} - Number of matched features: {len(lib.matched_strings)}")
        else:
            print("   No matched TPL found")
        
        # 2. Preview TPL analysis results
        print("\n🤖 TPL analysis results:")
        print(f"   Number of TPLs identified by Agent: {len(self.tpl_analysis_results)}")
        if self.tpl_analysis_results:
            for i, lib in enumerate(self.tpl_analysis_results, 1):
                print(f"   {i}. {lib.name}")
                print(f"      Description: {lib.description}")
                print(f"      Reasoning: {lib.reasoning}")
                print(f"      Evidence type: {lib.evidence_type}")
                print(f"      Number of evidences: {len(lib.evidences)}")
                print(f"      Evidence examples: {lib.evidences[:5]}")
        else:
            print("   Agent did not identify any TPL")
        
        # 3. Preview validation step 1 results
        print("\n✅ Validation Step 1: Reasonableness of identified results")
        print(f"   Number of validated TPLs: {len(self.validation_step_1_results)}")
        if self.validation_step_1_results:
            passed_count = sum(1 for result in self.validation_step_1_results if result.is_reasonable)
            print(f"   Passed: {passed_count}/{len(self.validation_step_1_results)}")
            for i, result in enumerate(self.validation_step_1_results, 1):
                status = "✅" if result.is_reasonable else "❌"
                print(f"   {i}. {status} {result.library_name}")
                print(f"      Confidence: {result.confidence}")
                print(f"      Analysis: {result.reasoning}")
        else:
            print("   No validation step 1 data")
        
        # 4. Preview validation step 2 results
        print("\n🔍 Validation Step 2: Redundancy of all reasonable results")
        print(f"   Number of TPLs in redundancy analysis: {len(self.validation_step_2_results)}")
        if self.validation_step_2_results:
            kept_count = sum(1 for result in self.validation_step_2_results if result.should_keep)
            print(f"   Kept TPLs: {kept_count}/{len(self.validation_step_2_results)}")
            for i, result in enumerate(self.validation_step_2_results, 1):
                status = "✅" if result.should_keep else "❌"
                print(f"   {i}. {status} {result.library_name}")
                print(f"      Analysis: {result.reasoning}")
        else:
            print("   No validation step 2 data")
        print("="*60)
        print(f"Efficiency and cost analysis")
        print("="*60)
        # 5. Print time cost
        print("\n⏱️  Time cost:")
        if self.durations:
            for step, duration in self.durations.items():
                print(f"   {step}: {duration} seconds")
        else:
            print("   No time cost data")
        
        # 6. Print token cost
        print("\n💰 Token cost:")

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
            print(f"   Total input tokens: {total_input} tokens, Total output tokens: {total_output} tokens, Total tokens: {total_tokens} tokens")

            total_cost = total_input * 2/1_000_000 + total_output * 8/1_000_000
            print(f"   Total cost: ${total_cost:.6f} (assuming unit price: input tokens $2/million, output tokens $8/million)")
        else:
            print("   No cost data")
        
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
    succeed: bool = True  # Whether the analysis succeeded
    error_message: str = None

    def dump_to_file(self, file_path: str):
        """
        Serialize the analysis result and save it to a file
        """
        import json
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self.customer_serialize(), f, ensure_ascii=False, indent=4)

    @classmethod
    def init_from_file(cls, file_path: str):
        """
        Load analysis result from a file
        """
        import json
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return cls.init_from_dict(data)

    def get_simple_result(self) -> SimpleResult:
        """
        Get a simplified analysis result
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
    Binary file context information (reserved interface)
    """
    # Project basic information
    project_root_path: str = ""
    project_type: str = ""  # web application, desktop software, library, etc.
    project_description: str = ""  # Project description extracted from README, etc.

    # File location information
    file_relative_path: str = ""  # Path relative to the project root directory
    directory_context: str = ""  # File types and purposes in the directory

    # Project structure information
    key_files: List[str] = dataclasses.field(default_factory=list)  # Key file list
    build_system: str = ""  # CMake, Makefile, npm, etc.

    # Function inference
    likely_purpose: str = ""  # The possible purpose of this binary file
    related_binaries: List[str] = dataclasses.field(default_factory=list)  # Other related binary files


class TPLDetectionTaskStatus(Enum):
    """
    Task status
    """
    PENDING = "pending"  # Task is pending
    FILE_DOWNLOADING = "file_downloading"  # File is downloading
    ANALYZING = "analyzing"  # Task is analyzing
    RESULT_UPLOADING = "result_uploading"  # Result is uploading
    SUCCESS = "success"  # Task succeeded
    FAILED = "failed"

    def customer_serialize(self) -> str:
        return self.value

    @classmethod
    def init_from_dict(cls, data: str) -> 'TPLDetectionTaskStatus':
        return cls(data)

@dataclass
class TPLDetectionTask(Serializable):
    task_id: str
    file_minio_path: str # minio path
    file_local_path: str = None  # Local temporary path
    workspace_dir: str = None  # Dedicated working directory for the task

    start_at: str = dataclasses.field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    end_at: str = None
    
    # Timestamps for each step
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



