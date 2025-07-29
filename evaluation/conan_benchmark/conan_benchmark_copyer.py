import os
import sys

from environs import Env
from loguru import logger
from tqdm import tqdm

from evaluation.general_benchmarks.interface import Benchmark as GeneralBenchmark

env = Env()
env.read_env()
logger.remove()
logger.add(sys.stderr, level="INFO")



def copy_test_cases_from_to(benchmark: GeneralBenchmark, from_dir: str, to_dir: str):

    for test_case in tqdm(benchmark.test_cases, desc="Copying test cases"):
        rel_path = test_case.test_binary.relative_path
        from_path = os.path.join(from_dir, rel_path)
        to_path = os.path.join(to_dir, rel_path)

        # Ensure the directory exists
        os.makedirs(os.path.dirname(to_path), exist_ok=True)

        # Copy the file if it exists
        if os.path.exists(from_path):
            os.system(f"cp '{from_path}' '{to_path}'")
        else:
            print(f"Warning: {from_path} does not exist, skipping copy.")





if __name__ == '__main__':
    # paths
    evaluation_dir = env.str("EVALUATION_DIR_PATH")

    conan_benchmark = os.path.join(evaluation_dir, "conan_benchmark")
    general_benchmarks = os.path.join(evaluation_dir, "general_benchmarks")

    conan_benchmark_meta_dir = os.path.join(conan_benchmark, "benchmark_meta")
    general_benchmark_meta_dir = os.path.join(general_benchmarks, "benchmark_meta")

    conan_benchmark_path = os.path.join(conan_benchmark_meta_dir, "conan_library_benchmark.json")
    general_benchmark_path = os.path.join(general_benchmark_meta_dir, "conan_library_benchmark.json")

    conan_libs_builder_output_dir = env.str("CONAN_LIBS_BUILDER_OUTPUT")

    conan_benchmark_test_case_dir = env.str("CONAN_BENCHMARK_TEST_CASE_DIR")


