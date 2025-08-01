from evaluation.general_benchmarks.evaluator import Evaluator
from evaluation.general_benchmarks.feture_matching_analysis import plot_feature_matching_top_n_effectiveness_figure, \
    analyze_feature_matching_top_n_effectiveness, classify_feature_matching_cases_having_fn
from evaluation.general_benchmarks.interface import EvaluationConfig
from evaluation.general_benchmarks.visualization import generate_analysis_report


def analyze_baseline():
    # Conan Binaries
    Conan_benchmark_meta = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/evaluation/general_benchmarks/benchmark_meta/conan_library_benchmark.json"
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
    # =============== baselines ==============
    # 经过格式转换的结果
    # ========================================
    # binary ai
    binary_result_path = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/tmp/evaluation_reports/Conan/binary_ai/evaluation_report_2025-07-30-10-03-54_converted.json"
    binary_result_path = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/tmp/evaluation_reports/Conan/binary_ai/evaluation_report_2025-07-30-12-54-29_converted.json"
    evaluator.analyze_baseline_result(binary_result_path)

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
    top_n = 5
    config = EvaluationConfig(
        benchmark_file=benchmark_meta,
        test_case_dir=benchmark_tc_dir,
        feature_matching_top_n=top_n,
        use_agent=False,
        concurrency=10,
        slice_start=0,
        slice_end=100,
    )

    # 初始化评估器
    evaluator = Evaluator(config)

    # 评估
    evaluator.run_benchmark(analyze_context=False)
    evaluator.report.dump(evaluation_report_save_path)

    # 分析结果
    # RQ 1 topn 和 效果的相关性
    analyze_feature_matching_top_n_effectiveness(evaluator, evaluation_report_save_path, top_n_effectiveness_analysis_result_path, top_n=top_n)
    # top_n_effectiveness 绘图
    plot_feature_matching_top_n_effectiveness_figure(top_n_effectiveness_analysis_result_path)

    # RQ 2 漏报的原因分类
    classify_feature_matching_cases_having_fn(evaluator,
                                              benchmark_meta,
                                              evaluation_report_save_path)

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
        feature_matching_top_n=5,
        # use_agent=False,
        concurrency=50,
        slice_start=0,
        slice_end=500,
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
    # run_feature_matching_only()
    # analyze_baseline()