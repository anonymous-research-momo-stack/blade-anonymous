# BLADE

A multi-agent C/C++ binary TPL detection framework.

## Requirements
- MacOS 13+/Ubuntu 20.04+
- Python 3.11+
- Docker

## Quick Start
### 1. Clone this Repository
### 2. Install required python dependencies: `pip install -r requirements.txt`
### 3. Prepare Database
#### 3.1 Download Database
Click [here](https://drive.google.com/file/d/1FnziXzxlPsHXLGVGd69EMaDQffDGQM6H/view?usp=sharing) to download the database_backup.sql (~1GB).


#### 3.2 Install and Start PostgreSQL with Docker
```shell
docker-compose -f compose/docker-compose-db.yml up -d
```

#### 3.3. Import Database Schema and data
```shell
docker exec -i bsca_data_1_0_5 psql -U tpl_data -d tpl_data < tpl_data.sql
```

### 4. Config environment variables by `.env` file
#### 4.1 Copy `.env.example` to `.env`
#### 4.2 Edit the `.env` file to set the params such as correct database connection parameters if needed.

### 5. Run Demo
#### 4.1 Edit the demo file path in `demo.py`
#### 4.2 Run 'python demo.py'

## Evaluation on Benchmark
### 1. Download Benchmark metafile
Click [here](https://drive.google.com/file/d/1JHk3y7g2Yy8X1F4v1Z4gYk9bX4e8t1nK/view?usp=sharing) to download the benchmark.

### 2. Download the Test Cases
Click [here](https://drive.google.com/file/d/1_L5lwdNImlOnIKq8ExhktTkvYfrjU7aK/view?usp=drive_link) to download the benchmark (~600MB).


### 3. Unzip the benchmark
edit `conan_test_case_dir`, `conan_benchmark_meta_file`, and `evaluation_result_file` in `evaluation_runner.py`

edit `evaluation_config` in `evaluation_runner.py` to set the params such as correct database connection parameters if needed.

```python
    config = EvaluationConfig(
        benchmark_file=conan_benchmark_meta_file, # path to the benchmark metafile
        test_case_dir=conan_test_case_dir, # path to the test cases
        feature_matching_top_n=5, # top n results to consider for feature matching
        use_agent=False, # whether to use multi-agent mode
        concurrency=30, # number of concurrent processes
        slice_start=0, # slice start index for slicing the benchmark
        # slice_end=10, # slice end index for slicing the benchmark
        input_token_price_per_1M=0.4, # input token price per 1M tokens
        output_token_price_per_1M=1.6, # output token price per 1M tokens
    )
```

