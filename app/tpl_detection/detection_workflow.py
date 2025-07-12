from typing import List

from app.config import settings
from app.interface import TargetBinary, Library
from app.tpl_detection.agent_analysis.binary_analyzer import BinaryAnalyzer
from app.tpl_detection.feature_matching.feature_matching_detector import FeatureMatchingDetector
from app.tpl_detection.file_preparation.file_preprocessor import FilePreprocessor


class DetectionWorkflow:
    """
    A class to represent a detection workflow.
    """

    def __init__(self, 
                 top_n: int = 10, 
                 min_match_num: int = 5,
                 min_effective_string_length: int = 10):
        """
        初始化检测工作流
        
        Args:
            top_n: 返回前N个候选库
            min_match_num: 最少匹配字符串数量
            min_effective_string_length: 有效字符串的最小长度
        """
        self.file_preprocessor = FilePreprocessor()
        self.feature_matching_detector = FeatureMatchingDetector(
            top_n=top_n,
            min_match_feature_num=min_match_num,
            min_effective_string_length=min_effective_string_length
        )
        self.binary_analyzer = BinaryAnalyzer(
            knowledge_json_path=settings.KNOWLEDGE_FILE_PATH
        )

    def run(self, file_path):
        """
        Run the detection workflow with the given arguments.
        """
        # 1. Prepare File
        root_path, target_binary_files = self.file_preprocessor.prepare_target_files(file_path)

        # 2. Run Feature Matching Detection
        detection_results = []
        for target_binary in target_binary_files:
            libraries = self._run_tpl_detection(root_path, target_binary)
            detection_results.append((target_binary, libraries))


        # 3. Run Agent Analysis
        # TODO: Analyze the Context
        for target_binary, libraries in detection_results:
            self._run_agent_analysis(root_path, target_binary, libraries)

        # 3. Return Results
        return detection_results

    def _run_tpl_detection(self, root_path, target_binary: TargetBinary)-> List[Library]:
        """
        Run the detection on the prepared files.
        """
        # 执行特征匹配检测
        candidate_libraries = self.feature_matching_detector.detect(
            target_binary=target_binary
        )

        libraries = candidate_libraries
        return libraries


    def _run_agent_analysis(self, root_path, target_binary: TargetBinary, candidate_libraries:List[Library]):

        # 1. Supplement information of the target binary, from LLM itself, web searching, and KnowledgeBase
        self.binary_analyzer.analyze(target_binary) # TODO 增加设置，支持是否开启搜索，是否开启知识库查询等
        print(target_binary.information.description, target_binary.information.source_library.description)

        # 2. Try to find TPLs from the strings

        # 3. Cross Validate the candidate TPLs

        # 4. remove the duplicate TPLs



























