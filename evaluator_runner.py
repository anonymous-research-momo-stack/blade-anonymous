from evaluation.general_benchmarks.evaluator import Evaluator
from evaluation.general_benchmarks.feture_matching_analysis import plot_feature_matching_top_n_effectiveness_figure, \
    analyze_feature_matching_top_n_effectiveness, \
    analyze_feature_matching_failures, print_failure_analysis_report
from evaluation.general_benchmarks.interface import EvaluationConfig
from environs import Env

env = Env()
env.read_env()


def reanalyze_all_result():
    # Conan Binaries
    Conan_benchmark_meta = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/evaluation/general_benchmarks/benchmark_meta/conan_library_benchmark_20250830_1142.json"
    Conan_test_case_dir = "/Users/liuchengyue/Desktop/BinarySCA Platform/Data/Test_Cases/TPL_Test_Cases/conan_test_cases"


    benchmark_meta = Conan_benchmark_meta
    benchmark_tc_dir = Conan_test_case_dir


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
    # =============== 重新对比结果与groundtruth ==============
    print(f"our gpt 5 mini")
    result_path = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/tmp/evaluation_reports/Conan/ours/gpt_5_mini/evaluation_report.json"
    report = evaluator.reanalyze_report(result_path, ignore_failed_cases=False)

    print(f"our gpt 5 nano")
    result_path = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/tmp/evaluation_reports/Conan/ours/gpt_5_nano/evaluation_report.json"
    report = evaluator.reanalyze_report(result_path, ignore_failed_cases=False)

    print(f"our gpt 4.1 mini")
    result_path = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/tmp/evaluation_reports/Conan/ours/gpt_4_1_mini/ours_105_0806/evaluation_report.json"
    report = evaluator.reanalyze_report(result_path, ignore_failed_cases=False)

    print(f"Blackduck")
    result_path = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/tmp/evaluation_reports/Conan/blackduck/result_converted.json"
    report = evaluator.reanalyze_report(result_path, ignore_failed_cases=False)


    print(f"Scantist")
    result_path = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/tmp/evaluation_reports/Conan/scantist/291-75403-xd70-无agent-扫描报告-2025-08-06T09_36_22+08_00/result_converted.json"
    report = evaluator.reanalyze_report(result_path, ignore_failed_cases=False)
    #
    print(f"BAT")
    result_path = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/tmp/evaluation_reports/Conan/bat/raw_result_converted.json"
    report = evaluator.reanalyze_report(result_path, ignore_failed_cases=False)

    print(f"OssPolice")
    result_path = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/tmp/evaluation_reports/Conan/osspolice/raw_result_converted.json"
    report = evaluator.reanalyze_report(result_path, ignore_failed_cases=False)

    print(f"Binary AI")
    result_path = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/tmp/evaluation_reports/Conan/binary_ai/evaluation_report_2025-07-30-12-54-29_converted.json"
    report = evaluator.reanalyze_report(result_path, ignore_failed_cases=False)

    print(f"B2SFinder")
    result_path = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/tmp/evaluation_reports/Conan/b2sfinder/result_converted.json"
    report = evaluator.reanalyze_report(result_path, ignore_failed_cases=False)



def run_feature_matching_only():
    # 分析输入Conan Binaries
    Conan_benchmark_meta = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/evaluation/general_benchmarks/benchmark_meta/conan_library_benchmark.json"
    Conan_test_case_dir = "/Users/liuchengyue/Desktop/BinarySCA Platform/Data/Test_Cases/TPL_Test_Cases/conan_test_cases"
    Conan_evluation_report_path = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/tmp/evaluation_reports/Conan/feture_matching/evaluation_report.json"

    # 评估输入
    benchmark_meta = Conan_benchmark_meta
    benchmark_tc_dir = Conan_test_case_dir

    # 评估结果
    evaluation_report_save_path = Conan_evluation_report_path

    # 评估结果的分析结果
    top_n_effectiveness_analysis_result_path = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/tmp/evaluation_reports/Conan/feture_matching/effectiveness_analysis_result.json"

    # 评估配置
    top_n = 30
    config = EvaluationConfig(
        benchmark_file=benchmark_meta,
        test_case_dir=benchmark_tc_dir,
        feature_matching_top_n=top_n,
        use_agent=False,
        concurrency=10,
        slice_start=0,
        # slice_end=100,
    )

    # 初始化评估器
    evaluator = Evaluator(config)

    # 评估
    # evaluator.run_benchmark(analyze_context=False)
    # evaluator.report.dump(evaluation_report_save_path)

    # 分析结果
    # RQ 1 topn 和 效果的相关性
    analyze_feature_matching_top_n_effectiveness(evaluator, evaluation_report_save_path, top_n_effectiveness_analysis_result_path, top_n=top_n)

    # top_n_effectiveness 绘图
    plot_feature_matching_top_n_effectiveness_figure(top_n_effectiveness_analysis_result_path)

    # RQ 2 漏报的原因分类
    # 执行分析
    report = analyze_feature_matching_failures(
        evaluator=evaluator,
        benchmark_path=benchmark_meta,
        evaluation_result_path=evaluation_report_save_path,
        top_n=top_n,
        small_file_threshold_kb=100
    )

    # 打印报告
    print_failure_analysis_report(report)

