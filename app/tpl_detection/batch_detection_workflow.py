import concurrent.futures
from typing import List, Optional
from app.tpl_detection.detection_workflow import DetectionWorkflow
from app.interface import AnalysisResult
from tqdm import tqdm

class BatchDetectionWorkflow:
    def __init__(self, concurrency: int = 4, **detection_kwargs):
        """
        concurrency: 并发数量
        detection_kwargs: 传递给 DetectionWorkflow 的参数
        """
        self.concurrency = concurrency
        self.detection_kwargs = detection_kwargs

    def run_batch(self, file_paths: List[str]) -> List[Optional[AnalysisResult]]:
        """
        并发分析多个二进制文件
        file_paths: 待分析的二进制文件路径列表
        返回: 每个文件的 AnalysisResult，失败则为 None
        """
        results = [None] * len(file_paths)
        def task(idx, file_path):
            try:
                workflow = DetectionWorkflow(**self.detection_kwargs)
                return idx, workflow.run(file_path)
            except Exception as e:
                # 可根据需要记录异常
                error_message = f"{e}"
                return idx, error_message

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.concurrency) as executor:
            future_to_idx = {
                executor.submit(task, idx, file_path): idx
                for idx, file_path in enumerate(file_paths)
            }
            for future in tqdm(concurrent.futures.as_completed(future_to_idx), total=len(file_paths), desc="批量分析进度"):
                idx, result = future.result()
                results[idx] = result
        return results 