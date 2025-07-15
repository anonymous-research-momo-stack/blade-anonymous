import os.path
import time
from typing import List

from app.interface import AnalysisResult
from app.tpl_detection.batch_detection_workflow import BatchDetectionWorkflow
from evaluation.interface import EvaluationConfig, Benchmark, EvaluationReport


class Evaluator:
    def __init__(self,config:EvaluationConfig):
        self.evaluation_config = config

        self.benchmark = Benchmark.load_from_json_file(config.benchmark_file)

        self.batch_detection_workflow = BatchDetectionWorkflow(concurrency=config.concurrency)

        self.evaluation_results = []

        self.report = EvaluationReport(
            evaluation_config=config,
            benchmark=self.benchmark,
        )

    def run_benchmark(self):
        """
        运行，以获取结果
        :return:
        """
        relative_paths = [tc.test_binary.relative_path for tc in self.benchmark.test_cases][self.evaluation_config.slice_start:self.evaluation_config.slice_end]
        absolute_paths = [os.path.join(self.evaluation_config.test_case_dir, path) for path in relative_paths]

        start_time = time.perf_counter()
        self.report.start_at = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(start_time))
        results = self.batch_detection_workflow.run_batch(absolute_paths)
        total_time = time.perf_counter() - start_time
        self.report.finished_at = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(start_time + total_time))

        self.report.evaluation_results = results

    @classmethod
    def check_result(cls, benchmark:Benchmark, evaluation_results:List[AnalysisResult]):
        """
        检查结果，与Ground Truth进行对比
        :return:
        """
        ground_truth_dict = {test_case.test_binary.relative_path: test_case.reused_libraries for test_case in benchmark.test_cases}
        for result in evaluation_results:
            ground_truth_reused_libraries = ground_truth_dict.get(result.target_binary.relative_path, [])

            tp_library_names = []
            fp_library_names = []
            fn_library_names = []

            detected_libraries = [lib.name for lib in result.detected_libraries]

        pass


    def generate_report(self):
        """
        生成报告
        1. 效果
        2. 效率
        3. 成本

        :return:
        """
        pass


def main():
    # Example usage
    config = EvaluationConfig(
        benchmark_file="/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent/evaluation/benchmark_meta/FTPL50.json",
        test_case_dir="/Users/liuchengyue/Desktop/BinarySCA Platform/Data/Test_Cases/TPL_Test_Cases/Benchmarks/FTPL100/decompressed_deb",
        concurrency=5,
        slice_start=0,
        slice_end=-1,
    )

    evaluator = Evaluator(config)
    evaluator.run_benchmark()

    evaluation_report_save_path = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/tmp/evaluation_report.json"
    evaluator.report.dump(evaluation_report_save_path)


if __name__ == '__main__':
    main()