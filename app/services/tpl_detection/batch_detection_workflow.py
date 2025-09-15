import concurrent.futures
from typing import List, Optional

from loguru import logger

from .agent_analysis.response_models import SoftwareContext
from .detection_workflow import DetectionWorkflow
from ...interface import AnalysisResult
from tqdm import tqdm


def _process_single_file(args):
    """
    Function to process a single file. Must be defined at module level to support
    multiprocessing serialization.
    args: (idx, file_path, detection_kwargs, software_context)
    """
    idx, file_path, detection_kwargs, software_context = args
    try:
        workflow = DetectionWorkflow(**detection_kwargs)
        result = workflow.run(file_path, software_context=software_context)
        if not result.succeed:
            logger.warning(
                f"File {file_path} analysis failed: {result.error_message}, try again with retry"
            )
            workflow = DetectionWorkflow(**detection_kwargs)
            result = workflow.run(file_path, software_context=software_context)
            if not result.succeed:
                logger.error(
                    f"File {file_path} analysis failed again: {result.error_message}, skipped."
                )
            else:
                logger.success(f"File {file_path} analysis succeeded on retry.")
        return idx, result
    except Exception as e:
        error_message = f"{e}"
        return idx, error_message


class BatchDetectionWorkflow:
    def __init__(self, concurrency: int = 4, **detection_kwargs):
        """
        concurrency: number of concurrent workers
        detection_kwargs: parameters passed to DetectionWorkflow
        """
        self.concurrency = concurrency
        self.detection_kwargs = detection_kwargs

    def run_batch(self, file_paths: List[str], software_context: SoftwareContext = None) -> List[
        Optional[AnalysisResult]]:
        """
        Concurrently analyze multiple binary files (multiprocessing version).
        file_paths: list of binary file paths to analyze
        Returns: AnalysisResult for each file; None if failed
        """
        results = [None] * len(file_paths)

        # Prepare argument list
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
                               desc="Batch analysis progress"):
                idx, result = future.result()
                results[idx] = result

        return results