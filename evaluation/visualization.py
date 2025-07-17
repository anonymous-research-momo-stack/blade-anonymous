import json


def generate_analysis_report(report, output_filename: str) -> None:
    """
    生成研究数据的可视化分析报告 - 优化版

    Args:
        report: EvaluationReport实例
        output_filename: 输出的HTML文件名（如 "analysis_report.html"）
    """

    def safe_format(value, decimal_places=2):
        """安全格式化数值，处理None值"""
        if value is None:
            return "N/A"
        if isinstance(value, (int, float)):
            if decimal_places == 0:
                return f"{int(value):,}"
            return f"{value:,.{decimal_places}f}"
        return str(value)

    def format_time(seconds):
        """格式化时间显示"""
        if seconds is None:
            return "N/A"
        if seconds >= 60:
            minutes = seconds / 60
            return f"{minutes:.2f} min"
        return f"{seconds:.2f} sec"

    def get_performance_color(value, metric_type='general'):
        """根据性能值返回对应的颜色"""
        if value == 'N/A' or value is None:
            return '#9e9e9e'

        val = float(str(value).replace('%', '')) if isinstance(value, str) else value

        if metric_type == 'precision' or metric_type == 'recall' or metric_type == 'f1':
            if val >= 90:
                return '#00c853'  # 优秀 - 绿色
            elif val >= 75:
                return '#64b5f6'  # 良好 - 蓝色
            elif val >= 60:
                return '#ffb300'  # 一般 - 橙色
            else:
                return '#e53935'  # 需改进 - 红色
        return '#1976d2'  # 默认蓝色

    def prepare_evaluation_info(report):
        """准备评估基本信息"""
        return {
            'start_at': report.start_at if report.start_at else 'N/A',
            'finished_at': report.finished_at if report.finished_at else 'N/A',
        }

    def prepare_evaluation_config(config):
        """准备评估配置信息"""
        if config is None:
            return {
                'benchmark_file': 'N/A',
                'test_case_dir': 'N/A',
                'llm_provider': 'N/A',
                'llm_model_id': 'N/A',
                'input_token_price_per_1M': 'N/A',
                'output_token_price_per_1M': 'N/A',
                'concurrency': 'N/A',
                'slice_start': 'N/A',
                'slice_end': 'N/A'
            }

        return {
            'benchmark_file': config.benchmark_file,
            'test_case_dir': config.test_case_dir,
            'llm_provider': config.llm_provider,
            'llm_model_id': config.llm_model_id,
            'input_token_price_per_1M': f"${config.input_token_price_per_1M:.2f}",
            'output_token_price_per_1M': f"${config.output_token_price_per_1M:.2f}",
            'concurrency': str(config.concurrency),
            'slice_start': str(config.slice_start),
            'slice_end': str(config.slice_end) if config.slice_end != -1 else 'End'
        }

    def prepare_benchmark_meta(benchmark):
        """准备benchmark元数据"""
        if benchmark is None:
            return {
                'name': 'N/A',
                'test_case_num': 'N/A',
                'covered_library_num': 'N/A',
                'version': 'N/A'
            }

        meta = benchmark.get_meta()
        return {
            'name': meta.name,
            'test_case_num': f"{meta.test_case_num:,}" if meta.test_case_num else 'N/A',
            'covered_library_num': f"{meta.covered_library_num:,}" if meta.covered_library_num else 'N/A',
            'version': meta.version
        }

    def prepare_effectiveness_data(eff_data):
        """准备效果数据"""
        if eff_data is None:
            return {
                'tp_count': 'N/A', 'fp_count': 'N/A', 'fn_count': 'N/A',
                'precision': 'N/A', 'recall': 'N/A', 'f1_score': 'N/A'
            }

        return {
            'tp_count': safe_format(eff_data.tp_count, 0),
            'fp_count': safe_format(eff_data.fp_count, 0),
            'fn_count': safe_format(eff_data.fn_count, 0),
            'precision': safe_format(eff_data.precision),
            'recall': safe_format(eff_data.recall),
            'f1_score': safe_format(eff_data.f1_score)
        }

    def prepare_ablation_data(ablation_data, effectiveness_data):
        """准备消融实验数据"""
        if ablation_data is None:
            return {
                'configurations': [],
                'precision_data': [],
                'recall_data': [],
                'f1_data': []
            }

        configurations = [
            ('Complete System', effectiveness_data),
            ('w/o Agent Analysis', ablation_data.wo_agent_analysis),
            ('w/o Agent Analysis (Top-1)', ablation_data.wo_agent_analysis_top_1),
            ('w/o Agent Analysis (Top-2)', ablation_data.wo_agent_analysis_top_2),
            ('w/o Agent Analysis (Top-3)', ablation_data.wo_agent_analysis_top_3),
            ('w/o Agent TPL Analysis', ablation_data.wo_agent_tpl_analysis),
            ('w/o Validation Step 1', ablation_data.wo_validation_step_1),
            ('w/o Validation Step 2', ablation_data.wo_validation_step_2),
            ('w/o All Validation', ablation_data.wo_validation_step_1_and_2)
        ]

        config_names = []
        precision_data = []
        recall_data = []
        f1_data = []

        for name, eff_data in configurations:
            if eff_data is not None:
                config_names.append(name)
                precision_data.append(eff_data.precision if eff_data.precision is not None else 0)
                recall_data.append(eff_data.recall if eff_data.recall is not None else 0)
                f1_data.append(eff_data.f1_score if eff_data.f1_score is not None else 0)

        return {
            'configurations': config_names,
            'precision_data': precision_data,
            'recall_data': recall_data,
            'f1_data': f1_data
        }

    def prepare_efficiency_data(eff_data):
        """准备效率数据"""
        if eff_data is None:
            return {
                'file_stats': {'total': 'N/A', 'average': 'N/A'},
                'time_stats': {'total_theoretical': 'N/A', 'average_theoretical': 'N/A',
                               'total_actual': 'N/A', 'average_actual': 'N/A'},
                'duration_breakdown': {'top_level': {}, 'sub_level': {}, 'subsub_level': {}}
            }

        # 用于多层展示的数据结构
        top_level_data = {}
        sub_level_data = {}
        subsub_level_data = {}

        if eff_data.duration_breakdown:
            # 创建标签映射，使名称更友好
            label_mapping = {
                'file_preparation': 'File Preparation',
                'feature_matching': 'Feature Matching',
                '_bin_info_finder': 'Binary Info Finder',
                '_tpl_analyzer': 'TPL Analyzer',
                '__validation_enhance': 'Validation Enhancement',
                '__validation_step_1': 'Validation Step 1',
                '__validation_step_2': 'Validation Step 2',
                '_library_validation': 'Library Validation',
                'agent_analysis': 'Agent Analysis'
            }

            # 分类处理不同层级的数据
            for key, value in eff_data.duration_breakdown.items():
                if key == 'total':
                    continue

                # 处理tuple格式的数据
                if isinstance(value, (list, tuple)) and len(value) >= 2:
                    actual_value = value[1]
                else:
                    actual_value = value if isinstance(value, (int, float)) else 0

                friendly_label = label_mapping.get(key, key)

                # 保证 value 是 float/int 类型，不用 safe_format
                if key.startswith('__'):  # 二级子阶段 (library_validation的子阶段)
                    subsub_level_data[friendly_label] = actual_value
                elif key.startswith('_'):  # 一级子阶段 (agent_analysis的子阶段)
                    sub_level_data[friendly_label] = actual_value
                else:  # 顶级阶段
                    top_level_data[friendly_label] = actual_value

        return {
            'file_stats': {
                'total': safe_format(eff_data.total_file_size_kb),
                'average': safe_format(eff_data.average_file_size_kb)
            },
            'time_stats': {
                'total_theoretical': format_time(eff_data.total_theoretical_duration),
                'average_theoretical': format_time(eff_data.average_theoretical_duration),
                'total_actual': format_time(eff_data.total_actual_duration),
                'average_actual': format_time(eff_data.average_actual_duration)
            },
            'duration_breakdown': {
                'top_level': top_level_data,
                'sub_level': sub_level_data,
                'subsub_level': subsub_level_data
            }
        }

    def prepare_cost_data(cost_data):
        """准备成本数据"""
        if cost_data is None:
            return {
                'token_stats': {'input': 'N/A', 'output': 'N/A', 'total': 'N/A'},
                'cost_stats': {'total': 'N/A', 'average': 'N/A'}
            }

        return {
            'token_stats': {
                'input': f"{int(cost_data.input_token_count):,}" if cost_data.input_token_count is not None else "N/A",
                'output': f"{int(cost_data.output_token_count):,}" if cost_data.output_token_count is not None else "N/A",
                'total': f"{int(cost_data.total_token_count):,}" if cost_data.total_token_count is not None else "N/A"
            },
            'cost_stats': {
                'total': f"${safe_format(cost_data.total_cost)}" if cost_data.total_cost is not None else "N/A",
                'average': f"${safe_format(cost_data.average_cost)}" if cost_data.average_cost is not None else "N/A"
            }
        }

    # 准备数据
    evaluation_info = prepare_evaluation_info(report)
    evaluation_config = prepare_evaluation_config(report.evaluation_config)
    benchmark_meta = prepare_benchmark_meta(report.benchmark)

    # 从 report.research_question_data 获取分析数据
    data = report.research_question_data
    effectiveness_data = prepare_effectiveness_data(data.effectiveness)
    ablation_data = prepare_ablation_data(data.effectiveness_ablation_study, data.effectiveness)
    efficiency_data = prepare_efficiency_data(data.efficiency)
    cost_data = prepare_cost_data(data.cost)

    # 生成优化后的HTML内容
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Evaluation Analysis Report - {benchmark_meta['name']}</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root {{
            /* 主色调 */
            --primary: #5e35b1;
            --primary-light: #7e57c2;
            --primary-dark: #4527a0;

            /* 语义色彩 */
            --success: #00c853;
            --warning: #ffb300;
            --danger: #e53935;
            --info: #00acc1;

            /* 中性色 */
            --gray-50: #fafafa;
            --gray-100: #f5f5f5;
            --gray-200: #eeeeee;
            --gray-300: #e0e0e0;
            --gray-400: #bdbdbd;
            --gray-500: #9e9e9e;
            --gray-600: #757575;
            --gray-700: #616161;
            --gray-800: #424242;
            --gray-900: #212121;

            /* 阴影 */
            --shadow-sm: 0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24);
            --shadow-md: 0 3px 6px rgba(0,0,0,0.15), 0 2px 4px rgba(0,0,0,0.12);
            --shadow-lg: 0 10px 20px rgba(0,0,0,0.15), 0 3px 6px rgba(0,0,0,0.10);
            --shadow-xl: 0 15px 25px rgba(0,0,0,0.15), 0 5px 10px rgba(0,0,0,0.05);

            /* 动画 */
            --transition-fast: 0.15s ease;
            --transition-base: 0.3s ease;
            --transition-slow: 0.5s ease;
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: var(--gray-50);
            color: var(--gray-900);
            line-height: 1.6;
            overflow-x: hidden;
        }}

        /* 导航栏 */
        .navbar {{
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            height: 64px;
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            box-shadow: var(--shadow-sm);
            z-index: 1000;
            display: flex;
            align-items: center;
            padding: 0 24px;
        }}

        .navbar-brand {{
            font-size: 1.25rem;
            font-weight: 600;
            color: var(--primary);
            display: flex;
            align-items: center;
            gap: 12px;
        }}

        .navbar-brand i {{
            font-size: 1.5rem;
        }}

        /* 侧边导航 */
        .sidenav {{
            position: fixed;
            left: 0;
            top: 64px;
            bottom: 0;
            width: 240px;
            background: white;
            border-right: 1px solid var(--gray-200);
            padding: 24px 0;
            overflow-y: auto;
        }}

        .sidenav-item {{
            display: block;
            padding: 12px 24px;
            color: var(--gray-700);
            text-decoration: none;
            transition: all var(--transition-fast);
            border-left: 3px solid transparent;
            font-size: 0.875rem;
        }}

        .sidenav-item:hover {{
            background: var(--gray-50);
            color: var(--primary);
            border-left-color: var(--primary);
        }}

        .sidenav-item.active {{
            background: rgba(94, 53, 177, 0.08);
            color: var(--primary);
            border-left-color: var(--primary);
            font-weight: 500;
        }}

        /* 主内容区 */
        .main-content {{
            margin-left: 240px;
            margin-top: 64px;
            padding: 32px;
            min-height: calc(100vh - 64px);
        }}

        /* 英雄区域 - 关键指标总览 */
        .hero-section {{
            background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
            color: white;
            padding: 48px;
            border-radius: 16px;
            margin-bottom: 32px;
            position: relative;
            overflow: hidden;
        }}

        .hero-section::before {{
            content: '';
            position: absolute;
            top: -50%;
            right: -10%;
            width: 50%;
            height: 200%;
            background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
            animation: float 20s ease-in-out infinite;
        }}

        @keyframes float {{
            0%, 100% {{ transform: translateY(0) rotate(0deg); }}
            50% {{ transform: translateY(-20px) rotate(180deg); }}
        }}

        .hero-title {{
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 16px;
            position: relative;
            z-index: 1;
        }}

        .hero-subtitle {{
            font-size: 1.125rem;
            opacity: 0.9;
            margin-bottom: 40px;
            position: relative;
            z-index: 1;
        }}

        .hero-metrics {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 24px;
            position: relative;
            z-index: 1;
        }}

        .hero-metric {{
            background: rgba(255, 255, 255, 0.15);
            backdrop-filter: blur(10px);
            padding: 24px;
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.2);
            transition: all var(--transition-base);
        }}

        .hero-metric:hover {{
            background: rgba(255, 255, 255, 0.25);
            transform: translateY(-4px);
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
        }}

        .hero-metric-label {{
            font-size: 0.875rem;
            opacity: 0.9;
            margin-bottom: 8px;
            font-weight: 500;
        }}

        .hero-metric-value {{
            font-size: 2rem;
            font-weight: 700;
            display: flex;
            align-items: baseline;
            gap: 8px;
        }}

        .hero-metric-unit {{
            font-size: 1rem;
            font-weight: 400;
            opacity: 0.8;
        }}

        .hero-metric-trend {{
            font-size: 0.75rem;
            margin-top: 4px;
            display: flex;
            align-items: center;
            gap: 4px;
        }}

        .trend-up {{ color: #69f0ae; }}
        .trend-down {{ color: #ff5252; }}

        /* 卡片样式 */
        .card {{
            background: white;
            border-radius: 12px;
            box-shadow: var(--shadow-sm);
            margin-bottom: 24px;
            transition: all var(--transition-base);
            overflow: hidden;
        }}

        .card:hover {{
            box-shadow: var(--shadow-md);
        }}

        .card-header {{
            padding: 24px;
            border-bottom: 1px solid var(--gray-100);
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}

        .card-title {{
            font-size: 1.25rem;
            font-weight: 600;
            color: var(--gray-900);
            display: flex;
            align-items: center;
            gap: 12px;
        }}

        .card-title i {{
            color: var(--primary);
            font-size: 1.5rem;
        }}

        .card-body {{
            padding: 24px;
        }}

        /* 指标卡片网格 */
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 16px;
        }}

        .metric-card {{
            background: var(--gray-50);
            padding: 24px;
            border-radius: 8px;
            text-align: center;
            transition: all var(--transition-base);
            border: 2px solid transparent;
            position: relative;
            overflow: hidden;
        }}

        .metric-card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: var(--primary);
            transform: scaleX(0);
            transition: transform var(--transition-base);
        }}

        .metric-card:hover {{
            transform: translateY(-4px);
            border-color: var(--primary);
            box-shadow: var(--shadow-md);
        }}

        .metric-card:hover::before {{
            transform: scaleX(1);
        }}

        .metric-label {{
            font-size: 0.75rem;
            color: var(--gray-600);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
            font-weight: 600;
        }}

        .metric-value {{
            font-size: 2rem;
            font-weight: 700;
            margin-bottom: 4px;
            font-variant-numeric: tabular-nums;
        }}

        .metric-value.large {{
            font-size: 2.5rem;
        }}

        /* 性能指标颜色 */
        .metric-excellent {{ color: var(--success); }}
        .metric-good {{ color: var(--info); }}
        .metric-average {{ color: var(--warning); }}
        .metric-poor {{ color: var(--danger); }}

        /* 表格样式 */
        .data-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.875rem;
        }}

        .data-table th,
        .data-table td {{
            padding: 12px 16px;
            text-align: left;
            border-bottom: 1px solid var(--gray-200);
        }}

        .data-table th {{
            background: var(--gray-50);
            font-weight: 600;
            color: var(--gray-700);
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .data-table tr:hover td {{
            background: var(--gray-50);
        }}

        .data-table td {{
            color: var(--gray-800);
        }}

        /* 图表容器 */
        .chart-container {{
            position: relative;
            height: 300px;
            margin-top: 24px;
        }}

        .chart-container.large {{
            height: 400px;
        }}

        /* 标签样式 */
        .tag {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 500;
            margin-right: 8px;
        }}

        .tag-primary {{
            background: rgba(94, 53, 177, 0.1);
            color: var(--primary);
        }}

        .tag-success {{
            background: rgba(0, 200, 83, 0.1);
            color: var(--success);
        }}

        /* 进度条 */
        .progress-bar {{
            height: 8px;
            background: var(--gray-200);
            border-radius: 4px;
            overflow: hidden;
            margin: 8px 0;
        }}

        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, var(--primary) 0%, var(--primary-light) 100%);
            border-radius: 4px;
            transition: width var(--transition-slow);
        }}

        /* 详细信息展开/折叠 */
        .collapsible {{
            cursor: pointer;
            user-select: none;
        }}

        .collapsible-icon {{
            transition: transform var(--transition-fast);
        }}

        .collapsible.expanded .collapsible-icon {{
            transform: rotate(90deg);
        }}

        .collapsible-content {{
            max-height: 0;
            overflow: hidden;
            transition: max-height var(--transition-base);
        }}

        .collapsible-content.expanded {{
            max-height: 1000px;
        }}

        /* 响应式设计 */
        @media (max-width: 1024px) {{
            .sidenav {{
                transform: translateX(-100%);
                transition: transform var(--transition-base);
            }}

            .sidenav.show {{
                transform: translateX(0);
            }}

            .main-content {{
                margin-left: 0;
            }}

            .hero-title {{
                font-size: 2rem;
            }}
        }}

        @media (max-width: 768px) {{
            .hero-section {{
                padding: 32px 24px;
            }}

            .main-content {{
                padding: 16px;
            }}

            .hero-metrics {{
                grid-template-columns: 1fr;
            }}

            .metrics-grid {{
                grid-template-columns: 1fr;
            }}
        }}

        /* 加载动画 */
        @keyframes pulse {{
            0% {{ opacity: 0.6; }}
            50% {{ opacity: 1; }}
            100% {{ opacity: 0.6; }}
        }}

        .skeleton {{
            background: var(--gray-200);
            border-radius: 4px;
            animation: pulse 1.5s ease-in-out infinite;
        }}

        /* 图表自定义样式 */
        .chart-legend {{
            display: flex;
            justify-content: center;
            gap: 24px;
            margin-top: 16px;
            flex-wrap: wrap;
        }}

        .legend-item {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 0.875rem;
            color: var(--gray-700);
        }}

        .legend-color {{
            width: 16px;
            height: 16px;
            border-radius: 4px;
        }}

        /* 时间线样式 */
        .timeline {{
            position: relative;
            padding-left: 32px;
        }}

        .timeline::before {{
            content: '';
            position: absolute;
            left: 8px;
            top: 0;
            bottom: 0;
            width: 2px;
            background: var(--gray-300);
        }}

        .timeline-item {{
            position: relative;
            padding-bottom: 24px;
        }}

        .timeline-item::before {{
            content: '';
            position: absolute;
            left: -28px;
            top: 4px;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: var(--primary);
            border: 3px solid white;
            box-shadow: var(--shadow-sm);
        }}

        .timeline-content {{
            background: var(--gray-50);
            padding: 16px;
            border-radius: 8px;
        }}

        /* 仪表盘样式 */
        .gauge-container {{
            position: relative;
            width: 120px;
            height: 120px;
            margin: 0 auto;
        }}

        .gauge-value {{
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            font-size: 1.5rem;
            font-weight: 700;
        }}
    </style>