def run_failed_case_only():

    # Conan Binaries
    Conan_benchmark_meta_updated = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/evaluation/general_benchmarks/benchmark_meta/conan_library_benchmark_20250830_1142.json"
    Conan_test_case_dir = "/Users/liuchengyue/Desktop/BinarySCA Platform/Data/Test_Cases/TPL_Test_Cases/conan_test_cases"

    Conan_evluation_report_path = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/tmp/evaluation_reports/Conan/ours/gpt_5_mini/evaluation_report_reanalyzed.json"
    Conan_only_failed_cases_evluation_report_path = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/tmp/evaluation_reports/Conan/ours/gpt_5_mini/only_failed_cases_evaluation_report.json"


    benchmark_meta = Conan_benchmark_meta_updated
    benchmark_tc_dir = Conan_test_case_dir
    evaluation_report_save_path = Conan_only_failed_cases_evluation_report_path

    # 评估配置
    config = EvaluationConfig(
        benchmark_file=benchmark_meta,
        test_case_dir=benchmark_tc_dir,
        feature_matching_top_n=5,
        # use_agent=False,
        concurrency=20,
        slice_start=0,
        # slice_end=0,
        input_token_price_per_1M=0.4,
        output_token_price_per_1M=1.6,
    )

    # 初始化评估器
    evaluator = Evaluator(config)

    # 评估
    evaluator.run_failed_cases(reference_report_path=Conan_evluation_report_path)
    evaluator.report.dump(evaluation_report_save_path)

    # 重新分析结果
    report = evaluator.reanalyze_report(evaluation_report_save_path,
                                        ignore_failed_cases=False)


def main():
    # benchmark meta
    evaluation_dir = env.str("EVALUATION_DIR_PATH")
    evaluation_output_dir = env.str("EVALUATION_OUTPUT_DIR_PATH")
    conan_test_case_dir = env.str("CONAN_BENCHMARK_TEST_CASE_DIR")

    conan_benchmark_meta_file = f"{evaluation_dir}/general_benchmarks/benchmark_meta/conan_library_benchmark.json"

    evaluation_result_file = f"{evaluation_output_dir}/Conan/ours/gpt_5_mini/evaluation_report.json"

    # evaluation config
    config = EvaluationConfig(
        benchmark_file=conan_benchmark_meta_file,
        test_case_dir=conan_test_case_dir,
        feature_matching_top_n=5,
        # use_agent=False,
        concurrency=30,
        slice_start=0,
        # slice_end=10,
        input_token_price_per_1M=0,
        output_token_price_per_1M=0,
        # input_token_price_per_1M=0.4,
        # output_token_price_per_1M=1.6,
    )

    # 初始化评估器
    evaluator = Evaluator(config)

    # 评估
    evaluator.run_benchmark(analyze_context=False)
    evaluator.report.dump(evaluation_result_file)

    # 重新分析结果
    report = evaluator.reanalyze_report(evaluation_result_file,
                                        ignore_failed_cases=False)

    # 可视化分析结果
    # visualization_html = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/tmp/visualization.html"
    # generate_analysis_report(report,
    #                         visualization_html
    #                          )

if __name__ == '__main__':
    # main()
    # run_failed_case_only()
    reanalyze_all_result()
    # run_feature_matching_only()


    """
    常用命令：
    查看后台进程，杀死后台进程
        ps aux | grep pipeline_runner.py
        pkill -f pipeline_runner.py & pkill -f rsync & rm -rf /dev/shm
        pkill -f pipeline_runner.py
        
        pkill -9 -f git -u wenze
    清空临时目录
        rm -rf /dev/shm
    
    激活conda环境并运行
        conda activate sca
    
    后台运行
        nohup python3 evaluator_runner.py > evaluation.log 2>&1 &
    
    跟踪查看日志
        tail -f evaluation.log
    """
