import time
from typing import List
from loguru import logger

from app.config import settings
from app.interface import TargetBinary, Library, AnalysisData, AnalysisResult, AnalysisConfig
from app.tpl_detection.agent_analysis.bin_info_finder import BinaryInformationFinder
from app.tpl_detection.agent_analysis.contex_analyzer import SoftwareContextAnalyzer, SoftwareContext
from app.tpl_detection.agent_analysis.tpl_analyzer import TPLAnalyzer
from app.tpl_detection.agent_analysis.validator import LibraryValidator
from app.tpl_detection.feature_matching.feature_matching_detector import FeatureMatchingDetector
from app.tpl_detection.file_preparation.file_preprocessor import FilePreprocessor

# 设置logger级别为INFO，这样debug级别的日志不会显示
logger.remove()
logger.add(lambda msg: None, level="INFO")


class DetectionWorkflow:
    """
    A class to represent a detection workflow.
    """

    def __init__(self,
                 feature_matching_min_string_length: int = 5,
                 feature_matching_max_string_length: int = 500,
                 feature_matching_min_match_feature_num: int = 5,
                 feature_matching_return_top_n: int = 3,
                 enable_bin_info_analysis: bool = True,
                 enable_bin_info_analysis_web_search: bool = False,
                 enable_bin_info_analysis_knowledge_base: bool = False,
                 enable_tpl_analysis: bool = True,
                 enable_tpl_analysis_web_search: bool = False,
                 enable_tpl_analysis_knowledge_base: bool = False,
                 enable_library_validation_web_search: bool = False,
                 enable_library_validation_knowledge_base: bool = False,
                 enable_library_validation_db_verification: bool = False,
                 library_validation_debug_mode: bool = False):
        """
        初始化检测工作流
        """
        self.enable_bin_info_analysis = enable_bin_info_analysis

        # 构建分析配置对象
        self.analysis_config = AnalysisConfig(
            llm_provider=settings.LLM_PROVIDER,
            model_id=settings.LLM_MODEL_ID,
            feature_matching_min_string_length=feature_matching_min_string_length,
            feature_matching_max_string_length=feature_matching_max_string_length,
            feature_matching_min_match_feature_num=feature_matching_min_match_feature_num,
            feature_matching_return_top_n=feature_matching_return_top_n,
            enable_bin_info_analysis=enable_bin_info_analysis,
            enable_bin_info_analysis_web_search=enable_bin_info_analysis_web_search,
            enable_bin_info_analysis_knowledge_base=enable_bin_info_analysis_knowledge_base,
            enable_tpl_analysis=enable_tpl_analysis,
            enable_tpl_analysis_web_search=enable_tpl_analysis_web_search,
            enable_tpl_analysis_knowledge_base=enable_tpl_analysis_knowledge_base,
            enable_library_validation_web_search=enable_library_validation_web_search,
            enable_library_validation_knowledge_base=enable_library_validation_knowledge_base,
            enable_library_validation_db_verification=enable_library_validation_db_verification,
            library_validation_debug_mode=library_validation_debug_mode
        )

        # 上下文环境分析器
        self.context_analyzer = SoftwareContextAnalyzer(
                enable_web_search=True,
                debug_mode=False
            )

        # 文件预处理器
        self.file_preprocessor = FilePreprocessor()  # 预处理文件，解压，找到二进制文件等。

        # 特征匹配检测器
        self.feature_matching_detector = FeatureMatchingDetector(
            top_n=feature_matching_return_top_n, # 返回前N个候选库
            min_match_feature_num=feature_matching_min_string_length, # 至少匹配的数量
            feature_min_length=feature_matching_min_string_length, # 有效字符串的最小长度
            feature_max_length=feature_matching_max_string_length # 有效字符串的最大长度
        )

        # 二进制信息查找器
        if self.enable_bin_info_analysis:
            self.bin_info_finder = BinaryInformationFinder(
                enable_web_search=enable_bin_info_analysis_web_search, # 是否启用网络搜索
                enable_knowledge_base=enable_bin_info_analysis_knowledge_base, # 是否启用知识库
                knowledge_json_path=settings.KNOWLEDGE_FILE_PATH # 知识库文件路径
            )

        # TPL分析器
        self.tpl_analyzer = TPLAnalyzer(
            enable_web_search=enable_tpl_analysis_web_search,
            enable_knowledge_base=enable_tpl_analysis_knowledge_base,
            knowledge_json_path=settings.KNOWLEDGE_FILE_PATH
        )

        # 库验证器
        self.library_validator = LibraryValidator(
            enable_web_search=enable_library_validation_web_search,
            enable_knowledge_base=enable_library_validation_knowledge_base,
            enable_db_verification=enable_library_validation_db_verification,
            debug_mode=library_validation_debug_mode
        )

        self.analysis_data = AnalysisData(config=self.analysis_config)  # 分析数据对象，用于存储分析结果

    def analyze_context(self, software_root_path: str)->SoftwareContext:
        software_context, context_data = self.context_analyzer.analyze_software_context(software_root_path)
        return software_context

    def run(self, file_path:str,
            software_context:SoftwareContext=None) -> AnalysisResult:
        """
        Run the detection workflow with the given arguments.
        """

        all_start_at = time.perf_counter()

        # 1. Prepare File
        target_binary = self.file_preprocessor.basic_analyze(file_path)
        prepare_file_duration = time.perf_counter() - all_start_at
        self.analysis_data.durations["file_preparation"] = prepare_file_duration

        # 2. feature matching detection
        feature_matching_start_at = time.perf_counter()
        feature_matching_libraries = self._run_tpl_detection(target_binary)
        feature_matching_duration = time.perf_counter() - feature_matching_start_at
        self.analysis_data.durations["feature_matching"] = feature_matching_duration
        self.analysis_data.feature_matching_results = feature_matching_libraries

        # 3. agent analysis
        validation_start_at = time.perf_counter()
        validated_libraries = self._run_agent_analysis(target_binary, feature_matching_libraries,software_context)
        self.analysis_data.durations["agent_analysis"] = time.perf_counter() - validation_start_at

        # 4. Return Results
        result = AnalysisResult(
            target_binary=target_binary,
            detected_libraries=[lib for lib in validated_libraries if lib.validation_passed],
            analysis_data=self.analysis_data
        )
        total_duration = time.perf_counter() - all_start_at
        self.analysis_data.durations["total"] = total_duration
        return result

    def _run_tpl_detection(self, target_binary: TargetBinary) -> List[Library]:
        """
        Run the feature matching detection on the target binary.
        """
        # 执行特征匹配检测
        candidate_libraries = self.feature_matching_detector.detect(
            target_binary=target_binary
        )

        # 为特征匹配结果添加检测方法标记
        for lib in candidate_libraries:
            if "Feature Matching" not in lib.identify_methods:
                lib.identify_methods.append("Feature Matching")

        logger.debug(f"\n=== Feature Matching Results for {target_binary.binary_name} ===")
        logger.debug(f"Found {len(candidate_libraries)} candidate libraries:")
        for index, lib in enumerate(candidate_libraries, 1):
            logger.debug(f"{index}: {lib.name} - {len(lib.matched_strings)} matches")
            logger.debug(f"   Description: {lib.description}")

        return candidate_libraries

    def _run_agent_analysis(self, target_binary: TargetBinary,
                            candidate_libraries_from_feature_matching: List[Library],
                            software_context:SoftwareContext=None) -> List[Library]:
        """
        Run agent analysis including binary info analysis, TPL analysis, and validation.

        Returns:
            Final validated library list
        """

        # 1. Supplement information of the target binary
        if self.enable_bin_info_analysis:
            bin_info_finder_start_at = time.perf_counter()
            logger.debug(f"\n=== Binary Information Analysis for {target_binary.binary_name} ===")
            response = self.bin_info_finder.find_for(target_binary, software_context)
            bin_info_finder_duration = time.perf_counter() - bin_info_finder_start_at
            self.analysis_data.durations["bin_info_finder"] = bin_info_finder_duration
            self.analysis_data.costs["bin_info_finder"] = response.metrics

            if target_binary.information:
                source_lib_desc = "None"
                if target_binary.information.source_library:
                    source_lib_desc = target_binary.information.source_library.description

                logger.debug(f"Binary Description: {target_binary.information.description}")
                logger.debug(f"Source Library: {source_lib_desc}")
            else:
                logger.debug("No binary information available")

        # 2. Try to find TPLs from the strings
        candidate_libraries_from_agent = []
        if self.enable_bin_info_analysis:
            logger.debug(f"\n=== Agent TPL Analysis for {target_binary.binary_name} ===")
            tpl_analyzer_start_at = time.perf_counter()
            candidate_libraries_from_agent, response = self.tpl_analyzer.analyze(target_binary)
            tpl_analyzer_duration = time.perf_counter() - tpl_analyzer_start_at
            self.analysis_data.durations["tpl_analyzer"] = tpl_analyzer_duration
            self.analysis_data.costs["tpl_analyzer"] = response.metrics
            self.analysis_data.tpl_analysis_results = candidate_libraries_from_agent

            logger.debug(f"Agent identified {len(candidate_libraries_from_agent)} libraries:")
            for index, lib in enumerate(candidate_libraries_from_agent, 1):
                logger.debug(f"{index}: {lib.name}")
                logger.debug(f"   Description: {lib.description}")
                logger.debug(f"   Reasoning: {lib.reasoning}")

        # 3. Combine results
        all_candidate_libraries = self._combine_candidate_libraries(candidate_libraries_from_feature_matching,
                                                                    candidate_libraries_from_agent)
        logger.debug(f"\n=== Combined Candidates for {target_binary.binary_name} ===")
        logger.debug(f"Total candidates before validation: {len(all_candidate_libraries)}")

        # 4. Validate the candidate TPLs
        logger.debug(f"\n=== Library Validation for {target_binary.binary_name} ===")
        validated_libraries, process_data = self.library_validator.validate_libraries(
            libraries=all_candidate_libraries,
            target_binary=target_binary
        )

        # metrics
        step_1_response = process_data["step_1_response"]
        individual_results = process_data["individual_results"]
        step_2_response = process_data["step_2_response"]
        redundancy_results = process_data["redundancy_results"]

        if step_1_response:
            step_1_metrics = step_1_response.metrics
            self.analysis_data.durations["library_validation_step_1"] = step_1_metrics['time']
            self.analysis_data.costs["library_validation_step_1"] = step_1_metrics

        if step_2_response:
            step_2_metrics = step_2_response.metrics
            # duration
            self.analysis_data.durations["library_validation_step_2"] = step_2_metrics['time']
            # cost
            self.analysis_data.costs["library_validation_step_2"] = step_2_metrics
        else:
            self.analysis_data.durations["library_validation_step_2"] = 0
            self.analysis_data.costs["library_validation_step_2"] = {}

        self.analysis_data.validation_step_1_results = individual_results
        self.analysis_data.validation_step_2_results = redundancy_results

        # 输出验证结果统计
        passed_count = sum(1 for lib in validated_libraries if lib.validation_passed)
        failed_count = len(validated_libraries) - passed_count
        logger.debug(f"Validation completed: {passed_count} passed, {failed_count} failed")

        # 输出详细验证结果
        logger.debug(f"\n=== Final Results for {target_binary.binary_name} ===")
        for lib in validated_libraries:
            status = "✅ PASS" if lib.validation_passed else "❌ FAIL"
            methods = ', '.join(lib.identify_methods)
            logger.debug(f"""
{status} Library: {lib.name}
    Detection Methods: {methods}
    Description: {lib.description}
    Original Reasoning: {lib.reasoning}
    Validation Passed: {lib.validation_passed}
    Validation Reasoning: {lib.validation_reasoning}
            """)

        return validated_libraries

    def _combine_candidate_libraries(self, libraries_1: List[Library], libraries_2: List[Library]) -> List[Library]:
        """
        按照小写名称合并
        """

        combined_library_dict = {}
        for lib in libraries_1 + libraries_2:
            key = lib.name.lower()
            if key in combined_library_dict:
               existing_lib = combined_library_dict[key]
               existing_lib.matched_strings = list(set(existing_lib.matched_strings + lib.matched_strings))
               existing_lib.reasoning += lib.reasoning
               existing_lib.identify_methods=list(set(existing_lib.identify_methods + lib.identify_methods))
            else:
                combined_library_dict[key] = lib

        return list(combined_library_dict.values())

