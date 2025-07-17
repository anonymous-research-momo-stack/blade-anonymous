import json

from evaluation.interface import ResearchQuestionData


def generate_analysis_report(data: ResearchQuestionData, output_filename: str) -> None:
    """
    生成研究数据的可视化分析报告

    Args:
        data: ResearchQuestionData 实例
        output_filename: 输出的HTML文件名（如 "analysis_report.html"）
    """

    def safe_format(value, decimal_places=2):
        """安全格式化数值，处理None值"""
        if value is None:
            return "N/A"
        if isinstance(value, (int, float)):
            return f"{value:.{decimal_places}f}"
        return str(value)

    def format_time(seconds):
        """格式化时间显示"""
        if seconds is None:
            return "N/A"
        if seconds >= 60:
            minutes = seconds / 60
            return f"{minutes:.2f} min"
        return f"{seconds:.2f} sec"

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

    def prepare_ablation_data(ablation_data):
        """准备消融实验数据"""
        if ablation_data is None:
            return {
                'configurations': [],
                'precision_data': [],
                'recall_data': [],
                'f1_data': []
            }

        configurations = [
            ('Complete System', data.effectiveness),
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
                'duration_breakdown': {'top_level': {}, 'sub_level': {}, 'subsub_level': {}},
                'token_stats': {'input': 'N/A', 'output': 'N/A', 'total': 'N/A'},
                'cost_stats': {'total': 'N/A', 'average': 'N/A'}
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
            },
            'token_stats': {
                'input': safe_format(eff_data.input_token_count, 0),
                'output': safe_format(eff_data.output_token_count, 0),
                'total': safe_format(eff_data.total_token_count, 0)
            },
            'cost_stats': {
                'total': f"${safe_format(eff_data.total_cost)}" if eff_data.total_cost is not None else "N/A",
                'average': f"${safe_format(eff_data.average_cost)}" if eff_data.average_cost is not None else "N/A"
            }
        }

    # 准备数据
    effectiveness_data = prepare_effectiveness_data(data.effectiveness)
    ablation_data = prepare_ablation_data(data.effectiveness_ablation_study)
    efficiency_data = prepare_efficiency_data(data.efficiency)

    # 生成HTML内容
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Evaluation Report</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>
    <style>
        body {{
            font-family: 'Times New Roman', serif;
            margin: 0;
            padding: 20px;
            background-color: #fafafa;
            color: #333;
            line-height: 1.6;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}

        h1 {{
            text-align: center;
            color: #2c3e50;
            margin-bottom: 40px;
            font-size: 2.2em;
            border-bottom: 3px solid #3498db;
            padding-bottom: 15px;
        }}

        h2 {{
            color: #2c3e50;
            margin-top: 40px;
            margin-bottom: 20px;
            font-size: 1.6em;
            border-left: 4px solid #3498db;
            padding-left: 15px;
        }}

        .section {{
            margin-bottom: 50px;
        }}

        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}

        .metric-card {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            border: 1px solid #e9ecef;
        }}

        .metric-card h3 {{
            margin: 0 0 10px 0;
            color: #2c3e50;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .metric-card .value {{
            font-size: 1.8em;
            font-weight: bold;
            color: #3498db;
        }}

        .chart-container {{
            margin: 30px 0;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
            border: 1px solid #e9ecef;
        }}

        .chart-title {{
            text-align: center;
            margin-bottom: 20px;
            color: #2c3e50;
            font-size: 1.2em;
            font-weight: bold;
        }}

        .chart-subtitle {{
            text-align: center;
            margin-bottom: 15px;
            color: #7f8c8d;
            font-size: 0.9em;
            font-style: italic;
        }}

        canvas {{
            max-height: 400px !important;
        }}

        .stats-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            background: white;
        }}

        .stats-table th,
        .stats-table td {{
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}

        .stats-table th {{
            background-color: #3498db;
            color: white;
            font-weight: bold;
        }}

        .stats-table tr:nth-child(even) {{
            background-color: #f2f2f2;
        }}

        .two-column {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
        }}

        .three-column {{
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 20px;
        }}

        @media (max-width: 768px) {{
            .container {{
                padding: 20px;
            }}

            .two-column, .three-column {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Evaluation Report</h1>

        <!-- Effectiveness Analysis Section -->
        <div class="section">
            <h2>1. Effectiveness Analysis</h2>

            <div class="metrics-grid">
                <div class="metric-card">
                    <h3>True Positives</h3>
                    <div class="value">{effectiveness_data['tp_count']}</div>
                </div>
                <div class="metric-card">
                    <h3>False Positives</h3>
                    <div class="value">{effectiveness_data['fp_count']}</div>
                </div>
                <div class="metric-card">
                    <h3>False Negatives</h3>
                    <div class="value">{effectiveness_data['fn_count']}</div>
                </div>
                <div class="metric-card">
                    <h3>Precision</h3>
                    <div class="value">{effectiveness_data['precision']}%</div>
                </div>
                <div class="metric-card">
                    <h3>Recall</h3>
                    <div class="value">{effectiveness_data['recall']}%</div>
                </div>
                <div class="metric-card">
                    <h3>F1-Score</h3>
                    <div class="value">{effectiveness_data['f1_score']}%</div>
                </div>
            </div>

            <div class="chart-container">
                <div class="chart-title">Performance Metrics</div>
                <canvas id="effectivenessChart"></canvas>
            </div>
        </div>

        <!-- Ablation Study Section -->
        <div class="section">
            <h2>2. Ablation Study</h2>

            <div class="chart-container">
                <div class="chart-title">Component Contribution Analysis</div>
                <canvas id="ablationChart"></canvas>
            </div>
        </div>

        <!-- Efficiency Analysis Section -->
        <div class="section">
            <h2>3. Efficiency Analysis</h2>

            <div class="two-column">
                <div>
                    <h3>File Statistics</h3>
                    <table class="stats-table">
                        <tr>
                            <th>Metric</th>
                            <th>Value</th>
                        </tr>
                        <tr>
                            <td>Total File Size</td>
                            <td>{efficiency_data['file_stats']['total']} KB</td>
                        </tr>
                        <tr>
                            <td>Average File Size</td>
                            <td>{efficiency_data['file_stats']['average']} KB</td>
                        </tr>
                    </table>

                    <h3>Time Statistics</h3>
                    <table class="stats-table">
                        <tr>
                            <th>Metric</th>
                            <th>Value</th>
                        </tr>
                        <tr>
                            <td>Total Theoretical Duration</td>
                            <td>{efficiency_data['time_stats']['total_theoretical']}</td>
                        </tr>
                        <tr>
                            <td>Average Theoretical Duration</td>
                            <td>{efficiency_data['time_stats']['average_theoretical']}</td>
                        </tr>
                        <tr>
                            <td>Total Actual Duration</td>
                            <td>{efficiency_data['time_stats']['total_actual']}</td>
                        </tr>
                        <tr>
                            <td>Average Actual Duration</td>
                            <td>{efficiency_data['time_stats']['average_actual']}</td>
                        </tr>
                    </table>
                </div>

                <div>
                    <div class="chart-container">
                        <div class="chart-title">Token Distribution</div>
                        <canvas id="tokenChart"></canvas>
                    </div>
                </div>
            </div>

            <!-- Duration Breakdown - Hierarchical View -->
            <h3>Duration Breakdown Analysis</h3>
            <div class="three-column">
                <div class="chart-container">
                    <div class="chart-title">Main Stages</div>
                    <div class="chart-subtitle">Overall time distribution</div>
                    <canvas id="mainStagesChart"></canvas>
                </div>

                <div class="chart-container">
                    <div class="chart-title">Agent Analysis</div>
                    <div class="chart-subtitle">Sub-stages breakdown</div>
                    <canvas id="agentStagesChart"></canvas>
                </div>

                <div class="chart-container">
                    <div class="chart-title">Library Validation</div>
                    <div class="chart-subtitle">Validation steps breakdown</div>
                    <canvas id="validationStagesChart"></canvas>
                </div>
            </div>

            <h3>Cost Analysis</h3>
            <table class="stats-table">
                <tr>
                    <th>Metric</th>
                    <th>Value</th>
                </tr>
                <tr>
                    <td>Total Cost</td>
                    <td>{efficiency_data['cost_stats']['total']}</td>
                </tr>
                <tr>
                    <td>Average Cost per Analysis</td>
                    <td>{efficiency_data['cost_stats']['average']}</td>
                </tr>
            </table>
        </div>
    </div>

    <script>
        // Chart.js configuration
        Chart.defaults.font.family = "'Times New Roman', serif";
        Chart.defaults.font.size = 12;

        // Colors for academic style
        const colors = {{
            primary: '#3498db',
            secondary: '#2c3e50',
            success: '#27ae60',
            warning: '#f39c12',
            danger: '#e74c3c',
            info: '#17a2b8',
            light: '#95a5a6',
            dark: '#34495e'
        }};

        const backgroundColors = [
            colors.primary,
            colors.success,
            colors.warning,
            colors.danger,
            colors.info,
            colors.secondary,
            colors.light,
            colors.dark,
            '#9b59b6'
        ];

        // 1. Effectiveness Chart
        const effectivenessCtx = document.getElementById('effectivenessChart').getContext('2d');
        new Chart(effectivenessCtx, {{
            type: 'bar',
            data: {{
                labels: ['Precision (%)', 'Recall (%)', 'F1-Score (%)'],
                datasets: [{{
                    label: 'Performance Metrics',
                    data: [
                        {effectiveness_data['precision'].replace('%', '') if effectiveness_data['precision'] != 'N/A' else 0},
                        {effectiveness_data['recall'].replace('%', '') if effectiveness_data['recall'] != 'N/A' else 0},
                        {effectiveness_data['f1_score'].replace('%', '') if effectiveness_data['f1_score'] != 'N/A' else 0}
                    ],
                    backgroundColor: [colors.primary, colors.success, colors.warning],
                    borderColor: [colors.primary, colors.success, colors.warning],
                    borderWidth: 1
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{
                        display: false
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        ticks: {{
                            callback: function(value) {{
                                return value + '%';
                            }}
                        }}
                    }}
                }}
            }}
        }});

        // 2. Ablation Study Chart
        const ablationCtx = document.getElementById('ablationChart').getContext('2d');
        const configurations = {json.dumps(ablation_data['configurations'])};
        const precisionData = {json.dumps(ablation_data['precision_data'])};
        const recallData = {json.dumps(ablation_data['recall_data'])};
        const f1Data = {json.dumps(ablation_data['f1_data'])};

        // Create datasets with different colors for each configuration
        const datasets = [];
        for (let i = 0; i < configurations.length; i++) {{
            datasets.push({{
                label: configurations[i],
                data: [precisionData[i], recallData[i], f1Data[i]],
                backgroundColor: backgroundColors[i % backgroundColors.length],
                borderColor: backgroundColors[i % backgroundColors.length],
                borderWidth: 1
            }});
        }}

        new Chart(ablationCtx, {{
            type: 'bar',
            data: {{
                labels: ['Precision (%)', 'Recall (%)', 'F1-Score (%)'],
                datasets: datasets
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{
                        position: 'bottom',
                        labels: {{
                            boxWidth: 12,
                            fontSize: 10
                        }}
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        ticks: {{
                            callback: function(value) {{
                                return value + '%';
                            }}
                        }}
                    }}
                }}
            }}
        }});

        // 3. Duration Breakdown Charts - Hierarchical View
        const topLevelData = {json.dumps(efficiency_data['duration_breakdown']['top_level'])};
        const subLevelData = {json.dumps(efficiency_data['duration_breakdown']['sub_level'])};
        const subsubLevelData = {json.dumps(efficiency_data['duration_breakdown']['subsub_level'])};

        // 3.1 Main Stages Chart
        const mainStagesCtx = document.getElementById('mainStagesChart').getContext('2d');
        const mainLabels = Object.keys(topLevelData);
        const mainValues = Object.values(topLevelData);

        if (mainLabels.length > 0) {{
            new Chart(mainStagesCtx, {{
                type: 'pie',
                data: {{
                    labels: mainLabels,
                    datasets: [{{
                        data: mainValues,
                        backgroundColor: mainLabels.map((_, i) => backgroundColors[i % backgroundColors.length]),
                        borderColor: '#fff',
                        borderWidth: 2
                    }}]
                }},
                options: {{
                    responsive: true,
                    plugins: {{
                        legend: {{
                            position: 'bottom',
                            labels: {{
                                boxWidth: 12,
                                fontSize: 10
                            }}
                        }},
                        tooltip: {{
                            callbacks: {{
                                label: function(context) {{
                                    return context.label + ': ' + context.parsed + '%';
                                }}
                            }}
                        }}
                    }}
                }}
            }});
        }} else {{
            mainStagesCtx.canvas.parentElement.innerHTML = '<p style="text-align: center; color: #666; margin-top: 50px;">No data available</p>';
        }}

        // 3.2 Agent Analysis Sub-stages Chart
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
                        backgroundColor: agentLabels.map((_, i) => backgroundColors[(i + 3) % backgroundColors.length]),
                        borderColor: '#fff',
                        borderWidth: 2
                    }}]
                }},
                options: {{
                    responsive: true,
                    plugins: {{
                        legend: {{
                            position: 'bottom',
                            labels: {{
                                boxWidth: 12,
                                fontSize: 10
                            }}
                        }},
                        tooltip: {{
                            callbacks: {{
                                label: function(context) {{
                                    return context.label + ': ' + context.parsed + '%';
                                }}
                            }}
                        }}
                    }}
                }}
            }});
        }} else {{
            agentStagesCtx.canvas.parentElement.innerHTML = '<p style="text-align: center; color: #666; margin-top: 50px;">No data available</p>';
        }}

        // 3.3 Library Validation Sub-stages Chart
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
                        backgroundColor: validationLabels.map((_, i) => backgroundColors[(i + 6) % backgroundColors.length]),
                        borderColor: '#fff',
                        borderWidth: 2
                    }}]
                }},
                options: {{
                    responsive: true,
                    plugins: {{
                        legend: {{
                            position: 'bottom',
                            labels: {{
                                boxWidth: 12,
                                fontSize: 10
                            }}
                        }},
                        tooltip: {{
                            callbacks: {{
                                label: function(context) {{
                                    return context.label + ': ' + context.parsed + '%';
                                }}
                            }}
                        }}
                    }}
                }}
            }});
        }} else {{
            validationStagesCtx.canvas.parentElement.innerHTML = '<p style="text-align: center; color: #666; margin-top: 50px;">No data available</p>';
        }}

        // 4. Token Distribution Chart
        const tokenCtx = document.getElementById('tokenChart').getContext('2d');
        const inputTokens = {efficiency_data['token_stats']['input'].replace(',', '') if efficiency_data['token_stats']['input'] != 'N/A' else 0};
        const outputTokens = {efficiency_data['token_stats']['output'].replace(',', '') if efficiency_data['token_stats']['output'] != 'N/A' else 0};

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
                plugins: {{
                    legend: {{
                        position: 'bottom'
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>
    """

    # 写入HTML文件
    with open(output_filename, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"Analysis report generated successfully: {output_filename}")