import os.path

from app.services.tpl_detection.detection_workflow import DetectionWorkflow
from app.services.tpl_detection.batch_detection_workflow import BatchDetectionWorkflow
import time

def debug_batch():
    openssl_path = "/Users/liuchengyue/Desktop/BinarySCA Platform/Data/Test_Cases/TPL_Test_Cases/Benchmarks/FTPL100/decompressed_deb/openssl_3.0.2-0ubuntu1.18_amd64/usr/bin/openssl"
    libpng16_so_path = "/Users/liuchengyue/Desktop/BinarySCA Platform/Data/Test_Cases/TPL_Test_Cases/Benchmarks/FTPL100/decompressed_deb/libpng16-16_1.6.37-3build5_amd64/usr/lib/x86_64-linux-gnu/libpng16.so.16"
    ffmpeg_path = "/Users/liuchengyue/Desktop/BinarySCA Platform/Data/Test_Cases/TPL_Test_Cases/Benchmarks/FTPL100/decompressed_deb/ffmpeg_7%3a4.4.2-0ubuntu0.22.04.1_amd64/usr/bin/ffmpeg"

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

def demo():
    openssl_path = "/Users/liuchengyue/Desktop/BinarySCA Platform/Data/Test_Cases/TPL_Test_Cases/Benchmarks/FTPL100/decompressed_deb/openssl_3.0.2-0ubuntu1.18_amd64/usr/bin/openssl"
    libpng16_so_path = "/Users/liuchengyue/Desktop/BinarySCA Platform/Data/Test_Cases/TPL_Test_Cases/Benchmarks/FTPL100/decompressed_deb/libpng16-16_1.6.37-3build5_amd64/usr/lib/x86_64-linux-gnu/libpng16.so.16"
    ffmpeg_path = "/Users/liuchengyue/Desktop/BinarySCA Platform/Data/Test_Cases/TPL_Test_Cases/Benchmarks/FTPL100/decompressed_deb/ffmpeg_7%3a4.4.2-0ubuntu0.22.04.1_amd64/usr/bin/ffmpeg"
    libsqlite3_so_path = "/Users/liuchengyue/Desktop/BinarySCA Platform/Data/Test_Cases/TPL_Test_Cases/Benchmarks/FTPL100/decompressed_deb/libsqlite3-0_3.37.2-2ubuntu0.3_amd64/usr/lib/x86_64-linux-gnu/libsqlite3.so.0.8.6"
    fftw3_path = "/Users/liuchengyue/Desktop/BinarySCA Platform/Data/Test_Cases/TPL_Test_Cases/Benchmarks/FTPL100/decompressed_deb/libfftw3-double3_3.3.8-2ubuntu8_amd64/usr/lib/x86_64-linux-gnu/libfftw3.so.3.5.8"
    libpg_path = "/Users/liuchengyue/Desktop/BinarySCA Platform/Data/Test_Cases/TPL_Test_Cases/Benchmarks/FTPL100/decompressed_deb/libpq5_14.15-0ubuntu0.22.04.1_amd64/usr/lib/x86_64-linux-gnu/libpq.so.5.14"
    libvulkan_path = "/Users/liuchengyue/Desktop/BinarySCA Platform/Data/Test_Cases/TPL_Test_Cases/Benchmarks/FTPL100/decompressed_deb/libvulkan1_1.3.204.1-2_amd64/usr/lib/x86_64-linux-gnu/libvulkan.so.1.3.204"

    # Car cases
    # mbedtls
    secverify_path = "/Users/liuchengyue/Desktop/BinarySCA Platform/Data/Test_Cases/TPL_Test_Cases/BYD/update/mdm9607-boot.img.xx_/ramdisk.xx_/usr/bin/secverify"
    libdevmapper_so_path = "/Users/liuchengyue/Desktop/BinarySCA Platform/Data/Test_Cases/TPL_Test_Cases/BYD/update/mdm9607-boot.img.xx_/ramdisk.xx_/usr/lib/libdevmapper.so.1.02"

    # DDE 2000
    libpulse_so = "/Users/liuchengyue/Desktop/BinarySCA Platform/Data/Test_Cases/TPL_Test_Cases/Benchmarks/DDE2000/libpulse.so"
    sktest = "/Users/liuchengyue/Desktop/BinarySCA Platform/Data/Test_Cases/TPL_Test_Cases/Benchmarks/DDE2000/sktest" # 特征匹配不到
    care = "/Users/liuchengyue/Desktop/BinarySCA Platform/Data/Test_Cases/TPL_Test_Cases/Benchmarks/DDE2000/care" # 特征匹配不到
    libcpu_ldap = "/Users/liuchengyue/Desktop/BinarySCA Platform/Data/Test_Cases/TPL_Test_Cases/Benchmarks/DDE2000/libcpu_ldap.so.0.0.0"

    # 根目录
    root_path = "/Users/liuchengyue/Desktop/BinarySCA Platform/Data/Test_Cases/TPL_Test_Cases/BYD/"

    # conan test cases
    conan_bin_dir = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/evaluation/conan_libs_builder_output/"

    grpc_cpp_plugin_shared = os.path.join(conan_bin_dir, "grpc/1.72.0/grpc_1.72.0_x86_64-gcc-release-shared/full_deploy/host/grpc/1.72.0/Release/x86_64/bin/grpc_cpp_plugin")
    setfattr_static = os.path.join(conan_bin_dir, "acl/2.3.1/acl_2.3.1_x86_64-gcc-release-static/full_deploy/host/libattr/2.5.1/Release/x86_64/bin/setfattr")
    setfacl_shared = os.path.join(conan_bin_dir, "acl/2.3.1/acl_2.3.1_arm_64-gcc-release-shared/full_deploy/host/acl/2.3.1/Release/armv8/bin/setfacl")
    getfacl_static = os.path.join(conan_bin_dir, "acl/2.3.1/acl_2.3.1_x86_64-gcc-release-static/full_deploy/host/acl/2.3.1/Release/x86_64/bin/getfacl")
    libacl_so = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/evaluation/conan_libs_builder_output/acl/2.3.1/acl_2.3.1_x86_64-clang-release-shared/full_deploy/host/acl/2.3.1/Release/x86_64/lib/libacl.so"
    getfattr = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/evaluation/conan_libs_builder_output/acl/2.3.1/acl_2.3.1_x86_64-gcc-release-static/full_deploy/host/libattr/2.5.1/Release/x86_64/bin/getfattr"
    libgrpc_so = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/evaluation/conan_libs_builder_output/grpc/1.72.0/grpc_1.72.0_x86_64-gcc-release-shared/full_deploy/host/grpc/1.72.0/Release/x86_64/lib/libgrpc.so"

    grpc_cpp_plugin_static = os.path.join(conan_bin_dir,
                                          "grpc/1.72.0/grpc_1.72.0_x86_64-gcc-release-static/full_deploy/host/grpc/1.72.0/Release/x86_64/bin/grpc_csharp_plugin")

    libaaplus_so = "/Users/liuchengyue/Desktop/BinarySCA Platform/Data/Test_Cases/TPL_Test_Cases/conan_test_cases/aaplus/2.53/aaplus_2.53_arm_64-gcc-release-shared/full_deploy/host/aaplus/2.53/Release/armv8/lib/libaaplus.so"
    imake = "/Users/liuchengyue/Desktop/BinarySCA Platform/Data/Test_Cases/TPL_Test_Cases/conan_test_cases/imake/1.0.9/imake_1.0.9_arm_64-gcc-release-shared/full_deploy/host/imake/1.0.9/Release/armv8/bin/imake"
    boost = "/Users/liuchengyue/Desktop/BinarySCA Platform/Data/Test_Cases/TPL_Test_Cases/conan_test_cases/cgal/6.0.1/cgal_6.0.1_x86_64-gcc-release-shared/full_deploy/host/boost/1.83.0/Release/x86_64/lib/libboost_system.so.1.83.0"

    libnsimd_cpu = "/Users/liuchengyue/Desktop/BinarySCA Platform/Data/Test_Cases/TPL_Test_Cases/conan_test_cases/nsimd/3.0.1/nsimd_3.0.1_arm_64-gcc-release-shared/full_deploy/host/nsimd/3.0.1/Release/armv8/lib/libnsimd_cpu.so"
    libz_so = "/Users/liuchengyue/Desktop/BinarySCA Platform/Data/Test_Cases/TPL_Test_Cases/conan_test_cases/cgal/6.0.1/cgal_6.0.1_x86_64-clang-release-shared/full_deploy/host/zlib/1.3.1/Release/x86_64/lib/libz.so.1.3.1"
    boost = "/Users/liuchengyue/Desktop/BinarySCA Platform/Data/Test_Cases/TPL_Test_Cases/conan_test_cases/cgal/6.0.1/cgal_6.0.1_x86_64-gcc-release-shared/full_deploy/host/boost/1.83.0/Release/x86_64/lib/libboost_system.so.1.83.0"
    libPcap = "/Users/liuchengyue/Desktop/BinarySCA Platform/Data/Test_Cases/TPL_Test_Cases/conan_test_cases/pcapplusplus/25.05/pcapplusplus_25.05_x86_64-gcc-release-shared/full_deploy/host/pcapplusplus/25.05/Release/x86_64/lib/libPcap++.so.25.05"
    libazure = "/Users/liuchengyue/Desktop/BinarySCA Platform/Data/Test_Cases/TPL_Test_Cases/conan_test_cases/azure-sdk-for-cpp/1.11.3/azure-sdk-for-cpp_1.11.3_x86_64-gcc-release-shared/full_deploy/host/azure-sdk-for-cpp/1.11.3/Release/x86_64/lib/libazure-core.so"
    m4 = "/Users/liuchengyue/Desktop/BinarySCA Platform/Data/Test_Cases/TPL_Test_Cases/conan_test_cases/nanodbc/cci.20200807/nanodbc_cci.20200807_x86_64-gcc-release-shared/full_deploy/host/m4/1.4.19/Release/x86_64/bin/m4"
    libohNet_so = "/Users/liuchengyue/Desktop/BinarySCA Platform/Data/Test_Cases/TPL_Test_Cases/conan_test_cases/ohnet/1.37.5454/ohnet_1.37.5454_x86_64-clang-release-shared/full_deploy/host/ohnet/1.37.5454/Release/x86_64/lib/libohNet.so"
    clp = "/Users/liuchengyue/Desktop/BinarySCA Platform/Data/Test_Cases/TPL_Test_Cases/conan_test_cases/coin-cgl/0.60.7/coin-cgl_0.60.7_x86_64-clang-release-shared/full_deploy/host/coin-clp/1.17.7/Release/x86_64/bin/clp"
    libboost_system = "/Users/liuchengyue/Desktop/BinarySCA Platform/Data/Test_Cases/TPL_Test_Cases/conan_test_cases/arg_router/1.3.0/arg_router_1.3.0_x86_64-clang-release-shared/full_deploy/host/boost/1.81.0/Release/x86_64/lib/libboost_system.so.1.81.0"
    libuuid = "/Users/liuchengyue/Desktop/BinarySCA Platform/Data/Test_Cases/TPL_Test_Cases/conan_test_cases/bmx/cci.20240517/bmx_cci.20240517_x86_64-gcc-release-shared/full_deploy/host/libuuid/1.0.3/Release/x86_64/lib/libuuid.so.1.0.0"
    libboost_system_182 = "/Users/liuchengyue/Desktop/BinarySCA Platform/Data/Test_Cases/TPL_Test_Cases/conan_test_cases/boost/1.88.0/boost_1.88.0_arm_64-gcc-release-shared/full_deploy/host/boost/1.88.0/Release/armv8/lib/libboost_system.so.1.88.0"
    kcov = "/Users/liuchengyue/Desktop/BinarySCA Platform/Data/Test_Cases/TPL_Test_Cases/conan_test_cases/kcov/42/kcov_42_x86_64-gcc-release-shared/full_deploy/host/kcov/42/x86_64/bin/kcov"
    libgrpc = "/Users/liuchengyue/Desktop/BinarySCA Platform/Data/Test_Cases/TPL_Test_Cases/conan_test_cases/etcd-cpp-apiv3/0.15.4/etcd-cpp-apiv3_0.15.4_x86_64-clang-release-shared/full_deploy/host/grpc/1.54.3/Release/x86_64/lib/libgrpc.so.31.0.0"
    libtcl8 = "/Users/liuchengyue/Desktop/BinarySCA Platform/Data/Test_Cases/TPL_Test_Cases/conan_test_cases/tcl/8.6.13/tcl_8.6.13_x86_64-gcc-release-shared/full_deploy/host/tcl/8.6.13/Release/x86_64/lib/libtcl8.6.so"
    libboost_system = "/Users/liuchengyue/Desktop/BinarySCA Platform/Data/Test_Cases/TPL_Test_Cases/conan_test_cases/svgpp/cci.20221030/svgpp_cci.20221030_arm_64-gcc-release-shared/full_deploy/host/boost/1.82.0/Release/armv8/lib/libboost_system.so.1.82.0"
    libhuffman_so = "/Users/liuchengyue/Desktop/BinarySCA Platform/Data/Test_Cases/TPL_Test_Cases/conan_test_cases/huffman/1.2.7/huffman_1.2.7_x86_64-clang-release-shared/full_deploy/host/huffman/1.2.7/Release/x86_64/lib/libhuffman.so"
    secverify = "/Users/liuchengyue/Desktop/BinarySCA Platform/Data/Test_Cases/TPL_Test_Cases/BYD/update/mdm9607-boot.img.xx_/ramdisk.xx_/usr/bin/secverify"


    # 分析工作流
    workflow = DetectionWorkflow(
        enable_bin_info_analysis_web_search=False,
        feature_matching_return_top_n=5,
        debug_mode=False,
        use_agent=True,
        # enable_tpl_analysis_web_search=True
    )


    # 分析
    result = workflow.run(secverify)

    # 结合上下文分析
    # context = workflow.analyze_context(root_path)
    # result = workflow.run(secverify_path, software_context=context)

    # 预览分析结果
    result.analysis_data.preview()

    result_save_path = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/tmp/analysis_result.json"
    result.dump_to_file(result_save_path)


if __name__ == '__main__':
    # debug_batch()
    demo()