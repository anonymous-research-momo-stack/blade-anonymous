import os.path

from app.services.tpl_detection.detection_workflow import DetectionWorkflow
from app.services.tpl_detection.batch_detection_workflow import BatchDetectionWorkflow
import time

def run_test_case(openssl_path, result_save_path):
    # analysis workflow
    workflow = DetectionWorkflow(
        enable_bin_info_analysis_web_search=False,
        feature_matching_return_top_n=5,
        debug_mode=False,
        use_agent=True,
        # enable_tpl_analysis_web_search=True
    )


    # run analysis
    result = workflow.run(openssl_path)

    # preview analysis result
    result.analysis_data.preview()

    # dump result
    result.dump_to_file(result_save_path)

def main():
    openssl_path = "/Users/liuchengyue/Desktop/BinarySCA Platform/Data/Test_Cases/TPL_Test_Cases/Benchmarks/FTPL100/decompressed_deb/openssl_3.0.2-0ubuntu1.18_amd64/usr/bin/openssl"
    result_save_path = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/tmp/analysis_result.json"
    run_test_case(openssl_path, result_save_path)


if __name__ == '__main__':
    main()