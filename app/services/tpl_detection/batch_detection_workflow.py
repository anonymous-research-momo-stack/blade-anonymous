import concurrent.futures
from typing import List, Optional

from app.services.tpl_detection.agent_analysis.response_models import SoftwareContext
from app.services.tpl_detection.detection_workflow import DetectionWorkflow
from app.interface import AnalysisResult
from tqdm import tqdm


def _process_single_file(args):
    """
    处理单个文件的函数，需要在模块级别定义以支持多进程序列化
    args: (idx, file_path, detection_kwargs, software_context)
    """
    idx, file_path, detection_kwargs, software_context = args
    try:
        workflow = DetectionWorkflow(**detection_kwargs)
        return idx, workflow.run(file_path, software_context=software_context)
    except Exception as e:
        error_message = f"{e}"
        return idx, error_message


class BatchDetectionWorkflow:
    def __init__(self, concurrency: int = 4, **detection_kwargs):
        """
        concurrency: 并发数量
        detection_kwargs: 传递给 DetectionWorkflow 的参数
        """
        self.concurrency = concurrency
        self.detection_kwargs = detection_kwargs

    def run_batch(self, file_paths: List[str], software_context: SoftwareContext = None) -> List[
        Optional[AnalysisResult]]:
        """
        并发分析多个二进制文件（多进程版本）
        file_paths: 待分析的二进制文件路径列表
        返回: 每个文件的 AnalysisResult，失败则为 None
        """
        results = [None] * len(file_paths)

        # 准备参数列表
        args_list = [
            (idx, file_path, self.detection_kwargs, software_context)
            for idx, file_path in enumerate(file_paths)
        ]

        with concurrent.futures.ProcessPoolExecutor(max_workers=self.concurrency) as executor:
            future_to_idx = {
                executor.submit(_process_single_file, args): args[0]
                for args in args_list
            }

            for future in tqdm(concurrent.futures.as_completed(future_to_idx), total=len(file_paths),
                               desc="批量分析进度"):
                idx, result = future.result()
                results[idx] = result

        return results