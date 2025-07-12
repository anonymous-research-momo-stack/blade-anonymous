from app.interface import TargetBinary
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

    def run(self, file_path):
        """
        Run the detection workflow with the given arguments.
        """
        # 1. Prepare File
        root_path, target_binary_files = self.file_preprocessor.prepare_target_files(file_path)

        # 2. Run Detection
        detection_results = []
        for target_binary in target_binary_files:
            detection_result = self._run_detection(root_path, target_binary)
            detection_results.append(detection_result)

        # 3. Return Results
        return detection_results

    def _run_detection(self, root_path, target_binary: TargetBinary):
        """
        Run the detection on the prepared files.
        """
        # 执行特征匹配检测
        candidate_libraries = self.feature_matching_detector.detect(
            target_binary=target_binary
        )
        
        # 构建检测结果
        detection_result = {
            'binary_name': target_binary.binary_name,
            'binary_path': target_binary.absolute_path,
            'candidate_libraries': candidate_libraries,  # Library接口类型列表
            'total_candidates': len(candidate_libraries)
        }
        
        return detection_result

























