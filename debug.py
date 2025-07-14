from app.tpl_detection.detection_workflow import DetectionWorkflow


def demo():
    openssl_path = "/Users/liuchengyue/Desktop/BinarySCA Platform/Data/Test Cases/TPL Test Cases/Benchmarks/FTPL100/decompressed_deb/openssl_3.0.2-0ubuntu1.18_amd64/usr/bin/openssl"
    libpng16_so_path = "/Users/liuchengyue/Desktop/BinarySCA Platform/Data/Test Cases/TPL Test Cases/Benchmarks/FTPL100/decompressed_deb/libpng16-16_1.6.37-3build5_amd64/usr/lib/x86_64-linux-gnu/libpng16.so.16"
    ffmpeg_path = "/Users/liuchengyue/Desktop/BinarySCA Platform/Data/Test Cases/TPL Test Cases/Benchmarks/FTPL100/decompressed_deb/ffmpeg_7%3a4.4.2-0ubuntu0.22.04.1_amd64/usr/bin/ffmpeg"

    workflow = DetectionWorkflow(
        top_n=3,
    )

    result = workflow.run(ffmpeg_path)

    result.analysis_data.preview()


if __name__ == '__main__':
    demo()