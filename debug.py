from app.tpl_detection.detection_workflow import DetectionWorkflow
from app.tpl_detection.batch_detection_workflow import BatchDetectionWorkflow
import time


def demo():
    openssl_path = "/Users/liuchengyue/Desktop/BinarySCA Platform/Data/Test Cases/TPL Test Cases/Benchmarks/FTPL100/decompressed_deb/openssl_3.0.2-0ubuntu1.18_amd64/usr/bin/openssl"
    libpng16_so_path = "/Users/liuchengyue/Desktop/BinarySCA Platform/Data/Test Cases/TPL Test Cases/Benchmarks/FTPL100/decompressed_deb/libpng16-16_1.6.37-3build5_amd64/usr/lib/x86_64-linux-gnu/libpng16.so.16"
    ffmpeg_path = "/Users/liuchengyue/Desktop/BinarySCA Platform/Data/Test Cases/TPL Test Cases/Benchmarks/FTPL100/decompressed_deb/ffmpeg_7%3a4.4.2-0ubuntu0.22.04.1_amd64/usr/bin/ffmpeg"
    libsqlite3_so_path = "/Users/liuchengyue/Desktop/BinarySCA Platform/Data/Test_Cases/TPL_Test_Cases/Benchmarks/FTPL100/decompressed_deb/libsqlite3-0_3.37.2-2ubuntu0.3_amd64/usr/lib/x86_64-linux-gnu/libsqlite3.so.0.8.6"

    workflow = DetectionWorkflow(
        feature_matching_return_top_n=3,
    )

    result = workflow.run(libsqlite3_so_path)

    result.analysis_data.preview()

    result_save_path = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/tmp/analysis_result.json"
    result.dump_to_file(result_save_path)

def debug_batch():
    openssl_path = "/Users/liuchengyue/Desktop/BinarySCA Platform/Data/Test Cases/TPL Test Cases/Benchmarks/FTPL100/decompressed_deb/openssl_3.0.2-0ubuntu1.18_amd64/usr/bin/openssl"
    libpng16_so_path = "/Users/liuchengyue/Desktop/BinarySCA Platform/Data/Test Cases/TPL Test Cases/Benchmarks/FTPL100/decompressed_deb/libpng16-16_1.6.37-3build5_amd64/usr/lib/x86_64-linux-gnu/libpng16.so.16"
    ffmpeg_path = "/Users/liuchengyue/Desktop/BinarySCA Platform/Data/Test Cases/TPL Test Cases/Benchmarks/FTPL100/decompressed_deb/ffmpeg_7%3a4.4.2-0ubuntu0.22.04.1_amd64/usr/bin/ffmpeg"

    file_paths = [openssl_path, libpng16_so_path, ffmpeg_path]
    batch_workflow = BatchDetectionWorkflow(concurrency=3, feature_matching_return_top_n=3)
    start_time = time.time()
    results = batch_workflow.run_batch(file_paths)
    total_time = time.time() - start_time
    print(f"\n总耗时: {total_time:.2f} 秒\n")

    for idx, result in enumerate(results):
        if result is not None:
            save_path = f"/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/tmp/analysis_result_{idx}.json"
            result.dump_to_file(save_path)
            print(f"Result {idx} saved to {save_path}")
            print(f"Result {idx} durations:")
            print(result.analysis_data.durations)
        else:
            print(f"Result {idx} failed.")

if __name__ == '__main__':
    # debug_batch()
    demo()