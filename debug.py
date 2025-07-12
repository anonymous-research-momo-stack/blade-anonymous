from app.tpl_detection.detection_workflow import DetectionWorkflow


def demo():
    openssl_path = "/Users/liuchengyue/Desktop/BinarySCA Platform/Data/Test Cases/TPL Test Cases/Benchmarks/FTPL100/decompressed_deb/openssl_3.0.2-0ubuntu1.18_amd64/usr/bin/openssl"

    workflow = DetectionWorkflow()

    result = workflow.run(openssl_path)

    # preview
    for target_binary, libraries in result:
        print(f"Target Binary: {target_binary.binary_name}")
        if libraries:
            for lib in libraries:
                print(f"  - Library: {lib.name}, Matched Strings: {len(lib.matched_strings)}")
        else:
            print("  - No matching libraries found.")



if __name__ == '__main__':
    demo()