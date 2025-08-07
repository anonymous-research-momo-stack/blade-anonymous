#!/usr/bin/env python3
"""
Software Composition Analysis Detection Script
Automatically chooses single or batch detection based on input file count
"""

import os
import sys
import argparse
import time
import json
from typing import List

from app.services.tpl_detection.detection_workflow import DetectionWorkflow
from app.services.tpl_detection.batch_detection_workflow import BatchDetectionWorkflow


def single_detection(binary_path: str, result_path: str, **kwargs):
    """
    Single file detection

    Args:
        binary_path: Path to the binary file to be detected
        result_path: Path to save the result
        **kwargs: Other parameters
    """
    print(f"Starting single file detection: {binary_path}")

    # Create detection workflow
    workflow = DetectionWorkflow(
        enable_bin_info_analysis_web_search=kwargs.get('enable_web_search', False),
        feature_matching_return_top_n=kwargs.get('top_n', 5),
        debug_mode=kwargs.get('debug_mode', False),
        use_agent=kwargs.get('use_agent', True)
    )

    try:
        # Execute detection
        start_time = time.time()
        result = workflow.run(binary_path)
        total_time = time.time() - start_time

        print(f"Detection completed, elapsed time: {total_time:.2f} seconds")

        # Preview analysis results
        if kwargs.get('preview', True):
            result.analysis_data.preview()

        # Save result
        result.dump_to_file(result_path)
        print(f"Result saved to: {result_path}")

    except Exception as e:
        print(f"Detection failed: {str(e)}")
        return False

    return True


def batch_detection(file_paths: List[str], result_save_path: str, **kwargs):
    """
    Batch file detection

    Args:
        file_paths: List of file paths to be detected
        result_save_path: Path to save the combined results file
        **kwargs: Other parameters
    """
    print(f"Starting batch detection for {len(file_paths)} files")

    # Ensure result save directory exists
    result_dir = os.path.dirname(result_save_path)
    if result_dir:
        os.makedirs(result_dir, exist_ok=True)

    # Create batch detection workflow
    batch_workflow = BatchDetectionWorkflow(
        concurrency=kwargs.get('concurrency', 3),
        feature_matching_return_top_n=kwargs.get('top_n', 3)
    )

    try:
        # Execute batch detection
        start_time = time.time()
        results = batch_workflow.run_batch(file_paths)
        total_time = time.time() - start_time

        print(f"\nBatch detection completed, total time: {total_time:.2f} seconds\n")

        # Process and combine results
        combined_results = {
            "batch_info": {
                "total_files": len(file_paths),
                "total_time_seconds": round(total_time, 2),
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            },
            "results": []
        }

        success_count = 0
        for idx, result in enumerate(results):
            file_name = os.path.basename(file_paths[idx])
            file_path = file_paths[idx]

            if result is not None:
                # Convert result to dictionary format
                result_data = {
                    "file_index": idx,
                    "file_name": file_name,
                    "file_path": file_path,
                    "status": "success",
                    "analysis_data": result.to_dict() if hasattr(result, 'to_dict') else str(result)
                }

                if kwargs.get('show_durations', False) and hasattr(result, 'analysis_data') and hasattr(
                        result.analysis_data, 'durations'):
                    result_data["durations"] = result.analysis_data.durations

                print(f"File {idx + 1} ({file_name}) detection successful")
                success_count += 1
            else:
                result_data = {
                    "file_index": idx,
                    "file_name": file_name,
                    "file_path": file_path,
                    "status": "failed",
                    "analysis_data": None
                }
                print(f"File {idx + 1} ({file_name}) detection failed")

            combined_results["results"].append(result_data)

        # Update batch info
        combined_results["batch_info"]["successful_files"] = success_count
        combined_results["batch_info"]["failed_files"] = len(file_paths) - success_count

        # Save combined results to single file
        with open(result_save_path, 'w', encoding='utf-8') as f:
            json.dump(combined_results, f, indent=2, ensure_ascii=False)

        print(f"\nBatch detection summary: {success_count}/{len(file_paths)} files successful")
        print(f"All results saved to: {result_save_path}")

    except Exception as e:
        print(f"Batch detection failed: {str(e)}")
        return False

    return True


def main():
    parser = argparse.ArgumentParser(
        description="Software Composition Analysis Detection Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Single file detection:
    python detect.py -i /path/to/binary -o result.json

  Multiple files detection:
    python detect.py -i /path/to/file1 /path/to/file2 /path/to/file3 -o results.json

  Detection from file list:
    python detect.py --file-list /path/to/file_list.txt -o results.json
        """
    )

    # Input arguments
    parser.add_argument('-i', '--input', nargs='*',
                        help='Input file path(s)')
    parser.add_argument('--file-list',
                        help='Text file containing file paths, one path per line')
    parser.add_argument('-o', '--output', required=True,
                        help='Output result file path')

    # Detection parameters
    parser.add_argument('--top-n', type=int, default=5,
                        help='Feature matching top n results (default: 5 for single, 3 for batch)')
    parser.add_argument('--enable-web-search', action='store_true',
                        help='Enable web search functionality (single detection only)')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug mode (single detection only)')
    parser.add_argument('--no-agent', action='store_true',
                        help='Disable agent functionality (single detection only)')
    parser.add_argument('--no-preview', action='store_true',
                        help='Do not preview results (single detection only)')

    # Batch detection parameters
    parser.add_argument('--concurrency', type=int, default=3,
                        help='Concurrency level for batch detection (default: 3)')
    parser.add_argument('--show-durations', action='store_true',
                        help='Show detailed timing information (batch detection only)')

    args = parser.parse_args()

    # Collect file paths
    file_paths = []

    # Get file paths from command line arguments
    if args.input:
        file_paths.extend(args.input)

    # Get paths from file list
    if args.file_list:
        if not os.path.exists(args.file_list):
            print(f"Error: File list does not exist: {args.file_list}")
            return 1

        with open(args.file_list, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    file_paths.append(line)

    if not file_paths:
        print("Error: No input files specified")
        parser.print_help()
        return 1

    # Check if files exist
    missing_files = [f for f in file_paths if not os.path.exists(f)]
    if missing_files:
        print("Error: The following files do not exist:")
        for f in missing_files:
            print(f"  {f}")
        return 1

    # Ensure output directory exists
    output_dir = os.path.dirname(args.output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    # Auto-detect detection mode based on file count
    if len(file_paths) == 1:
        # Single file detection
        print(f"Auto-detected: Single file detection mode")
        success = single_detection(
            binary_path=file_paths[0],
            result_path=args.output,
            enable_web_search=args.enable_web_search,
            top_n=args.top_n,
            debug_mode=args.debug,
            use_agent=not args.no_agent,
            preview=not args.no_preview
        )
    else:
        # Batch file detection
        print(f"Auto-detected: Batch detection mode ({len(file_paths)} files)")
        # Use default top_n=3 for batch if user didn't specify
        batch_top_n = 3 if args.top_n == 5 else args.top_n
        success = batch_detection(
            file_paths=file_paths,
            result_save_path=args.output,
            concurrency=args.concurrency,
            top_n=batch_top_n,
            show_durations=args.show_durations
        )

    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())