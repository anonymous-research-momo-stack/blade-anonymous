import dataclasses
import json
import traceback
from dataclasses import asdict, fields
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Type, Any
from typing import List

from loguru import logger

from app.interface import SimpleResult, AnalysisResult
from app.tpl_detection.agent_analysis.response_models import SoftwareContext


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
class TestBinary(Serializable):
    original_name: str  # Original name of the binary file
    relative_path: str  # Path of the binary file Relative to the test case directory
    file_size_kb: float  # Size of the binary file in KB
    sha256: str = None
    notes: str = None  # Notes about the binary file


@dataclass
class ReusedLibrary(Serializable):
    name: str  # Name of the library
    vendor: str  # Vendor of the library
    repository: str  # Source Code Repository URL of the library
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
class Benchmark(Serializable):
    name: str  # benchmark name
    version: str  # benchmark version
    notes: List[BenchmarkNote]
    test_cases: List[TestCase]

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

    ground_truth_lib_names: List[str] = dataclasses.field(default_factory=list)  # Ground Truth Libraries
    detected_lib_names: List[str] = dataclasses.field(default_factory=list)  # Detected Libraries

    hs_fn: bool = False  # Has False Negative, if True, means there are libraries in ground truth that are not detected
    hs_fp: bool = False  # Has False Positive, if True, means there are libraries detected that are not in ground truth

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

    1. 消融整个Agent分析
    2. 消融 Agent 识别
    3. 消融 Agent 验证
        3.1 消融 合理性 验证
        3.2 消融 冗余性 验证
        3.3 消融全部验证
    """

    wo_agent_analysis: EffectivenessData = None  # Effectiveness data without agent analysis
    wo_agent_analysis_top_1:EffectivenessData = None # Effectiveness data without agent analysis, only top 1
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

    # cost


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
    rq_1_data: EffectivenessData = None  # Data for research question 1

    # rq 2 消融实验
    rq_2_data: AblationData = None  # Data for research question 2

    # rq 3 效率
    rq_3_data: EfficiencyData = None  # Data for research question 3

    # rq 4 实例实验

@dataclass
class EvaluationConfig(Serializable):
    """
    Configuration for evaluation
    """
    # input
    benchmark_file: str
    test_case_dir: str

    # llm
    llm_provider: str = 'openai'  # LLM provider, e.g., OpenAI, Azure, etc.
    llm_model_id: str = 'gpt-4o'
    input_token_price_per_1M: float = 2.0  # Price per million input tokens
    output_token_price_per_1M: float = 8.0

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
