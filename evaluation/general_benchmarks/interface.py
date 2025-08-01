import dataclasses
import json
import traceback
from dataclasses import asdict, fields
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Type, Any, Optional, get_origin, get_args, Union
from typing import List

from loguru import logger

from app.config import settings
from app.interface import SimpleResult, AnalysisResult
from app.tpl_detection.agent_analysis.response_models import SoftwareContext
from evaluation.conan_benchmark.compiled_files_parser import cal_sha256
import os

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
            elif isinstance(value, dict):
                # 处理字典类型的序列化
                serialized_dict = {}
                for key, val in value.items():
                    if hasattr(val, 'customer_serialize'):
                        serialized_dict[key] = val.customer_serialize()
                    elif isinstance(val, list) and val and hasattr(val[0], 'customer_serialize'):
                        serialized_dict[key] = [item.customer_serialize() for item in val]
                    else:
                        serialized_dict[key] = val
                serialized_data[field.name] = serialized_dict
        return serialized_data

    @classmethod
    def init_from_dict(cls: Type['Serializable'], data: Dict[str, Any]) -> 'Serializable':
        init_args = {}
        for field in fields(cls):
            try:
                field_value = data.get(field.name)

                # 如果字段值为None，直接使用默认值
                if field_value is None:
                    init_args[field.name] = field_value
                    continue

                # 获取类型信息
                field_type = field.type
                origin_type = get_origin(field_type)
                type_args = get_args(field_type)

                # 处理直接的自定义类
                if hasattr(field_type, 'init_from_dict') and isinstance(field_value, dict):
                    init_args[field.name] = field_type.init_from_dict(field_value)

                # 处理 List[CustomClass] 类型
                elif (origin_type is list and
                      isinstance(field_value, list) and
                      type_args and
                      hasattr(type_args[0], 'init_from_dict') and
                      all(isinstance(i, dict) for i in field_value if i is not None)):
                    init_args[field.name] = [type_args[0].init_from_dict(item) for item in field_value if
                                             item is not None]

                # 处理 Dict[str, List[CustomClass]] 类型
                elif (origin_type is dict and
                      isinstance(field_value, dict) and
                      len(type_args) >= 2):

                    value_type = type_args[1]  # 获取字典值的类型
                    value_origin = get_origin(value_type)
                    value_args = get_args(value_type)

                    # 如果字典值是 List[CustomClass] 类型
                    if (value_origin is list and
                            value_args and
                            hasattr(value_args[0], 'init_from_dict')):
                        processed_dict = {}
                        for key, value_list in field_value.items():
                            if isinstance(value_list, list):
                                processed_dict[key] = [value_args[0].init_from_dict(item)
                                                       for item in value_list
                                                       if isinstance(item, dict)]
                            else:
                                processed_dict[key] = value_list
                        init_args[field.name] = processed_dict

                    # 如果字典值是直接的自定义类 Dict[str, CustomClass]
                    elif hasattr(value_type, 'init_from_dict'):
                        processed_dict = {}
                        for key, value_item in field_value.items():
                            if isinstance(value_item, dict):
                                processed_dict[key] = value_type.init_from_dict(value_item)
                            else:
                                processed_dict[key] = value_item
                        init_args[field.name] = processed_dict

                    else:
                        # 普通字典，直接赋值
                        init_args[field.name] = field_value

                # 处理 Union 类型（包括 Optional）
                elif origin_type is Union:
                    # 尝试按照Union中的每个类型进行初始化
                    initialized = False
                    for union_type in type_args:
                        if union_type is type(None):  # 跳过 None 类型
                            continue
                        try:
                            if hasattr(union_type, 'init_from_dict') and isinstance(field_value, dict):
                                init_args[field.name] = union_type.init_from_dict(field_value)
                                initialized = True
                                break
                        except:
                            continue

                    if not initialized:
                        init_args[field.name] = field_value

                else:
                    # 其他情况，直接赋值
                    init_args[field.name] = field_value

            except Exception as e:
                logger.error(f"Error in {cls.__name__}, field: {field.name}, type: {field.type}")
                logger.error(f"Field value: {field_value}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                raise e

        return cls(**init_args)

@dataclass
class CompileConfig(Serializable):
    conan_version:str
    profile:str

@dataclass
class TestBinary(Serializable):
    original_name: str  # Original name of the binary file
    relative_path: str  # Path of the binary file Relative to the test case directory
    file_size_kb: float  # Size of the binary file in KB
    sha256: str = None
    notes: str = None  # Notes about the binary file
    compile_config: Optional[CompileConfig] = None  # Compile configuration, e.g., conan version, profile

@dataclass
class ReusedLibrary(Serializable):
    name: str  # Name of the library
    vendor: str = None # Vendor of the library
    repository: str  = None# Source Code Repository URL of the library
    other_names: List[str] = dataclasses.field(default_factory=list)  # Other names of the library
    version: str = None  # Version of the Library
    description: str = None  # A concise sentence to Description of the library
    type: str = None  # A phrase or a couple of words to describe the type of the library
    notes: str = None  # Notes about the library


@dataclass
class TestCase(Serializable):
    test_binary: TestBinary  # Target binary file
    reused_libraries: List[ReusedLibrary]  # Ground Truth, Static Reused Libraries


@dataclass
class BenchmarkMeta(Serializable):
    name: str  # benchmark name
    test_case_num: int
    covered_library_num: int
    version: str  # benchmark version


@dataclass
class BenchmarkNote(Serializable):
    message: str
    update_at: str = dataclasses.field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

@dataclass
class BenchmarkSummary(Serializable):
    test_case_num: int  # Number of test cases
    covered_library_num: int  # Number of covered libraries


@dataclass
class Benchmark(Serializable):
    name: str  # benchmark name
    version: str  # benchmark version
    summary: BenchmarkSummary = None  # Summary of the benchmark
    notes: List[BenchmarkNote] = dataclasses.field(default_factory=list)  # Notes about the benchmark
    test_cases: List[TestCase] = dataclasses.field(default_factory=list)  # List of test cases in the benchmark

    @classmethod
    def load_from_json_file(cls, json_path: str) -> 'Benchmark':
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.init_from_dict(data)

    def dump_to_json_file(self, json_path: str):
        data = self.customer_serialize()
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return json_path

    def get_meta(self):
        # count the number of test cases and covered libraries
        test_case_num = len(self.test_cases)  # test case
        covered_library_repository_set = set()  # TPL Repository
        tpl_names = set()  # TPL Name
        for tc in self.test_cases:
            for reused_lib in tc.reused_libraries:
                covered_library_repository_set.add(reused_lib.name)
                tpl_names.add(reused_lib.name)

        # generate the benchmark meta
        benchmark_meta = BenchmarkMeta(
            name=self.name,
            test_case_num=test_case_num,
            covered_library_num=len(covered_library_repository_set),
            version=self.version,
        )

        return benchmark_meta

    def update_sha256(self, new_test_case_dir_path:str):
        for tc in self.test_cases:
            tc_path = os.path.join(new_test_case_dir_path, tc.test_binary.relative_path)
            tc.test_binary.sha256 = cal_sha256(tc_path)

    def __repr__(self):
        return self.get_meta().__repr__()

@dataclass
class AnalysisResultCheck(Serializable):

    """
    1. 结果的验证
    2. 记录TP, FP, FN
    """
    binary_name: str = None  # Name of the binary file
    binary_path: str = None  # Path of the binary file, relative to the test case directory
    binary_hash: str = None  # Hash of the binary file, used for verification

    perfect:bool = False
    has_multi_results:bool = False
    no_results:bool = False  # No results detected, if True, means no libraries are detected in this binary
    hs_fn: bool = False  # Has False Negative, if True, means there are libraries in ground truth that are not detected
    hs_fp: bool = False  # Has False Positive, if True, means there are libraries detected that are not in ground truth
    result_count:int = 0  # Number of results in this check
    tp_count:int = 0  # True Positive count
    fp_count:int = 0  # False Positive count
    fn_count:int = 0  # False Negative count

    ground_truth_lib_names: List[str] = dataclasses.field(default_factory=list)  # Ground Truth Libraries
    detected_lib_names: List[str] = dataclasses.field(default_factory=list)  # Detected Libraries

    tp_lib_names: List[str] = dataclasses.field(default_factory=list)  # True Positive Libraries
    fp_lib_names: List[str] = dataclasses.field(default_factory=list)  # False Positive Libraries
    fn_lib_names: List[str] = dataclasses.field(default_factory=list)  # False Negative Libraries


@dataclass
class EffectivenessData(Serializable):
    """
    Effectiveness
    """
    # rq 1
    tp_count: int = None  # Trues Positive count
    fp_count: int = None  # False Positive count
    fn_count: int = None  # False Negative count

    precision: float = None  # Precision of the analysis
    recall: float = None  # Recall of the analysis
    f1_score: float = None  # F1 Score of the analysis

@dataclass
class AblationData(Serializable):
    """
    分析几个主要环节的贡献

    1. 消融整个Agent分析 (仅保留特征匹配结果）
    2. 消融 Agent 识别
    3. 消融 Agent 验证
        3.1 消融 合理性 验证
        3.2 消融 冗余性 验证
        3.3 消融全部验证
    """

    wo_agent_analysis: EffectivenessData = None  # Effectiveness data without agent analysis
    wo_agent_analysis_top_1:EffectivenessData = None # Effectiveness data without agent analysis, only keep the top 1 results
    wo_agent_analysis_top_2:EffectivenessData = None # Effectiveness data without agent analysis, only keep the top 2 results
    wo_agent_analysis_top_3:EffectivenessData = None # Effectiveness data without agent analysis, only keep the top 3 results
    wo_agent_tpl_analysis: EffectivenessData = None  # Effectiveness data without agent analysis
    wo_validation_step_1: EffectivenessData = None  # Effectiveness data without validation step 1
    wo_validation_step_2: EffectivenessData = None  # Effectiveness data without validation step 2
    wo_validation_step_1_and_2: EffectivenessData = None  # Effectiveness data without validation step 1 and 2


@dataclass
class EfficiencyData(Serializable):
    """
    Data structure for research question data
    """
    # file size
    total_file_size_kb: float = None  # Total file size in KB
    average_file_size_kb: float = None  # Average file size in KB

    # duration
    total_theoretical_duration: float = None  # Total detection duration in seconds
    average_theoretical_duration: float = None  # Average detection duration in seconds

    total_actual_duration: float = None  # Total actual duration in seconds
    average_actual_duration: float = None  # Average actual duration in seconds

    duration_breakdown: dict = dataclasses.field(default_factory=dict)  # Breakdown of duration by step, e.g., {'agent_analysis': 10.5, 'tpl_analysis': 5.0, 'validation': 2.0}



@dataclass
class CostData(Serializable):
    """
    Data structure for research question data
    """
    # token
    input_token_count:int = None  # Input token count
    output_token_count:int = None  # Output token count
    total_token_count:int = None  # Total token count

    # cost
    total_cost: float = None  # Total cost in USD
    average_cost: float = None  # Average cost per analysis in USD

@dataclass
class ResearchQuestionData(Serializable):
    """
    Data structure for research question data
    """
    # rq 1 效果
    effectiveness: EffectivenessData = None  # Data for research question 1

    # rq 2 消融实验
    effectiveness_ablation_study: AblationData = None  # Data for research question 2

    # rq 3 效率
    efficiency: EfficiencyData = None  # Data for research question 3

    # rq 4 成本
    cost: CostData = None

@dataclass
class EvaluationConfig(Serializable):
    """
    Configuration for evaluation
    """
    # input
    benchmark_file: str
    test_case_dir: str

    # llm
    llm_provider: str = settings.LLM_PROVIDER  # LLM provider, e.g., OpenAI, Azure, etc.
    llm_model_id: str = settings.LLM_MODEL_ID
    input_token_price_per_1M: float = 2.0  # Price per million input tokens
    output_token_price_per_1M: float = 8.0

    # workflow settings
    feature_matching_top_n:int = 3
    use_agent:bool = True

    # process
    concurrency: int = 3

    # test cases
    slice_start: int = 0
    slice_end: int = -1



@dataclass
class SimpleEvaluationReport(Serializable):
    start_at: str = None
    finished_at: str = None
    evaluation_config: EvaluationConfig = None
    benchmark_meta: BenchmarkMeta = None
    research_question_data: ResearchQuestionData = None
    evaluation_results_check: List[AnalysisResultCheck] = dataclasses.field(default_factory=list)
    simple_results: List[SimpleResult] = dataclasses.field(default_factory=list)


@dataclass
class EvaluationReport(Serializable):
    start_at: str = None
    finished_at: str = None
    evaluation_config: EvaluationConfig = None
    research_question_data: ResearchQuestionData = None
    evaluation_results_check: List[AnalysisResultCheck] = dataclasses.field(default_factory=list)
    software_context: SoftwareContext = None
    evaluation_results: List[AnalysisResult] = None
    benchmark: Benchmark = None




    def dump(self, file_path):
        data = self.customer_serialize()
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

        simple_report = self.get_simple_report()
        simple_report_save_path = file_path.replace('.json', '_simple.json')
        with open(simple_report_save_path, 'w', encoding='utf-8') as f:
            json.dump(simple_report.customer_serialize(), f, indent=4, ensure_ascii=False)

    @classmethod
    def load_from_file(cls, file_path: str) -> 'EvaluationReport':
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.init_from_dict(data)

    def get_simple_report(self):
        """
        Dump a simplified version of the report, focusing on essential information.
        """
        simple_report = SimpleEvaluationReport(
            start_at=self.start_at,
            finished_at=self.finished_at,
            evaluation_config=self.evaluation_config,
            benchmark_meta=self.benchmark.get_meta() if self.benchmark else None,
            research_question_data=self.research_question_data,
            evaluation_results_check=self.evaluation_results_check,
            simple_results=[r.get_simple_result() for r in self.evaluation_results] if self.evaluation_results else []
        )

        return simple_report
