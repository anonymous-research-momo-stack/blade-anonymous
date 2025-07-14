import os.path
import time

from app.tpl_detection.batch_detection_workflow import BatchDetectionWorkflow
from evaluation.interface import EvaluationConfig, Benchmark, EvaluationReport


class Evaluator:
    def __init__(self,config:EvaluationConfig):
        self.config = config

        self.benchmark = Benchmark.load_from_json_file(config.benchmark_file)

        self.batch_detection_workflow = BatchDetectionWorkflow(concurrency=config.concurrency)

        self.report = EvaluationReport(
            evaluation_config=config,
            benchmark=self.benchmark,
        )

    def run_benchmark(self):
        """
        运行，以获取结果
        :return:
        """
        relative_paths = [tc.test_binary.relative_path for tc in self.benchmark.test_cases][self.config.slice_start:self.config.slice_end]
        absolute_paths = [os.path.join(self.config.test_case_dir, path) for path in relative_paths]

        start_time = time.perf_counter()
        self.report.start_at = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(start_time))
        results = self.batch_detection_workflow.run_batch(absolute_paths)
        total_time = time.perf_counter() - start_time
        self.report.finished_at = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(start_time + total_time))

        self.report.evaluation_results = results


    def check_result(self):
        """
        检查结果，与Ground Truth进行对比
        :return:
        """
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