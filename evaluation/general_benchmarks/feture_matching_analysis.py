import json

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import rcParams


def _plot_feature_matching_top_n_effectiveness_figure(effectiveness_dict):
    """
    绘制特征匹配效果分析图表

    Parameters:
    effectiveness_dict: dict, 格式为 {top_n: {"precision": float, "recall": float, "f1_score": float}}
    """

    # 设置学术论文风格
    plt.style.use('seaborn-v0_8-whitegrid')  # 使用学术风格
    rcParams['font.family'] = 'serif'
    rcParams['font.size'] = 12
    rcParams['axes.labelsize'] = 14
    rcParams['axes.titlesize'] = 16
    rcParams['xtick.labelsize'] = 12
    rcParams['ytick.labelsize'] = 12
    rcParams['legend.fontsize'] = 12

    # 提取数据并转换键为整数
    top_n_values = sorted([int(k) for k in effectiveness_dict.keys()])
    precision_values = [effectiveness_dict[str(top_n)]['precision'] for top_n in top_n_values]
    recall_values = [effectiveness_dict[str(top_n)]['recall'] for top_n in top_n_values]
    f1_values = [effectiveness_dict[str(top_n)]['f1_score'] for top_n in top_n_values]

    # 创建图表
    fig, ax = plt.subplots(figsize=(10, 6), dpi=300)

    # 绘制三条线，使用插值让线条更加流畅
    from scipy.interpolate import make_interp_spline

    # 为了让线条更流畅，创建更密集的x点进行插值
    x_smooth = np.linspace(min(top_n_values), max(top_n_values), 300)

    # 使用样条插值让线条更流畅
    precision_smooth = make_interp_spline(top_n_values, precision_values, k=3)(x_smooth)
    recall_smooth = make_interp_spline(top_n_values, recall_values, k=3)(x_smooth)
    f1_smooth = make_interp_spline(top_n_values, f1_values, k=3)(x_smooth)

    # 绘制流畅的线条
    ax.plot(x_smooth, precision_smooth, 'b-', linewidth=2.5, label='Precision', alpha=0.8)
    ax.plot(x_smooth, recall_smooth, 'r-', linewidth=2.5, label='Recall', alpha=0.8)
    ax.plot(x_smooth, f1_smooth, 'g-', linewidth=2.5, label='F1-Score', alpha=0.8)

    # 在原始数据点上添加小标记点（可选，让数据点更明显）
    ax.scatter(top_n_values, precision_values, color='blue', s=15, alpha=0.6, zorder=5)
    ax.scatter(top_n_values, recall_values, color='red', s=15, alpha=0.6, zorder=5)
    ax.scatter(top_n_values, f1_values, color='green', s=15, alpha=0.6, zorder=5)

    # 设置坐标轴
    ax.set_xlabel('Top-N Results', fontweight='bold')
    ax.set_ylabel('Performance (%)', fontweight='bold')

    # 设置坐标轴范围和刻度
    ax.set_xlim(1, max(top_n_values))
    ax.set_ylim(0, 100)

    # 设置x轴刻度，确保显示关键点
    x_ticks = list(range(1, max(top_n_values) + 1, 10))  # 每10个显示一个刻度
    if max(top_n_values) not in x_ticks:
        x_ticks.append(max(top_n_values))
    ax.set_xticks(x_ticks)

    # 设置y轴刻度
    ax.set_yticks(range(0, 101, 10))

    # 添加网格
    ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
    ax.set_axisbelow(True)  # 将网格放在数据线后面

    # 添加图例
    ax.legend(loc='best', frameon=True, fancybox=True, shadow=True)

    # 优化布局
    plt.tight_layout()

    # 显示图表
    plt.show()

    # 如果需要保存图表，可以取消注释以下行
    # plt.savefig('effectiveness_analysis.pdf', dpi=300, bbox_inches='tight')
    # plt.savefig('effectiveness_analysis.png', dpi=300, bbox_inches='tight')

    print("建议的图表标题：Performance Metrics vs Top-N Results in Binary Third-party Component Detection")
    print("图表已生成，如需保存请取消注释相应代码行")


def plot_feature_matching_top_n_effectiveness_figure(effectiveness_analysis_result_path):
    """
    绘制特征匹配效果分析图表
    :param effectiveness_analysis_result_path: 效果分析结果文件路径
    """
    # 加载效果分析结果
    with open(effectiveness_analysis_result_path, "r", encoding="utf-8") as f:
        effectiveness_dict = json.load(f)

    # 绘制图表
    _plot_feature_matching_top_n_effectiveness_figure(effectiveness_dict)