</head>
<body>
    <!-- 导航栏 -->
    <nav class="navbar">
        <div class="navbar-brand">
            <i class="fas fa-chart-line"></i>
            <span>Evaluation Analysis Report</span>
        </div>
    </nav>

    <!-- 侧边导航 -->
    <aside class="sidenav" id="sidenav">
        <a href="#overview" class="sidenav-item active">
            <i class="fas fa-home"></i> Overview
        </a>
        <a href="#effectiveness" class="sidenav-item">
            <i class="fas fa-check-circle"></i> Effectiveness
        </a>
        <a href="#ablation" class="sidenav-item">
            <i class="fas fa-flask"></i> Ablation Study
        </a>
        <a href="#efficiency" class="sidenav-item">
            <i class="fas fa-tachometer-alt"></i> Efficiency
        </a>
        <a href="#cost" class="sidenav-item">
            <i class="fas fa-dollar-sign"></i> Cost Analysis
        </a>
    </aside>

    <!-- 主内容区 -->
    <main class="main-content">
        <!-- 英雄区域 - 关键指标总览 -->
        <section class="hero-section" id="overview">
            <h1 class="hero-title">{benchmark_meta["name"]} Evaluation Results</h1>
            <p class="hero-subtitle">Comprehensive analysis of SCA tool performance</p>

            <div class="hero-metrics">
                <div class="hero-metric">
                    <div class="hero-metric-label">Overall Performance</div>
                    <div class="hero-metric-value">
                        {effectiveness_data["f1_score"]}<span class="hero-metric-unit">%</span>
                    </div>
                    <div class="hero-metric-trend">
                        <i class="fas fa-chart-line"></i> F1-Score
                    </div>
                </div>

                <div class="hero-metric">
                    <div class="hero-metric-label">Detection Accuracy</div>
                    <div class="hero-metric-value">
                        {effectiveness_data["precision"]}<span class="hero-metric-unit">%</span>
                    </div>
                    <div class="hero-metric-trend">
                        <i class="fas fa-bullseye"></i> Precision
                    </div>
                </div>

                <div class="hero-metric">
                    <div class="hero-metric-label">Coverage Rate</div>
                    <div class="hero-metric-value">
                        {effectiveness_data["recall"]}<span class="hero-metric-unit">%</span>
                    </div>
                    <div class="hero-metric-trend">
                        <i class="fas fa-expand"></i> Recall
                    </div>
                </div>

                <div class="hero-metric">
                    <div class="hero-metric-label">Analysis Cost</div>
                    <div class="hero-metric-value">
                        {cost_data['cost_stats']['average']}<span class="hero-metric-unit">$/file</span>
                    </div>
                    <div class="hero-metric-trend">
                        <i class="fas fa-coins"></i> Per Analysis
                    </div>
                </div>
            </div>
        </section>

        <!-- 评估配置信息 -->
        <section class="card">
            <div class="card-header">
                <h2 class="card-title">
                    <i class="fas fa-cog"></i>
                    Evaluation Configuration
                </h2>
            </div>
            <div class="card-body">
                <div class="metrics-grid">
                    <div class="metric-card">
                        <div class="metric-label">Test Cases</div>
                        <div class="metric-value">{benchmark_meta['test_case_num']}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Libraries Covered</div>
                        <div class="metric-value">{benchmark_meta['covered_library_num']}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">LLM Model</div>
                        <div class="metric-value" style="font-size: 1rem;">{evaluation_config['llm_model_id']}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Concurrency</div>
                        <div class="metric-value">{evaluation_config['concurrency']}</div>
                    </div>
                </div>

                <div class="collapsible" onclick="toggleCollapsible(this)" style="margin-top: 24px; cursor: pointer;">
                    <h3 style="display: flex; align-items: center; gap: 8px; color: var(--primary);">
                        <i class="fas fa-chevron-right collapsible-icon"></i>
                        View Configuration Detail
                    </h3>
                </div>
                <div class="collapsible-content">
                    <table class="data-table" style="margin-top: 16px;">
                        <tr>
                            <th>Parameter</th>
                            <th>Value</th>
                        </tr>
                        <!-- Benchmark 相关配置 -->
                        <tr style="background: var(--gray-50);">
                            <td colspan="2" style="font-weight: 600; color: var(--primary); padding: 8px 16px; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.5px;">Benchmark Configuration</td>
                        </tr>
                        <tr>
                            <td>Benchmark File</td>
                            <td><code style="background: var(--gray-100); padding: 2px 8px; border-radius: 4px;">{evaluation_config['benchmark_file']}</code></td>
                        </tr>
                        <tr>
                            <td>Test Case Directory</td>
                            <td><code style="background: var(--gray-100); padding: 2px 8px; border-radius: 4px;">{evaluation_config['test_case_dir']}</code></td>
                        </tr>
                        <tr>
                            <td>Test Cases</td>
                            <td>{benchmark_meta['test_case_num']}</td>
                        </tr>
                        <tr>
                            <td>Libraries Covered</td>
                            <td>{benchmark_meta['covered_library_num']}</td>
                        </tr>
                        <!-- 模型相关配置 -->
                        <tr style="background: var(--gray-50);">
                            <td colspan="2" style="font-weight: 600; color: var(--primary); padding: 8px 16px; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.5px;">Model Configuration</td>
                        </tr>
                        <tr>
                            <td>LLM Provider</td>
                            <td>{evaluation_config['llm_provider']}</td>
                        </tr>
                        <tr>
                            <td>LLM Model</td>
                            <td>{evaluation_config['llm_model_id']}</td>
                        </tr>
                        <tr>
                            <td>Input Token Price</td>
                            <td>{evaluation_config['input_token_price_per_1M']} per 1M tokens</td>
                        </tr>
                        <tr>
                            <td>Output Token Price</td>
                            <td>{evaluation_config['output_token_price_per_1M']} per 1M tokens</td>
                        </tr>
                        <!-- 运行配置 -->
                        <tr style="background: var(--gray-50);">
                            <td colspan="2" style="font-weight: 600; color: var(--primary); padding: 8px 16px; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.5px;">Runtime Configuration</td>
                        </tr>
                        <tr>
                            <td>Concurrency</td>
                            <td>{evaluation_config['concurrency']}</td>
                        </tr>
                        <tr>
                            <td>Test Range</td>
                            <td>{evaluation_config['slice_start']} - {evaluation_config['slice_end']}</td>
                        </tr>
                        <tr>
                            <td>Start Time</td>
                            <td>{evaluation_info['start_at']}</td>
                        </tr>
                        <tr>
                            <td>Finish Time</td>
                            <td>{evaluation_info['finished_at']}</td>
                        </tr>
                    </table>
                </div>
            </div>
        </section>

        <!-- 效果分析 -->
        <section class="card" id="effectiveness">
            <div class="card-header">
                <h2 class="card-title">
                    <i class="fas fa-check-circle"></i>
                    Effectiveness Analysis
                </h2>
            </div>
            <div class="card-body">
                <div class="metrics-grid">
                    <div class="metric-card">
                        <div class="metric-label">True Positives</div>
                        <div class="metric-value metric-excellent">{effectiveness_data['tp_count']}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">False Positives</div>
                        <div class="metric-value metric-average">{effectiveness_data['fp_count']}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">False Negatives</div>
                        <div class="metric-value metric-poor">{effectiveness_data['fn_count']}</div>
                    </div>
                </div>

                <div class="chart-container" style="margin-top: 32px;">
                    <canvas id="effectivenessRadar"></canvas>
                </div>
            </div>
        </section>

        <!-- 消融实验 -->
        <section class="card" id="ablation">
            <div class="card-header">
                <h2 class="card-title">
                    <i class="fas fa-flask"></i>
                    Ablation Study
                </h2>
            </div>
            <div class="card-body">
                <div class="chart-container large">
                    <canvas id="ablationChart"></canvas>
                </div>
                <div class="chart-legend" style="margin-top: 24px;">
                    <!-- 完整实验组 -->
                    <div style="margin-bottom: 16px;">
                        <h4 style="color: var(--gray-700); margin-bottom: 8px; font-size: 0.875rem; font-weight: 600;">Complete System</h4>
                        <div class="legend-item">
                            <div class="legend-color" style="background: #1f77b4;"></div>
                            <span>Complete System</span>
                        </div>
                    </div>
                    
                    <!-- Agent Analysis消融组 -->
                    <div style="margin-bottom: 16px;">
                        <h4 style="color: var(--gray-700); margin-bottom: 8px; font-size: 0.875rem; font-weight: 600;">Agent Analysis Ablation</h4>
                        <div class="legend-item">
                            <div class="legend-color" style="background: #d62728;"></div>
                            <span>w/o Agent Analysis</span>
                        </div>
                        <div class="legend-item">
                            <div class="legend-color" style="background: #e74c3c;"></div>
                            <span>w/o Agent Analysis (Top-1)</span>
                        </div>
                        <div class="legend-item">
                            <div class="legend-color" style="background: #f39c12;"></div>
                            <span>w/o Agent Analysis (Top-2)</span>
                        </div>
                        <div class="legend-item">
                            <div class="legend-color" style="background: #e67e22;"></div>
                            <span>w/o Agent Analysis (Top-3)</span>
                        </div>
                    </div>
                    
                    <!-- TPL Analysis消融组 -->
                    <div style="margin-bottom: 16px;">
                        <h4 style="color: var(--gray-700); margin-bottom: 8px; font-size: 0.875rem; font-weight: 600;">TPL Analysis Ablation</h4>
                        <div class="legend-item">
                            <div class="legend-color" style="background: #2ecc71;"></div>
                            <span>w/o Agent TPL Analysis</span>
                        </div>
                    </div>
                    
                    <!-- 验证消融组 -->
                    <div style="margin-bottom: 16px;">
                        <h4 style="color: var(--gray-700); margin-bottom: 8px; font-size: 0.875rem; font-weight: 600;">Validation Ablation</h4>
                        <div class="legend-item">
                            <div class="legend-color" style="background: #7d3c98;"></div>
                            <span>w/o All Validation</span>
                        </div>
                        <div class="legend-item">
                            <div class="legend-color" style="background: #8e44ad;"></div>
                            <span>w/o Validation Step 1</span>
                        </div>
                        <div class="legend-item">
                            <div class="legend-color" style="background: #9b59b6;"></div>
                            <span>w/o Validation Step 2</span>
                        </div>
                    </div>
                </div>
            </div>
        </section>

        <!-- 效率分析 -->
        <section class="card" id="efficiency">
            <div class="card-header">
                <h2 class="card-title">
                    <i class="fas fa-tachometer-alt"></i>
                    Efficiency Analysis
                </h2>
            </div>
            <div class="card-body">
                <div class="metrics-grid">
                    <div class="metric-card">
                        <div class="metric-label">Total File Size</div>
                        <div class="metric-value">{efficiency_data['file_stats']['total']}</div>
                        <div style="font-size: 0.75rem; color: var(--gray-600);">KB</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Avg File Size</div>
                        <div class="metric-value">{efficiency_data['file_stats']['average']}</div>
                        <div style="font-size: 0.75rem; color: var(--gray-600);">KB</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Avg Theoretical Time</div>
                        <div class="metric-value">{efficiency_data['time_stats']['average_theoretical']}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Avg Actual Time</div>
                        <div class="metric-value">{efficiency_data['time_stats']['average_actual']}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Total Theoretical Duration</div>
                        <div class="metric-value">{efficiency_data['time_stats']['total_theoretical']}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Total Actual Duration</div>
                        <div class="metric-value">{efficiency_data['time_stats']['total_actual']}</div>
                    </div>
                </div>

                <h3 style="margin-top: 32px; margin-bottom: 16px; color: var(--gray-800);">
                    <i class="fas fa-clock"></i> Time Breakdown Analysis
                </h3>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 24px;">
                    <div class="chart-container">
                        <canvas id="mainStagesChart"></canvas>
                    </div>
                    <div class="chart-container">
                        <canvas id="agentStagesChart"></canvas>
                    </div>
                    <div class="chart-container">
                        <canvas id="validationStagesChart"></canvas>
                    </div>
                </div>
            </div>
        </section>

        <!-- 成本分析 -->
        <section class="card" id="cost">
            <div class="card-header">
                <h2 class="card-title">
                    <i class="fas fa-dollar-sign"></i>
                    Cost Analysis
                </h2>
            </div>
            <div class="card-body">
                <div class="metrics-grid">
                    <div class="metric-card">
                        <div class="metric-label">Total Cost</div>
                        <div class="metric-value large">{cost_data['cost_stats']['total']}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Average Cost</div>
                        <div class="metric-value">{cost_data['cost_stats']['average']}</div>
                        <div style="font-size: 0.75rem; color: var(--gray-600);">per analysis</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Input Tokens</div>
                        <div class="metric-value">{cost_data['token_stats']['input']}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Output Tokens</div>
                        <div class="metric-value">{cost_data['token_stats']['output']}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Total Tokens</div>
                        <div class="metric-value">{cost_data['token_stats']['total']}</div>
                    </div>
                </div>

                <div class="chart-container" style="margin-top: 32px;">
                    <canvas id="tokenDistribution"></canvas>
                </div>
            </div>
        </section>
    </main>

    <script>
        // 配色方案
        const colors = {{
            primary: '#5e35b1',
            primaryLight: '#7e57c2',
            primaryDark: '#4527a0',
            success: '#00c853',
            warning: '#ffb300',
            danger: '#e53935',
            info: '#00acc1',
            gray: '#9e9e9e'
        }};

        // Chart.js 默认配置
        Chart.defaults.font.family = "'Inter', -apple-system, BlinkMacSystemFont, sans-serif";
        Chart.defaults.font.size = 12;
        Chart.defaults.color = '#424242';

        // 1. 效果雷达图
        const effectivenessRadarCtx = document.getElementById('effectivenessRadar').getContext('2d');
        new Chart(effectivenessRadarCtx, {{
            type: 'radar',
            data: {{
                labels: ['Precision', 'Recall', 'F1-Score'],
                datasets: [{{
                    label: 'Performance Metrics',
                    data: [
                        {effectiveness_data['precision'].replace('%', '') if effectiveness_data['precision'] != 'N/A' else 0},
                        {effectiveness_data['recall'].replace('%', '') if effectiveness_data['recall'] != 'N/A' else 0},
                        {effectiveness_data['f1_score'].replace('%', '') if effectiveness_data['f1_score'] != 'N/A' else 0}
                    ],
                    backgroundColor: 'rgba(94, 53, 177, 0.2)',
                    borderColor: colors.primary,
                    borderWidth: 2,
                    pointBackgroundColor: colors.primary,
                    pointBorderColor: '#fff',
                    pointHoverBackgroundColor: '#fff',
                    pointHoverBorderColor: colors.primary
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        display: false
                    }}
                }},
                scales: {{
                    r: {{
                        beginAtZero: true,
                        max: 100,
                        ticks: {{
                            callback: function(value) {{
                                return value + '%';
                            }}
                        }}
                    }}
                }}
            }}
        }});

        // 2. 消融实验对比图 - 修改为指标分组显示
        const ablationCtx = document.getElementById('ablationChart').getContext('2d');
        const configurations = {json.dumps(ablation_data["configurations"])};
        const precisionData = {json.dumps(ablation_data["precision_data"])};
        const recallData = {json.dumps(ablation_data["recall_data"])};
        const f1Data = {json.dumps(ablation_data["f1_data"])};

        // 重新组织数据：将指标作为分组，消融方式作为数据集
        const metrics = ['F1-Score', 'Recall', 'Precision'];
        const datasets = [];
        
                            // 定义期望的顺序和对应的颜色
        const expectedOrder = [
            'Complete System',
            'w/o Agent Analysis',
            'w/o Agent Analysis (Top-1)',
            'w/o Agent Analysis (Top-2)',
            'w/o Agent Analysis (Top-3)',
            'w/o Agent TPL Analysis',
            'w/o All Validation',
            'w/o Validation Step 1',
            'w/o Validation Step 2'
        ];
        
        const colorMapping = {{
            'Complete System': '#1f77b4',
            'w/o Agent Analysis': '#d62728',
            'w/o Agent Analysis (Top-1)': '#e74c3c',
            'w/o Agent Analysis (Top-2)': '#f39c12',
            'w/o Agent Analysis (Top-3)': '#e67e22',
            'w/o Agent TPL Analysis': '#2ecc71',
            'w/o All Validation': '#7d3c98',
            'w/o Validation Step 1': '#8e44ad',
            'w/o Validation Step 2': '#9b59b6'
        }};
        
        // 按照期望的顺序创建数据集
        expectedOrder.forEach(configName => {{
            const index = configurations.indexOf(configName);
            if (index !== -1) {{
                const data = [f1Data[index], recallData[index], precisionData[index]];
                const selectedColor = colorMapping[configName];
                
                datasets.push({{
                    label: configName,
                    data: data,
                    backgroundColor: selectedColor,
                    borderColor: selectedColor,
                    borderWidth: 1
                }});
            }}
        }});

        new Chart(ablationCtx, {{
            type: 'bar',
            data: {{
                labels: metrics,
                datasets: datasets
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        display: false // 关闭默认图例，只使用下面的自定义图例
                    }},
                    tooltip: {{
                        callbacks: {{
                            label: function(context) {{
                                return context.dataset.label + ': ' + context.parsed.y.toFixed(2) + '%';
                            }}
                        }}
                    }}
                }},
                scales: {{
                    x: {{
                        title: {{
                            display: true,
                            text: 'Metrics',
                            font: {{
                                size: 14,
                                weight: '600'
                            }}
                        }}
                    }},
                    y: {{
                        beginAtZero: true,
                        max: 100,
                        title: {{
                            display: true,
                            text: 'Performance (%)',
                            font: {{
                                size: 14,
                                weight: '600'
                            }}
                        }},
                        ticks: {{
                            callback: function(value) {{
                                return value + '%';
                            }}
                        }}
                    }}
                }}
            }}
        }});

        // 3. 时间分布饼图 - 三层展示
        const topLevelData = {json.dumps(efficiency_data["duration_breakdown"]["top_level"])};
        const subLevelData = {json.dumps(efficiency_data["duration_breakdown"]["sub_level"])};
        const subsubLevelData = {json.dumps(efficiency_data["duration_breakdown"]["subsub_level"])};

        // 主阶段图表
        const mainStagesCtx = document.getElementById('mainStagesChart').getContext('2d');
        const mainLabels = Object.keys(topLevelData);
        const mainValues = Object.values(topLevelData);

        if (mainLabels.length > 0) {{
            new Chart(mainStagesCtx, {{
                type: 'doughnut',
                data: {{
                    labels: mainLabels,
                    datasets: [{{
                        data: mainValues,
                        backgroundColor: [
                            colors.primary,
                            colors.info,
                            colors.warning,
                            colors.success,
                            colors.danger
                        ],
                        borderColor: '#fff',
                        borderWidth: 2
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        title: {{
                            display: true,
                            text: 'Main Processing Stages',
                            font: {{
                                size: 14,
                                weight: '600'
                            }}
                        }},
                        legend: {{
                            position: 'bottom',
                            labels: {{
                                padding: 12,
                                usePointStyle: true
                            }}
                        }}
                    }}
                }}
            }});
        }}

        // Agent Analysis子阶段图表
        const agentStagesCtx = document.getElementById('agentStagesChart').getContext('2d');
        const agentLabels = Object.keys(subLevelData);
        const agentValues = Object.values(subLevelData);

        if (agentLabels.length > 0) {{
            new Chart(agentStagesCtx, {{
                type: 'doughnut',
                data: {{
                    labels: agentLabels,
                    datasets: [{{
                        data: agentValues,
                        backgroundColor: [
                            colors.primaryLight,
                            colors.primary,
                            colors.primaryDark,
                            '#8e24aa',
                            '#6a1b9a'
                        ],
                        borderColor: '#fff',
                        borderWidth: 2
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        title: {{
                            display: true,
                            text: 'Agent Analysis Breakdown',
                            font: {{
                                size: 14,
                                weight: '600'
                            }}
                        }},
                        legend: {{
                            position: 'bottom',
                            labels: {{
                                padding: 12,
                                usePointStyle: true
                            }}
                        }}
                    }}
                }}
            }});
        }}

        // Library Validation子阶段图表
        const validationStagesCtx = document.getElementById('validationStagesChart').getContext('2d');
        const validationLabels = Object.keys(subsubLevelData);
        const validationValues = Object.values(subsubLevelData);

        if (validationLabels.length > 0) {{
            new Chart(validationStagesCtx, {{
                type: 'doughnut',
                data: {{
                    labels: validationLabels,
                    datasets: [{{
                        data: validationValues,
                        backgroundColor: [
                            '#00acc1',
                            '#0097a7',
                            '#00838f',
                            '#006064'
                        ],
                        borderColor: '#fff',
                        borderWidth: 2
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        title: {{
                            display: true,
                            text: 'Library Validation Breakdown',
                            font: {{
                                size: 14,
                                weight: '600'
                            }}
                        }},
                        legend: {{
                            position: 'bottom',
                            labels: {{
                                padding: 12,
                                usePointStyle: true
                            }}
                        }}
                    }}
                }}
            }});
        }}

        // 4. Token分布图
        const tokenCtx = document.getElementById('tokenDistribution').getContext('2d');
        const inputTokensStr = "{cost_data['token_stats']['input']}";
        const outputTokensStr = "{cost_data['token_stats']['output']}";
        const inputTokens = inputTokensStr !== 'N/A' ? parseInt(inputTokensStr.replace(/,/g, '')) : 0;
        const outputTokens = outputTokensStr !== 'N/A' ? parseInt(outputTokensStr.replace(/,/g, '')) : 0;

        new Chart(tokenCtx, {{
            type: 'doughnut',
            data: {{
                labels: ['Input Tokens', 'Output Tokens'],
                datasets: [{{
                    data: [inputTokens, outputTokens],
                    backgroundColor: [colors.primary, colors.success],
                    borderColor: '#fff',
                    borderWidth: 2
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        position: 'bottom',
                        labels: {{
                            padding: 16,
                            usePointStyle: true,
                            font: {{
                                size: 14
                            }}
                        }}
                    }},
                    tooltip: {{
                        callbacks: {{
                            label: function(context) {{
                                const total = inputTokens + outputTokens;
                                const percentage = ((context.parsed / total) * 100).toFixed(1);
                                return context.label + ': ' + context.parsed.toLocaleString() + ' (' + percentage + '%)';
                            }}
                        }}
                    }}
                }}
            }}
        }});

        // 交互功能
        function toggleCollapsible(element) {{
            element.classList.toggle('expanded');
            const content = element.nextElementSibling;
            content.classList.toggle('expanded');
        }}

        // 平滑滚动到锚点
        document.querySelectorAll('.sidenav-item').forEach(link => {{
            link.addEventListener('click', function(e) {{
                e.preventDefault();
                const targetId = this.getAttribute('href');
                const targetElement = document.querySelector(targetId);

                if (targetElement) {{
                    targetElement.scrollIntoView({{
                        behavior: 'smooth',
                        block: 'start'
                    }});
                }}

                // 更新活动状态
                document.querySelectorAll('.sidenav-item').forEach(item => {{
                    item.classList.remove('active');
                }});
                this.classList.add('active');
            }});
        }});

        // 滚动时更新侧边栏活动状态
        window.addEventListener('scroll', () => {{
            const sections = document.querySelectorAll('section[id]');
            const scrollY = window.pageYOffset;

            sections.forEach(section => {{
                const sectionTop = section.offsetTop - 100;
                const sectionHeight = section.clientHeight;
                const sectionId = section.getAttribute('id');

                if (scrollY > sectionTop && scrollY <= sectionTop + sectionHeight) {{
                    document.querySelectorAll('.sidenav-item').forEach(item => {{
                        item.classList.remove('active');
                        if (item.getAttribute('href') === '#' + sectionId) {{
                            item.classList.add('active');
                        }}
                    }});
                }}
            }});
        }});
    </script>
</body>
</html>
"""

    # 写入HTML文件
    with open(output_filename, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"优化的分析报告已生成: {output_filename}")