import copy
import json
import os.path
import time
from typing import List

from loguru import logger

from app.interface import AnalysisResult, AnalysisData, TargetBinary
from app.services.tpl_detection.batch_detection_workflow import BatchDetectionWorkflow
from app.services.tpl_detection.detection_workflow import DetectionWorkflow
from evaluation.general_benchmarks.interface import EvaluationConfig, Benchmark, EvaluationReport, AnalysisResultCheck, \
    ResearchQuestionData, EffectivenessData, EfficiencyData, AblationData, CostData, BenchmarkSummary


class Evaluator:
    def __init__(self, config: EvaluationConfig):
        self.evaluation_config = config

        self.benchmark = Benchmark.load_from_json_file(config.benchmark_file)

        self.workflow = DetectionWorkflow(
            feature_matching_return_top_n=config.feature_matching_top_n,
            use_agent=config.use_agent,
        )
        self.batch_detection_workflow = BatchDetectionWorkflow(concurrency=config.concurrency,
                                                               feature_matching_return_top_n=config.feature_matching_top_n,
                                                               use_agent=config.use_agent,)

        self.evaluation_results = []

        self.report = EvaluationReport(
            evaluation_config=config,
            benchmark=self.benchmark,
        )
    def run_failed_cases(self, reference_report_path: str, *args, **kwargs):
        report = EvaluationReport.load_from_file(reference_report_path)
        failed_hashes = [check.binary_hash for check in report.evaluation_results_check if not check.perfect]

        self.benchmark = copy.deepcopy(self.benchmark)
        self.benchmark.test_cases = [tc for tc in self.benchmark.test_cases if tc.test_binary.sha256 in failed_hashes]
        self.benchmark.summary = BenchmarkSummary(
            test_case_num = len(self.benchmark.test_cases),
            covered_library_num = len(set(lib.name for tc in self.benchmark.test_cases for lib in tc.reused_libraries)),
        )
        print(len(self.benchmark.test_cases))
        self.run_benchmark(*args, **kwargs)

    def run_benchmark(self, analyze_context: bool = False):
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
        file_size_kb_dict = {test_case.test_binary.sha256: test_case.test_binary.file_size_kb for test_case in
                                self.benchmark.test_cases}
        results_check_lst = []
        for result in evaluation_results:
            ground_truth_reused_libraries = ground_truth_dict.get(result.binary_sha256, [])

            # 使用集合跟踪已匹配的GT库，避免重复匹配
            matched_gt_libraries = set()
            detected_gt_libraries = []

            tp_library_names = []
            redundant_tp_library_names = []
            fp_library_names = []

            # 检测到的库名称与Ground Truth进行对比
            for detected_lib in result.detected_libraries:
                # 跳过GCC
                if detected_lib.name.startswith('gcc'):
                    continue

                tp = False
                already_matched_before = False
                # 遍历所有GT库寻找匹配
                for i, gt_lib in enumerate(ground_truth_reused_libraries):

                    # 与Ground Truth 名称一致
                    if self._normalize_lib_name(detected_lib.name) == self._normalize_lib_name(gt_lib.name):
                        detected_gt_libraries.append(gt_lib)
                        tp = True


                    # 与Ground Truth 名称加前缀lib一致
                    elif self._normalize_lib_name(detected_lib.name) == self._normalize_lib_name('lib' + gt_lib.name) or self._normalize_lib_name('lib' + detected_lib.name) == self._normalize_lib_name(gt_lib.name):
                        detected_gt_libraries.append(gt_lib)
                        tp = True


                    # 与Ground Truth 名称的其他名称一致
                    elif self._normalize_lib_name(detected_lib.name) in [self._normalize_lib_name(lib_name) for lib_name
                                                                         in gt_lib.other_names]:
                        detected_gt_libraries.append(gt_lib)
                        tp = True

                    # 如果是TP, 中止循环，且记录已经匹配过的GT库
                    if tp == True:
                        if i in matched_gt_libraries:
                            already_matched_before = True
                        else:
                            matched_gt_libraries.add(i)
                        break

                if tp:
                    # 如果之前匹配过，则不重复添加
                    if not already_matched_before:
                        tp_library_names.append(detected_lib.name)
                    else:
                        redundant_tp_library_names.append(detected_lib.name)
                else:
                    fp_library_names.append(detected_lib.name)

            # 未检测到的Ground Truth库，均认为是FN
            undetected_gt_libraries = [gt_lib for i, gt_lib in enumerate(ground_truth_reused_libraries)
                                       if i not in matched_gt_libraries]

            fn_library_names = [lib.name for lib in undetected_gt_libraries]
            # 生成分析结果检查对象
            has_fn = len(fn_library_names) > 0  # 是否有漏报
            has_fp = len(fp_library_names) > 0
            analysis_result_check = AnalysisResultCheck(
                binary_name=result.binary_name,
                binary_path=result.binary_path,
                binary_hash=result.binary_sha256,
                binary_size_kb=file_size_kb_dict.get(result.binary_sha256, 0),  # 获取文件大小
                succeed= result.error_message is None,  # 是否成功
                err_msg=result.error_message,  # 错误信息
                ground_truth_lib_names=[lib.name for lib in ground_truth_reused_libraries],  # Ground Truth 库名称
                detected_lib_names=[lib.name for lib in result.detected_libraries],  # 检测到的库名称
                result_count=len(result.detected_libraries),
                tp_count=len(tp_library_names),  # 检测到的真正库数量
                redundant_tp_count=len(redundant_tp_library_names), # 正确但重复的结果数量
                fp_count=len(fp_library_names),  # 检测到的误报库数量
                fn_count=len(fn_library_names),  # 漏报的库数量
                perfect= not(has_fn or has_fp),  # 是否完美
                hs_fn=has_fn,  # 是否有漏报
                hs_fp=has_fp,  # 是否有误报
                hs_rd_tp= len(redundant_tp_library_names) > 0,  # 是否有重复的正确结果
                has_multi_results= len(result.detected_libraries) > 1,  # 是否有多个检测结果
                no_results=len(result.detected_libraries)==0,
                tp_lib_names=tp_library_names,  # 真正检测到的库名称
                redundant_tp_lib_names=redundant_tp_library_names,  # 正确但重复的结果。
                fp_lib_names=fp_library_names,  # 误报的库名称
                fn_lib_names=fn_library_names,  # 漏报的库名称
            )
            results_check_lst.append(analysis_result_check)
        return results_check_lst

    def analyze_result(self,
                    evaluation_results: List[AnalysisResult],
                    evaluation_duration: float,
                    input_token_price_per_1M: float=0.8,  # 每百万输入token的价格, OpenAI GPT-4.1 mini
                    cached_input_token_price_per_1M: float=0.2,  # 每百万输入token的价格, OpenAI GPT-4.1  mini
                    output_token_price_per_1M: float=3.2,  # 每百万输出token的价格, OpenAI GPT-4.1  mini
                    ignore_failed_cases: bool = False,  # 是否忽略失败的测试用例
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
        if ignore_failed_cases:
            evaluation_results = [result for result in evaluation_results if result.error_message is None]

        results_check_lst = self.check_result(evaluation_results)

        # RQ 1，效率
        print(f"计算RQ 1 效果性...")
        effectiveness = self._cal_effectiveness(results_check_lst)
        print(f"RQ 1 效果性计算完成: {effectiveness}, 计算不同编译配置的效果性...")
        gcc_x86_effectiveness, gcc_arm_effectiveness, clang_x86_64_effectiveness = self._cal_effectiveness_group_by_compile_config(results_check_lst)
        print(f"RQ 1 计算不同文件大小的效果")
        size_lt_1000_effectiveness, size_lt_500_effectiveness, size_lt_100_effectiveness = self._cal_effectiveness_group_by_file_size(results_check_lst)

        # RQ 2 消融实验
        print(f"计算RQ 2 效果性消融实验...")
        effectiveness_ablation_study = self._cal_ablation_data(evaluation_results)

        # RQ 3 效率和成本
        print(f"计算RQ 3 效率和成本...")
        efficiency = self._cal_efficiency(evaluation_results,
                                         evaluation_duration,
                                         input_token_price_per_1M,
                                         output_token_price_per_1M)
        cost = self._cal_cost(
                evaluation_results,
                input_token_price_per_1M,
            cached_input_token_price_per_1M,
                output_token_price_per_1M
        )

        rq_data = ResearchQuestionData(
            effectiveness=effectiveness,
            gcc_x86_effectiveness=gcc_x86_effectiveness,
            gcc_arm_effectiveness=gcc_arm_effectiveness,
            clang_x86_64_effectiveness=clang_x86_64_effectiveness,
            size_lt_1000kb_effectiveness=size_lt_1000_effectiveness,
            size_lt_500kb_effectiveness=size_lt_500_effectiveness,
            size_lt_100kb_effectiveness=size_lt_100_effectiveness,
            effectiveness_ablation_study=effectiveness_ablation_study,
            efficiency=efficiency,
            cost=cost,
        )
        print(f"全部研究问题数据计算完成: {rq_data}")
        return results_check_lst, rq_data

    def _correct_evaluation_results(self, evaluation_results, benchmark_test_cases):
        # 1. 建立benchmark的索引（用sha256或relative_path）
        benchmark_dict = {tc.test_binary.sha256: tc for tc in benchmark_test_cases}

        # 2. 删除：过滤evaluation_results，只保留benchmark中存在的测试用例
        corrected_results = []
        existing_sha256s = set()

        for result in evaluation_results:
            if result.binary_sha256 in benchmark_dict:
                corrected_results.append(result)
                existing_sha256s.add(result.binary_sha256)

        # 3. 补充：为benchmark中存在但evaluation_results中缺失的测试用例创建失败结果
        for sha256, test_case in benchmark_dict.items():
            if sha256 not in existing_sha256s:
                # 创建一个失败的AnalysisResult
                failed_result = AnalysisResult(
                    binary_name=test_case.test_binary.original_name,
                    binary_path=test_case.test_binary.relative_path,
                    binary_sha256=sha256,
                    analysis_data=AnalysisData(
                        target_binary=TargetBinary(
                            binary_name=test_case.test_binary.original_name,
                            relative_path=test_case.test_binary.relative_path,
                            hash_sha256=sha256,
                            file_size_kb=test_case.test_binary.file_size_kb,
                        )
                    ),
                    succeed=False,
                    error_message="Auto added! Analysis failed: No result found for this test case.",
                )
                corrected_results.append(failed_result)

        return corrected_results

    def reanalyze_report(self, evaluation_report_save_path:str,
                         new_report_save_path:str=None,
                         ignore_failed_cases:bool=False):
        if not new_report_save_path:
            new_report_save_path = evaluation_report_save_path[:-5] + '_reanalyzed.json'
        # load
        report = EvaluationReport.load_from_file(evaluation_report_save_path)

        # 和benchmark对齐测试用例
        corrected_results = self._correct_evaluation_results(
            report.evaluation_results,
            self.benchmark.test_cases
        )

        # reanalyze
        evaluation_duration = report.research_question_data.efficiency.total_actual_duration if report.research_question_data else 0.0
        results_check_lst, rq_data = self.analyze_result(
            evaluation_results=corrected_results,
            evaluation_duration=evaluation_duration,
            input_token_price_per_1M=self.evaluation_config.input_token_price_per_1M,  # 每百万输入token的价格, OpenAI GPT-4.1
            output_token_price_per_1M=self.evaluation_config.output_token_price_per_1M,
            ignore_failed_cases=ignore_failed_cases,
        )

        # update
        report.evaluation_results = corrected_results # 更新检测结果
        report.evaluation_results_check = results_check_lst # 更新检查结果
        report.research_question_data = rq_data # 更新RQ数据

        # 更新统计数据
        report.succeed_count = sum(1 for result in corrected_results if result.error_message is None)
        report.failed_count = sum(1 for result in corrected_results if result.error_message is not None)

        # save
        report.dump(new_report_save_path)
        return report

    def analyze_baseline_result(self, evaluation_result_path, result_checks_save_path:str = None):
        if not result_checks_save_path:
            result_checks_save_path = evaluation_result_path[:-5] + '_checks.json'

        # 加载结果
        with open(evaluation_result_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        evaluation_results = [AnalysisResult.init_from_dict(result) for result in data]

        # 检查正确性
        result_check_lst = self.check_result(evaluation_results)

        with open(result_checks_save_path, "w", encoding="utf-8") as f:
            data = [check.customer_serialize() for check in result_check_lst]
            json.dump(data, f, indent=4, ensure_ascii=False)

        # 计算评估指标
        effectiveness = self._cal_effectiveness(result_check_lst)

        # 预览评估指标
        print(effectiveness)

    # 正规化名称
    def _normalize_lib_name(self, lib_name: str):
        return lib_name.lower().strip()

    def _cal_effectiveness(self, result_check_lst):
        # TP, FP, FN
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

    def _cal_effectiveness_group_by_compile_config(self,result_check_lst):
        gcc_x86 = []
        gcc_arm = []
        clang_x86_64 = []
        for check in result_check_lst:
            if "x86_64-gcc" in check.binary_path:
                gcc_x86.append(check)
            elif "arm_64-gcc" in check.binary_path:
                gcc_arm.append(check)
            elif "x86_64-clang" in check.binary_path:
                clang_x86_64.append(check)
            else:
                logger.warning(f"Unknown compile config for binary {check.binary_name}, path: {check.binary_path}")
                continue

        gcc_x86_effectiveness = self._cal_effectiveness(gcc_x86)
        gcc_arm_effectiveness = self._cal_effectiveness(gcc_arm)
        clang_x86_64_effectiveness = self._cal_effectiveness(clang_x86_64)

        return gcc_x86_effectiveness, gcc_arm_effectiveness, clang_x86_64_effectiveness

    def _cal_effectiveness_group_by_file_size(self,result_check_lst):
        size_lt_1000= []  # 小于1MB
        size_lt_500 = []
        size_lt_100 = []
        for check in result_check_lst:
            if check.binary_size_kb < 1000:  # 小于1MB
                size_lt_1000.append(check)
            if check.binary_size_kb < 500:
                size_lt_500.append(check)
            if check.binary_size_kb < 100:
                size_lt_100.append(check)

        size_lt_1000_effectiveness = self._cal_effectiveness(size_lt_1000)
        size_lt_500_effectiveness = self._cal_effectiveness(size_lt_500)
        size_lt_100_effectiveness = self._cal_effectiveness(size_lt_100)

        return size_lt_1000_effectiveness, size_lt_500_effectiveness, size_lt_100_effectiveness

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

        # 消融掉Agent 全部分析, 且特征匹配只取top_4
        evaluation_results_wo_agent_analysis = copy.deepcopy(evaluation_results)
        for evaluation_result in evaluation_results_wo_agent_analysis:
            # 只保留检测到的库
            evaluation_result.detected_libraries = [tpl for tpl in evaluation_result.analysis_data.all_candidate_libraries
                                                    if self.workflow.feature_matching_detector.method_name in tpl.identify_methods][:4]

        results_check_lst = self.check_result(evaluation_results_wo_agent_analysis)
        effectiveness_wo_agent_analysis_top_4 = self._cal_effectiveness(results_check_lst)

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
            wo_agent_analysis_top_4=effectiveness_wo_agent_analysis_top_4,
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
        # 理论时间开销
        total_theoretical_duration = sum(result.analysis_data.durations.get('total', 0) for result in evaluation_results)  # 总检测时间
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

        # 更正理论总时间，有些中间出错的，导致总时间不等于各步骤时间之和
        total = 0.0
        for step, duration in step_total_theoretical_duration.items():
            if step != 'total' and not step.startswith('_'):
                total += duration
        step_total_theoretical_duration['total'] = total_theoretical_duration = total

        # 计算比例
        step_total_theoretical_duration_proportions = {}
        for step, duration in step_total_theoretical_duration.items():
            step_total_theoretical_duration_proportions[step] = round((duration / total_theoretical_duration) * 100, 2) if total_theoretical_duration > 0 else 0.0

        # 计算LLM时间
        all_llm_duration = 0.0
        for result in evaluation_results:
            for detector_name, cost_dict in result.analysis_data.costs.items():
                if 'time' in cost_dict:
                    llm_duration = sum(cost_dict.get('time', []))
                    all_llm_duration += llm_duration

        rq_3_data = EfficiencyData(
            total_file_size_kb=total_file_size,
            average_file_size_kb=average_file_size,
            total_theoretical_duration=total_theoretical_duration,
            average_theoretical_duration=average_theoretical_duration,
            total_actual_duration=total_actual_duration,
            average_actual_duration=average_actual_duration,
            step_total_theoretical_duration=step_total_theoretical_duration,
            duration_breakdown=step_total_theoretical_duration_proportions,
            llm_duration=all_llm_duration
        )
        return rq_3_data

    def _cal_cost(self,
                        evaluation_results,
                        input_token_price_per_1M,
                  cached_input_token_price_per_1M,
                        output_token_price_per_1M):
        # ----- 成本 -----
        total_uncached_input_tokens = 0
        total_cached_input_tokens = 0
        total_input_tokens = 0
        output_token_count = 0
        total_cost = 0.0
        for result in evaluation_results:
            for agent_name, cost_dict in result.analysis_data.costs.items():
                # total input token
                input_tokens = sum(cost_dict.get('input_tokens', []))
                total_input_tokens += input_tokens

                # cached token
                cached_tokens = sum(cost_dict.get('cached_tokens', []))
                total_cached_input_tokens += cached_tokens

                # uncached token
                uncached_tokens = input_tokens - cached_tokens
                total_uncached_input_tokens += uncached_tokens

                # output token
                output_tokens = sum(cost_dict.get('output_tokens', []))
                output_token_count += output_tokens

        # cost
        uncached_input_cost = total_uncached_input_tokens /1_000_000 * input_token_price_per_1M  # 未缓存输入token成本
        cached_input_cost = total_cached_input_tokens /1_000_000 * cached_input_token_price_per_1M

        input_cost = uncached_input_cost + cached_input_cost
        output_cost = (output_token_count / 1_000_000) * output_token_price_per_1M
        total_cost += input_cost + output_cost

        average_cost = total_cost / len(evaluation_results) if evaluation_results else 0.0  # 平均成本

        cost_data = CostData(
            uncached_input_token_count=total_uncached_input_tokens,
            cached_input_token_count=total_cached_input_tokens,
            total_input_token_count=total_input_tokens,
            output_token_count=output_token_count,
            total_token_count=total_input_tokens + output_token_count,

            uncached_input_cost=uncached_input_cost,
            cached_input_cost=cached_input_cost,
            total_input_cost=input_cost,
            output_cost=output_cost,
            total_cost=total_cost,
            average_cost=average_cost
        )

        return cost_data

