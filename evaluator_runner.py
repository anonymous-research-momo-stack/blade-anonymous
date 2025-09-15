from environs import Env

from evaluation.general_benchmarks.evaluator import Evaluator
from evaluation.general_benchmarks.interface import EvaluationConfig

env = Env()
env.read_env()


def main():
    # benchmark meta
    evaluation_dir = env.str("EVALUATION_DIR_PATH")
    evaluation_output_dir = env.str("EVALUATION_OUTPUT_DIR_PATH")
    conan_test_case_dir = env.str("CONAN_BENCHMARK_TEST_CASE_DIR")

    conan_benchmark_meta_file = f"{evaluation_dir}/general_benchmarks/benchmark_meta/conan_library_benchmark_20250831_2032.json"

    evaluation_result_file = f"{evaluation_output_dir}/Conan/ours/gpt_5_mini_no_COT/evaluation_report.json"

    # evaluation config
    config = EvaluationConfig(
        benchmark_file=conan_benchmark_meta_file,
        test_case_dir=conan_test_case_dir,
        feature_matching_top_n=5,
        use_agent=False,
        concurrency=30,
        slice_start=0,
        # slice_end=10,
        input_token_price_per_1M=0.4,
        output_token_price_per_1M=1.6,
    )

    # evaluator
    evaluator = Evaluator(config)

    # run benchmark
    evaluator.run_benchmark(analyze_context=False)

    # dump report
    evaluator.report.dump(evaluation_result_file)


if __name__ == '__main__':
    main()
