import os.path
import time
from typing import List

from loguru import logger

from app.interface import AnalysisResult, AnalysisData
from app.tpl_detection.batch_detection_workflow import BatchDetectionWorkflow
from app.tpl_detection.detection_workflow import DetectionWorkflow
from evaluation.interface import EvaluationConfig, Benchmark, EvaluationReport, AnalysisResultCheck, \
    ResearchQuestionData


class Evaluator:
    def __init__(self, config: EvaluationConfig):
        self.evaluation_config = config

        self.benchmark = Benchmark.load_from_json_file(config.benchmark_file)

        self.workflow = DetectionWorkflow(
        feature_matching_return_top_n=5,
      )
        self.batch_detection_workflow = BatchDetectionWorkflow(concurrency=config.concurrency, feature_matching_return_top_n=5)

        self.evaluation_results = []

        self.report = EvaluationReport(
            evaluation_config=config,
            benchmark=self.benchmark,
        )

    def run_benchmark(self, analyze_context:bool=True):
        """
        运行，以获取结果
        :return:
        """
        relative_paths = [tc.test_binary.relative_path for tc in self.benchmark.test_cases][
                         self.evaluation_config.slice_start:self.evaluation_config.slice_end]
        absolute_paths = [os.path.join(self.evaluation_config.test_case_dir, path) for path in relative_paths]

        # run test cases
        start_time = time.perf_counter()
        self.report.start_at = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(start_time))

        context = None
        if analyze_context:
            logger.info("分析软件上下文...")
            context = self.workflow.analyze_context(self.evaluation_config.test_case_dir)
        logger.info(f"开始分析")
        results = self.batch_detection_workflow.run_batch(absolute_paths, software_context=context)
        total_time = time.perf_counter() - start_time
        self.report.finished_at = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(start_time + total_time))

        self.report.evaluation_results = results

        # 检查结果
        logger.info("检查结果...")
        results_check_lst = self.check_result(self.benchmark, results)
        self.report.evaluation_results_check = results_check_lst

        # 生成RQ数据
        logger.info("生成研究问题数据...")
        rq_data = self.cal_rq_data(
            evaluation_results=results,
            result_check_lst=results_check_lst,
            input_token_price_per_1M=self.evaluation_config.input_token_price_per_1M,  # 每百万输入token的价格, OpenAI GPT-4.1
            output_token_price_per_1M=self.evaluation_config.output_token_price_per_1M,
        )
        self.report.research_question_data = rq_data
        logger.info(f"All Done, total time: {total_time:.2f} seconds")

    def check_result(self, benchmark: Benchmark, evaluation_results: List[AnalysisResult]) -> List[AnalysisResultCheck]:
        """
        检查结果，与Ground Truth进行对比
        :return:
        """
        ground_truth_dict = {test_case.test_binary.sha256: test_case.reused_libraries for test_case in
                             benchmark.test_cases}
        results_check_lst = []
        for result in evaluation_results:
            ground_truth_reused_libraries = ground_truth_dict.get(result.target_binary.hash_sha256, [])

            undetected_gt_libraries = ground_truth_reused_libraries
            detected_gt_libraries = []

            tp_library_names = []
            fp_library_names = []

            # 检测到的库名称与Ground Truth进行对比
            for detected_lib in result.detected_libraries:
                tp = False
                for gt_lib in undetected_gt_libraries:
                    # 与Ground Truth 名称一致
                    if self.normalize_lib_name(detected_lib.name) == self.normalize_lib_name(gt_lib.name):
                        detected_gt_libraries.append(gt_lib)
                        undetected_gt_libraries.remove(gt_lib)
                        tp = True
                        break
                    # 与Ground Truth 名称的其他名称一致
                    elif self.normalize_lib_name(detected_lib.name) in [self.normalize_lib_name(lib_name) for lib_name
                                                                        in gt_lib.other_names]:
                        detected_gt_libraries.append(gt_lib)
                        undetected_gt_libraries.remove(gt_lib)
                        tp = True
                        break
                # 如果找到了匹配的Ground Truth库，则认为是TP，否则是FP
                if tp:
                    tp_library_names.append(detected_lib.name)
                else:
                    fp_library_names.append(detected_lib.name)

            # 未检测到的Ground Truth库，均认为是FN
            fn_library_names = [lib.name for lib in undetected_gt_libraries]

            # 生成分析结果检查对象
            analysis_result_check = AnalysisResultCheck(
                binary_name=result.target_binary.binary_name,
                binary_path=result.target_binary.absolute_path,
                binary_hash=result.target_binary.hash_sha256,
                ground_truth_lib_names=[lib.name for lib in ground_truth_reused_libraries],  # Ground Truth 库名称
                detected_lib_names=[lib.name for lib in result.detected_libraries],  # 检测到的库名称
                hs_fn=len(fn_library_names) > 0,  # 是否有漏报
                hs_fp=len(fp_library_names) > 0,  # 是否有误报
                tp_lib_names=tp_library_names,  # 真正检测到的库名称
                fp_lib_names=fp_library_names,  # 误报的库名称
                fn_lib_names=fn_library_names,  # 漏报的库名称
            )
            results_check_lst.append(analysis_result_check)
        return results_check_lst

    # 正规化名称
    def normalize_lib_name(self, lib_name: str):
        return lib_name.lower().strip()

    def cal_rq_data(self,
                    evaluation_results: List[AnalysisResult],
                    result_check_lst: List[AnalysisResultCheck],
                    input_token_price_per_1M: 2,  # 每百万输入token的价格, OpenAI GPT-4.1
                    output_token_price_per_1M: 8,  # 每百万输出token的价格, OpenAI GPT-4.1
                    ) -> ResearchQuestionData:
        """
        生成报告
        1. 效果
        2. 效率
        3. 成本

        :return:
        """

        # RQ 1，
        # TP, FP, FN,
        tp_count = sum(len(check.tp_lib_names) for check in result_check_lst)
        fp_count = sum(len(check.fp_lib_names) for check in result_check_lst)
        fn_count = sum(len(check.fn_lib_names) for check in result_check_lst)

        # Precision, Recall, F1-Score (百分比，保留两位小数)
        precision = round(tp_count / (tp_count + fp_count) * 100, 2) if (tp_count + fp_count) > 0 else 0.0
        recall = round(tp_count / (tp_count + fn_count) * 100, 2) if (tp_count + fn_count) > 0 else 0.0
        f1_score = round(2 * (precision * recall) / (precision + recall), 2) if (precision + recall) > 0 else 0.0

        # RQ 2 消融实验

        # RQ 3 效率和成本
        # 文件大小
        total_file_size = sum(result.target_binary.file_size_kb for result in evaluation_results)  # 总文件大小
        average_file_size = total_file_size / len(evaluation_results) if evaluation_results else 0.0  # 平均文件大小

        # 时间开销
        total_duration = sum(result.analysis_data.durations['total'] for result in evaluation_results)  # 总检测时间
        average_duration = total_duration / len(evaluation_results) if evaluation_results else 0.0  # 平均检测时间

        # 成本
        input_token_count = 0
        output_token_count = 0
        total_cost = 0.0
        for result in evaluation_results:
            for agent_name, cost_dict in result.analysis_data.costs.items():
                # input token
                input_tokens = sum(cost_dict.get('input_tokens', []))
                input_token_count += input_tokens

                # output token
                output_tokens = sum(cost_dict.get('output_tokens', []))
                output_token_count += output_tokens

                # cost
                input_cost = (input_tokens / 1_000_000) * input_token_price_per_1M
                output_cost = (output_tokens / 1_000_000) * output_token_price_per_1M
                total_cost += input_cost + output_cost
        average_cost = total_cost / len(evaluation_results) if evaluation_results else 0.0  # 平均成本

        rq_data = ResearchQuestionData(
            tp_count=tp_count,
            fp_count=fp_count,
            fn_count=fn_count,
            precision=precision,
            recall=recall,
            f1_score=f1_score,
            total_file_size_kb=total_file_size,
            average_file_size_kb=average_file_size,
            total_detection_duration=total_duration,
            average_detection_duration=average_duration,
            input_token_count=input_token_count,
            output_token_count=output_token_count,
            total_token_count=input_token_count + output_token_count,
            total_cost=total_cost,
            average_cost=average_cost,

        )

        return rq_data

