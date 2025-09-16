# BLADE

A multi-agent C/C++ binary TPL detection framework for identifying third-party libraries in compiled binaries.

## 📌 Repository Notice

This repository contains the core components of BLADE framework. Due to anonymous peer review requirements, we are temporarily hosting the code at this location. Once the paper review process is complete, we will migrate this repository back to its original location.

In addition to the core framework presented here, we have developed a comprehensive ecosystem including:
- **Web API** - RESTful services for integration
- **User Interface** - Interactive web-based frontend  
- **Asynchronous Processing** - Background task management
- **Additional Tools** - Supporting utilities and extensions

All supplementary components will be open-sourced together after the paper review process concludes.

---

*We appreciate your understanding during the review period and look forward to sharing the complete BLADE ecosystem with the community soon.*

## 📋 Requirements

- **Operating System**: MacOS 13+ or Ubuntu 20.04+
- **Python**: 3.11 or higher
- **Docker**: Latest version

## 🚀 Quick Start

### 1. Clone Repository
```bash
git clone [repository-url]
cd blade
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Database Setup

#### 3.1 Download Database
Download the database backup file (~1GB):
- [📥 Database Backup](https://drive.google.com/file/d/1FnziXzxlPsHXLGVGd69EMaDQffDGQM6H/view?usp=sharing)

#### 3.2 Start PostgreSQL Container
```bash
docker-compose -f compose/docker-compose-db.yml up -d
```

#### 3.3 Import Database
```bash
docker exec -i bsca_data_1_0_5 psql -U tpl_data -d tpl_data < tpl_data.sql
```

### 4. Environment Configuration

#### 4.1 Create Configuration File
```bash
cp .env.example .env
```

#### 4.2 Edit Configuration
Update the `.env` file with your database connection parameters and other settings as needed.

### 5. Run Demo

#### 5.1 Configure Demo
Edit the file path in `demo.py` to point to your test binary.

#### 5.2 Execute Demo
```bash
python demo.py
```

## 📊 Benchmark Evaluation

### 1. Download Benchmark Files

#### Benchmark Metadata
- [📥 Benchmark Metafile](https://drive.google.com/file/d/1yK56oShgH5yRLDy2YsTuAjMHJZCS1dB2/view?usp=sharing)

#### Test Cases
- [📥 Benchmark Dataset (~600MB)](https://drive.google.com/file/d/1_L5lwdNImlOnIKq8ExhktTkvYfrjU7aK/view?usp=drive_link)

### 2. Configure Evaluation

Extract the benchmark files and update the following variables in `evaluation_runner.py`:

```python
# File paths
conan_test_case_dir = "path/to/your/test/cases"
conan_benchmark_meta_file = "path/to/your/benchmark/metafile"
evaluation_result_file = "path/to/your/results/file"

# Evaluation configuration
config = EvaluationConfig(
    benchmark_file=conan_benchmark_meta_file,     # Benchmark metafile path
    test_case_dir=conan_test_case_dir,           # Test cases directory
    feature_matching_top_n=5,                    # Top N results for feature matching
    use_agent=False,                             # Enable multi-agent mode
    concurrency=30,                              # Concurrent processes
    slice_start=0,                               # Benchmark slice start index
    # slice_end=10,                              # Benchmark slice end index (optional)
    input_token_price_per_1M=0.4,               # Input token pricing (per 1M tokens)
    output_token_price_per_1M=1.6,              # Output token pricing (per 1M tokens)
)
```

### 3. Run Evaluation
```bash
python evaluation_runner.py
```

## 🔧 Configuration Options

| Parameter | Description | Default |
|-----------|-------------|---------|
| `feature_matching_top_n` | Number of top results to consider | 5       |
| `use_agent` | Enable multi-agent detection mode | True    |
| `concurrency` | Number of parallel processes | 30      |
| `slice_start/end` | Benchmark subset selection | 0/None  |

## 💰 Cost Estimation

The framework includes token-based cost estimation for API usage:
- Input tokens: $0.4 per 1M tokens
- Output tokens: $1.6 per 1M tokens

---
