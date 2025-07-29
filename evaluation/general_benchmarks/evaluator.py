import copy
import os.path
import subprocess
import time
from typing import List

from loguru import logger
from sqlalchemy.testing.util import total_size

from app.interface import AnalysisResult, AnalysisData
from app.tpl_detection.batch_detection_workflow import BatchDetectionWorkflow
from app.tpl_detection.detection_workflow import DetectionWorkflow
from evaluation.general_benchmarks.interface import EvaluationConfig, Benchmark, EvaluationReport, AnalysisResultCheck, \
    ResearchQuestionData, EffectivenessData, EfficiencyData, AblationData, CostData
from evaluation.general_benchmarks.visualization import generate_analysis_report


class Evaluator:
    def __init__(self, config: EvaluationConfig):
        self.evaluation_config = config

        self.benchmark = Benchmark.load_from_json_file(config.benchmark_file)

        self.workflow = DetectionWorkflow(
            feature_matching_return_top_n=5,
        )
        self.batch_detection_workflow = BatchDetectionWorkflow(concurrency=config.concurrency,
                                                               feature_matching_return_top_n=5)

        self.evaluation_results = []

        self.report = EvaluationReport(
            evaluation_config=config,
            benchmark=self.benchmark,
        )

    def run_benchmark(self, analyze_context: bool = True):
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
            self.report.software_context = context

        logger.info(f"开始运行测试用例")
        results = self.batch_detection_workflow.run_batch(absolute_paths, software_context=context)
        total_time = time.perf_counter() - start_time
        self.report.finished_at = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(start_time + total_time))
        self.report.evaluation_results = results

        # 生成RQ数据
        logger.info("分析测试结果")
        results_check_lst, rq_data = self.analyze_result(
            evaluation_results=results,
            evaluation_duration=total_time,
            input_token_price_per_1M=self.evaluation_config.input_token_price_per_1M,  # 每百万输入token的价格, OpenAI GPT-4.1
            output_token_price_per_1M=self.evaluation_config.output_token_price_per_1M,
        )
        self.report.evaluation_results_check = results_check_lst
        self.report.research_question_data = rq_data
        logger.info(f"All Done, total time: {total_time:.2f} seconds")

    def check_result(self, evaluation_results: List[AnalysisResult]) -> List[AnalysisResultCheck]:
        """
        检查结果，与Ground Truth进行对比
        :return:
        """
        ground_truth_dict = {test_case.test_binary.sha256: test_case.reused_libraries for test_case in
                             self.benchmark.test_cases}
        results_check_lst = []
        for result in evaluation_results:
            ground_truth_reused_libraries = ground_truth_dict.get(result.binary_sha256, [])

            undetected_gt_libraries = copy.deepcopy(ground_truth_reused_libraries)
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
                binary_name=result.binary_name,
                binary_path=result.binary_path,
                binary_hash=result.binary_sha256,
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

    def reanalyze_report(self, evaluation_report_save_path:str):
        # load
        report = EvaluationReport.load_from_file(evaluation_report_save_path)

        # reanalyze
        results_check_lst, rq_data = self.analyze_result(
            evaluation_results=report.evaluation_results,
            evaluation_duration=report.research_question_data.efficiency.total_actual_duration,
            input_token_price_per_1M=self.evaluation_config.input_token_price_per_1M,  # 每百万输入token的价格, OpenAI GPT-4.1
            output_token_price_per_1M=self.evaluation_config.output_token_price_per_1M,
        )

        # update
        report.evaluation_results_check = results_check_lst
        report.research_question_data = rq_data

        # save
        report.dump(evaluation_report_save_path)
        return report

    def analyze_result(self,
                    evaluation_results: List[AnalysisResult],
                    evaluation_duration: float,
                    input_token_price_per_1M: float=2,  # 每百万输入token的价格, OpenAI GPT-4.1
                    output_token_price_per_1M: float=8,  # 每百万输出token的价格, OpenAI GPT-4.1
                    ) -> tuple[list[AnalysisResultCheck], ResearchQuestionData]:
        """
        生成报告
        1. 效果
        2. 效率
        3. 成本

        :return:
        """
        # 检查结果
        logger.info("检查结果...")
        results_check_lst = self.check_result(evaluation_results)

        # RQ 1，效率
        effectiveness = self._cal_effectiveness(results_check_lst)

        # RQ 2 消融实验
        effectiveness_ablation_study = self._cal_ablation_data(evaluation_results)

        # RQ 3 效率和成本
        efficiency = self._cal_efficiency(evaluation_results,
                                         evaluation_duration,
                                         input_token_price_per_1M,
                                         output_token_price_per_1M)
        cost = self._cal_cost(
                evaluation_results,
                input_token_price_per_1M,
                output_token_price_per_1M
        )

        rq_data = ResearchQuestionData(
            effectiveness=effectiveness,
            effectiveness_ablation_study=effectiveness_ablation_study,
            efficiency=efficiency,
            cost=cost,
        )

        return results_check_lst, rq_data

    def _cal_effectiveness(self, result_check_lst):
        # TP, FP, FN,
        tp_count = sum(len(check.tp_lib_names) for check in result_check_lst)
        fp_count = sum(len(check.fp_lib_names) for check in result_check_lst)
        fn_count = sum(len(check.fn_lib_names) for check in result_check_lst)
        # Precision, Recall, F1-Score (百分比，保留两位小数)
        precision = round(tp_count / (tp_count + fp_count) * 100, 2) if (tp_count + fp_count) > 0 else 0.0
        recall = round(tp_count / (tp_count + fn_count) * 100, 2) if (tp_count + fn_count) > 0 else 0.0
        f1_score = round(2 * (precision * recall) / (precision + recall), 2) if (precision + recall) > 0 else 0.0
        rq_1_data = EffectivenessData(
            tp_count=tp_count,
            fp_count=fp_count,
            fn_count=fn_count,
            precision=precision,
            recall=recall,
            f1_score=f1_score
        )
        return rq_1_data

    def _cal_ablation_data(self, evaluation_results):
        # 消融掉Agent 全部分析, 特征匹配取top_n
        evaluation_results_wo_agent_analysis = copy.deepcopy(evaluation_results)
        for evaluation_result in evaluation_results_wo_agent_analysis:
            # 只保留检测到的库
            evaluation_result.detected_libraries = [tpl for tpl in evaluation_result.analysis_data.all_candidate_libraries
                                                    if self.workflow.feature_matching_detector.method_name in tpl.identify_methods]

        results_check_lst = self.check_result(evaluation_results_wo_agent_analysis)
        effectiveness_wo_agent_analysis = self._cal_effectiveness(results_check_lst)

        # 消融掉Agent 全部分析, 且特征匹配只取top_1
        evaluation_results_wo_agent_analysis = copy.deepcopy(evaluation_results)
        for evaluation_result in evaluation_results_wo_agent_analysis:
            # 只保留检测到的库
            evaluation_result.detected_libraries = [tpl for tpl in evaluation_result.analysis_data.all_candidate_libraries
                                                    if self.workflow.feature_matching_detector.method_name in tpl.identify_methods][:1]

        results_check_lst = self.check_result(evaluation_results_wo_agent_analysis)
        effectiveness_wo_agent_analysis_top_1 = self._cal_effectiveness(results_check_lst)

        # 消融掉Agent 全部分析, 且特征匹配只取top_2
        evaluation_results_wo_agent_analysis = copy.deepcopy(evaluation_results)
        for evaluation_result in evaluation_results_wo_agent_analysis:
            # 只保留检测到的库
            evaluation_result.detected_libraries = [tpl for tpl in evaluation_result.analysis_data.all_candidate_libraries
                                                    if self.workflow.feature_matching_detector.method_name in tpl.identify_methods][:2]

        results_check_lst = self.check_result(evaluation_results_wo_agent_analysis)
        effectiveness_wo_agent_analysis_top_2 = self._cal_effectiveness(results_check_lst)

        # 消融掉Agent 全部分析, 且特征匹配只取top_3
        evaluation_results_wo_agent_analysis = copy.deepcopy(evaluation_results)
        for evaluation_result in evaluation_results_wo_agent_analysis:
            # 只保留检测到的库
            evaluation_result.detected_libraries = [tpl for tpl in evaluation_result.analysis_data.all_candidate_libraries
                                                    if self.workflow.feature_matching_detector.method_name in tpl.identify_methods][:3]

        results_check_lst = self.check_result(evaluation_results_wo_agent_analysis)
        effectiveness_wo_agent_analysis_top_3 = self._cal_effectiveness(results_check_lst)

        # 消融实验1： 消融 Agent TPL分析
        # 计算消融后的结果
        evaluation_results_wo_agent_tpl_analysis = copy.deepcopy(evaluation_results)
        for evaluation_result in evaluation_results_wo_agent_tpl_analysis:
            # 过滤掉 Agent TPL 分析方法检测到的库，即：有特征匹配的就可以。
            evaluation_result.detected_libraries = [tpl for tpl in evaluation_result.detected_libraries
                                           if self.workflow.feature_matching_detector.method_name in tpl.identify_methods]
        # 重新检查
        results_check_lst = self.check_result(evaluation_results_wo_agent_tpl_analysis)

        # 重新计算effectiveness
        effectiveness_wo_agent_tpl_analysis = self._cal_effectiveness(results_check_lst)

        # 消融实验2： 消融验证步骤
        # 消融验证步骤 1
        # 计算消融后的结果
        evaluation_results_wo_validation_step_1 = copy.deepcopy(evaluation_results)
        for evaluation_result in evaluation_results_wo_validation_step_1:
            # 不冗余即可
            evaluation_result.detected_libraries = [tpl for tpl in evaluation_result.analysis_data.all_candidate_libraries if not tpl.is_redundant]

        results_check_lst = self.check_result(evaluation_results_wo_validation_step_1)

        effectiveness_wo_validation_step_1 = self._cal_effectiveness(results_check_lst)

        # 消融验证步骤 2
        evaluation_results_wo_validation_step_2 = copy.deepcopy(evaluation_results)
        for evaluation_result in evaluation_results_wo_validation_step_2:
            # 合理即可
            evaluation_result.detected_libraries =  [tpl for tpl in evaluation_result.analysis_data.all_candidate_libraries if tpl.is_reasonable]

        results_check_lst = self.check_result(evaluation_results_wo_validation_step_2)

        effectiveness_wo_validation_step_2 = self._cal_effectiveness(results_check_lst)


        # 消融Agent 全部验证步骤
        evaluation_results_wo_validation_step_1_and_2 = copy.deepcopy(evaluation_results)
        for evaluation_result in evaluation_results_wo_validation_step_1_and_2:
            # 不冗余且合理即可
            evaluation_result.detected_libraries = evaluation_result.analysis_data.all_candidate_libraries

        results_check_lst = self.check_result(evaluation_results_wo_validation_step_1_and_2)
        effectiveness_wo_validation_step_1_and_2 = self._cal_effectiveness(results_check_lst)

        return AblationData(
            wo_agent_analysis=effectiveness_wo_agent_analysis,
            wo_agent_analysis_top_1=effectiveness_wo_agent_analysis_top_1,
            wo_agent_analysis_top_2=effectiveness_wo_agent_analysis_top_2,
            wo_agent_analysis_top_3=effectiveness_wo_agent_analysis_top_3,
            wo_agent_tpl_analysis=effectiveness_wo_agent_tpl_analysis,
            wo_validation_step_1=effectiveness_wo_validation_step_1,
            wo_validation_step_2=effectiveness_wo_validation_step_2,
            wo_validation_step_1_and_2=effectiveness_wo_validation_step_1_and_2,
        )

    def _cal_efficiency(self,
                        evaluation_results,
                        evaluation_duration,
                        input_token_price_per_1M,
                        output_token_price_per_1M):
        # ----- 文件大小 -----
        total_file_size = sum(result.analysis_data.target_binary.file_size_kb for result in evaluation_results)  # 总文件大小
        average_file_size = total_file_size / len(evaluation_results) if evaluation_results else 0.0  # 平均文件大小

        # ----- 时间开销 -----
        # 理论实践开销
        total_theoretical_duration = sum(result.analysis_data.durations['total'] for result in evaluation_results)  # 总检测时间
        average_theoretical_duration = total_theoretical_duration / len(evaluation_results) if evaluation_results else 0.0  # 平均检测时间

        # 实际检测时间
        total_actual_duration = evaluation_duration  # 实际总检测时间
        average_actual_duration = evaluation_duration / len(evaluation_results) if evaluation_results else 0.0  # 实际平均检测时间

        # 每个步骤的时间的 break down
        step_total_theoretical_duration = {}
        for result in evaluation_results:
            for step, duration in result.analysis_data.durations.items():
                if step not in step_total_theoretical_duration:
                    step_total_theoretical_duration[step] = 0.0
                step_total_theoretical_duration[step] += duration

        # 计算比例
        step_total_theoretical_duration_proportions = {}
        for step, duration in step_total_theoretical_duration.items():
            step_total_theoretical_duration_proportions[step] = round((duration / total_theoretical_duration) * 100, 2) if total_theoretical_duration > 0 else 0.0

        # 合并break down数据
        duration_breakdown = {}
        for step, (step_total_theoretical_duration, step_proportion) in zip(step_total_theoretical_duration.keys(), step_total_theoretical_duration_proportions.items()):
            duration_breakdown[step] = (step_total_theoretical_duration, step_proportion)


        rq_3_data = EfficiencyData(
            total_file_size_kb=total_file_size,
            average_file_size_kb=average_file_size,
            total_theoretical_duration=total_theoretical_duration,
            average_theoretical_duration=average_theoretical_duration,
            total_actual_duration=total_actual_duration,
            average_actual_duration=average_actual_duration,
            duration_breakdown=duration_breakdown,
        )
        return rq_3_data

    def _cal_cost(self,
                        evaluation_results,
                        input_token_price_per_1M,
                        output_token_price_per_1M):
        # ----- 成本 -----
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

        cost_data = CostData(
            input_token_count=input_token_count,
            output_token_count=output_token_count,
            total_token_count=input_token_count+output_token_count,
            total_cost=total_cost,
            average_cost=average_cost
        )

        return cost_data


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

    # Conan Binaries
    Conan_benchmark_meta = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/evaluation/general_benchmarks/benchmark_meta/conan_library_benchmark.json"
    Conan_test_case_dir = "/Users/liuchengyue/Desktop/BinarySCA Platform/Data/Test_Cases/TPL_Test_Cases/conan_test_cases"
    Conan_evluation_report_path = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/tmp/evaluation_reports/Conan/evaluation_report.json"


    benchmark_meta = Conan_benchmark_meta
    benchmark_tc_dir = Conan_test_case_dir
    evaluation_report_save_path = Conan_evluation_report_path

    # 评估配置
    config = EvaluationConfig(
        benchmark_file=benchmark_meta,
        test_case_dir=benchmark_tc_dir,
        concurrency=30,
        slice_start=0,
        slice_end=30,
    )

    # 初始化评估器
    evaluator = Evaluator(config)

    # 评估
    evaluator.run_benchmark(analyze_context=False)
    evaluator.report.dump(evaluation_report_save_path)

    # 重新分析结果
    report = evaluator.reanalyze_report(evaluation_report_save_path)

    # 可视化分析结果
    visualization_html = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/tmp/visualization.html"
    generate_analysis_report(report,
                            visualization_html
                             )

if __name__ == '__main__':
    main()