def main():
    # 41 个常见组件
    Famous_TPL_41_benchmark_meta = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/evaluation/benchmark_meta/FTPL50.json"
    Famous_TPL_41_test_case_dir = "/Users/liuchengyue/Desktop/BinarySCA Platform/Data/Test_Cases/TPL_Test_Cases/Benchmarks/FTPL100/decompressed_deb"
    Famous_TPL_41_evluation_report_path = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/tmp/evaluation_reports/FTPL_41/evaluation_report.json"

    # 车载系统
    CAR_150_benchmark_meta = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/evaluation/benchmark_meta/CAR150.json"
    CAR_150_test_case_dir = "/Users/liuchengyue/Desktop/BinarySCA Platform/Data/Test_Cases/TPL_Test_Cases/BYD"
    CAR_150_evluation_report_path = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/tmp/evaluation_reports/CAR_150/evaluation_report.json"

    # Debian Binaries
    Debian_benchmark_meta = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/evaluation/benchmark_meta/DDE2000.json"
    Debian_test_case_dir = "/Users/liuchengyue/Desktop/BinarySCA Platform/Data/Test_Cases/TPL_Test_Cases/Benchmarks/DDE2000"
    Debian_evluation_report_path = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/tmp/evaluation_reports/DDE_2000/evaluation_report.json"

    benchmark_meta = Debian_benchmark_meta
    benchmark_tc_dir = Debian_test_case_dir
    evaluation_report_save_path = Debian_evluation_report_path

    # Example usage
    config = EvaluationConfig(
        benchmark_file=benchmark_meta,
        test_case_dir=benchmark_tc_dir,
        concurrency=10,
        slice_start=0,
        slice_end=100,
    )
    evaluator = Evaluator(config)
    evaluator.run_benchmark(analyze_context=False)
    evaluator.report.dump(evaluation_report_save_path)


    # report = EvaluationReport.load_from_file(evaluation_report_save_path)
    # result_check = evaluator.check_result(evaluator.benchmark, report.evaluation_results)


if __name__ == '__main__':
    main()
