from app.tpl_detection.detection_workflow import DetectionWorkflow


def demo():
    openssl_path = "/Users/liuchengyue/Desktop/BinarySCA Platform/Data/Test Cases/TPL Test Cases/Benchmarks/FTPL100/decompressed_deb/openssl_3.0.2-0ubuntu1.18_amd64/usr/bin/openssl"

    workflow = DetectionWorkflow()

    result = workflow.run(openssl_path)

    print(result)



if __name__ == '__main__':
    demo()