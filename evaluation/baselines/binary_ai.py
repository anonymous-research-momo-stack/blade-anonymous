import os
import queue

from binaryai import BinaryAI
from environs import Env
from tqdm import tqdm

from evaluation.general_benchmarks.interface import Benchmark

env = Env()
env.read_env(".env")  # load .env file

import json
import schedule
import time
from datetime import datetime
from pathlib import Path




def run_benchmark(benchmark:Benchmark, test_case_dir: str):

    # 初始化 BinaryAI 客户端
    print(f"init BinaryAI client")
    bai = BinaryAI(
        secret_id=env.str("BINARYAI_SECRET_ID"),
        secret_key=env.str("BINARYAI_SECRET_KEY")
    )


    # 构建上传任务队列
    print('Building upload queue')
    upload_q = queue.Queue()
    # 临时限制前30个
    for tc in benchmark.test_cases:
        file_path = f"{test_case_dir}/{tc.test_binary.relative_path}"
        upload_q.put(file_path)

    # 上传直至全部成功
    time_out = 14 * 60 * 60  # 3 hour timeout
    start_at = time.perf_counter()
    last_print_time = start_at
    successful_count = 0
    total_files = len(benchmark.test_cases)
    upload_succeed_dict = {}
    while not upload_q.empty():
        if time.perf_counter() - start_at > time_out:
            print("Upload timed out.")
            break
        file_path = upload_q.get()
        try:
            sha256 = bai.upload(file_path)
            successful_count += 1
            upload_succeed_dict[file_path] = {
                "sha256": sha256,
                "file_size": file_path,
                'upload_at': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            }
            # 每10秒打印一次进度
            current_time = time.perf_counter()
            if current_time - last_print_time >= 10:
                elapsed_time = current_time - start_at
                avg_time_per_file = elapsed_time / successful_count if successful_count > 0 else 0
                print(
                    f"已耗时: {elapsed_time:.1f}秒, 成功上传: {successful_count}/{total_files}, 平均每个: {avg_time_per_file:.2f}秒")
                last_print_time = current_time
        except Exception as e:
            print(f"Failed to upload {file_path}: {e}")
            upload_q.put(file_path)
            continue

    # 统计失败的上传路径
    failed_paths = []
    while not upload_q.empty():
        failed_paths.append(upload_q.get())

    upload_log = {
        "total_files": total_files,
        "successful_count": successful_count,
        "failed_count": len(failed_paths),
        "failed_paths": failed_paths,
        "upload_succeed_dict": upload_succeed_dict
    }

    # 保存失败的上传路径到 JSON 文件
    with open(f"upload_log.json", "w") as f:
        json.dump(upload_log, f, indent=4, ensure_ascii=False)

    # 生成评估报告
    print(f"Upload finished, {successful_count}/{total_files} files uploaded successfully.")

def _get_benchmark_results(benchmark:Benchmark, result_json_path: str):
    # 初始化 BinaryAI 客户端
    print(f"init BinaryAI client")
    bai = BinaryAI(
        secret_id=env.str("BINARYAI_SECRET_ID"),
        secret_key=env.str("BINARYAI_SECRET_KEY")
    )

    results = []
    for tc in tqdm(benchmark.test_cases[:30], desc="Get SCA Results"):
        sha256 = tc.test_binary.sha256
        status = bai.get_analyze_status(sha256)
        components = []
        try:
            for lib in bai.get_sca_result(sha256):
                components.append({
                    "name": lib.name,
                    "version": lib.version,
                    "description": lib.description,
                    "source_code_url": lib.source_code_url,
                    "summary": lib.summary,
                })

            results.append({
                "test_case": tc.test_binary.relative_path,
                "sha256": sha256,
                "status": status,
                "components": components
            })

        except Exception as e:
            print(f"Failed to get SCA results for {sha256}: {e}")
            components = []
            results.append({
                "test_case": tc.test_binary.relative_path,
                "sha256": sha256,
                "status": status,
                "finished_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "components": components,
                "error": str(e)
            })

    return results




def get_benchmark_results(benchmark, result_json_path: str):
    """
    每1小时保存1次结果，文件名加上时间后缀

    :param benchmark: Benchmark对象
    :param result_json_path: 基础结果路径
    """
    try:
        print(f"开始获取基准测试结果，保存到: {result_json_path}")
        # 生成带时间后缀的文件路径
        timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        path_obj = Path(result_json_path)
        timestamped_path = path_obj.parent / f"{path_obj.stem}_{timestamp}{path_obj.suffix}"

        # 执行benchmark
        results = _get_benchmark_results(benchmark, str(timestamped_path))

        # 确保目录存在
        timestamped_path.parent.mkdir(parents=True, exist_ok=True)

        # 保存结果
        with open(timestamped_path, "w", encoding='utf-8') as f:
            json.dump(results, f, indent=4, ensure_ascii=False)

        print(f"✅ 成功保存: {timestamped_path}")

    except Exception as e:
        print(f"❌ 执行失败: {e}")


def start_hourly_job(benchmark, result_json_path: str):
    """
    启动每小时执行的定时任务
    """
    # 安排任务：每小时执行一次
    # 测试，每分钟执行1次
    schedule.every().hour.do(get_benchmark_results, benchmark, result_json_path)

    print("🚀 定时任务已启动，每小时执行一次")
    print("按 Ctrl+C 停止...")

    # 持续运行
    while True:
        schedule.run_pending()
        time.sleep(1)



def main():
    evaluation_dir = env.str("EVALUATION_DIR_PATH")

    conan_benchmark = os.path.join(evaluation_dir, "conan_benchmark")
    general_benchmarks = os.path.join(evaluation_dir, "general_benchmarks")

    conan_benchmark_meta_dir = os.path.join(conan_benchmark, "benchmark_meta")
    general_benchmark_meta_dir = os.path.join(general_benchmarks, "benchmark_meta")

    conan_benchmark_path = os.path.join(conan_benchmark_meta_dir, "conan_library_benchmark.json")
    general_benchmark_path = os.path.join(general_benchmark_meta_dir, "conan_library_benchmark.json")
    conan_libs_builder_output_dir = env.str("CONAN_LIBS_BUILDER_OUTPUT")

    conan_benchmark_test_case_dir = env.str("CONAN_BENCHMARK_TEST_CASE_DIR")

    Conan_evluation_report_path = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/tmp/evaluation_reports/Conan/binary_ai/evaluation_report.json"
    # Conan_evluation_report_path = "/home/chengyue/data/evaluation_results/binaryai/evaluation_report.json"

    # 加载基准测试元数据
    print(f"laod benchmark data")
    benchmark = Benchmark.load_from_json_file(general_benchmark_path)

    # 运行
    run_benchmark(benchmark, conan_benchmark_test_case_dir)

    # 获取结果，每10分钟获取一次结果。
    get_benchmark_results(benchmark, Conan_evluation_report_path)

    start_hourly_job(benchmark, Conan_evluation_report_path)

if __name__ == '__main__':
    main()
