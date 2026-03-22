"""
Visualize Farm Micro-Analysis Results
生成分析结果的可视化图表
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from pathlib import Path

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

OUTPUT_DIR = Path('farm_reports')

def create_phase_summary_charts(df):
    """创建 Phase 摘要图表"""
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))

    # 1. 各 Phase 的 Farm 数量和面积
    ax1 = axes[0, 0]
    phase_stats = df.groupby('phase').agg({
        'farm_id': 'count',
        'area_sqm': 'sum'
    }).reset_index()
    phase_stats.columns = ['Phase', 'Farm Count', 'Total Area (sqm)']

    x = np.arange(len(phase_stats))
    width = 0.35

    ax1_twin = ax1.twinx()
    bars1 = ax1.bar(x - width/2, phase_stats['Farm Count'], width, label='Farm Count', color='steelblue')
    bars2 = ax1_twin.bar(x + width/2, phase_stats['Total Area (sqm)'], width, label='Area', color='coral')

    ax1.set_xlabel('Phase')
    ax1.set_ylabel('Farm Count', color='steelblue')
    ax1_twin.set_ylabel('Total Area (sqm)', color='coral')
    ax1.set_xticks(x)
    ax1.set_xticklabels([f'Phase {i}' for i in phase_stats['Phase']])
    ax1.legend(loc='upper left')
    ax1_twin.legend(loc='upper right')
    ax1.set_title('Farms and Area by Phase')

    # 2. 各 Phase 的连接数量
    ax2 = axes[0, 1]
    connection_stats = df.groupby('phase')[['food_connections', 'social_connections', 'cultural_connections']].sum()
    connection_stats.plot(kind='bar', ax=ax2, color=['#ff7f0e', '#2ca02c', '#1f77b4'])
    ax2.set_xlabel('Phase')
    ax2.set_ylabel('Connection Count')
    ax2.set_title('POI Connections by Phase')
    ax2.legend(['Food', 'Social', 'Cultural'])
    ax2.set_xticklabels([f'Phase {i}' for i in connection_stats.index], rotation=0)

    # 3. Shannon 多样性指数分布
    ax3 = axes[0, 2]
    phases = sorted(df['phase'].unique())
    for phase in phases:
        phase_data = df[df['phase'] == phase]['current_shannon']
        ax3.hist(phase_data, alpha=0.5, label=f'Phase {phase}', bins=20)
    ax3.set_xlabel('Shannon Diversity Index')
    ax3.set_ylabel('Frequency')
    ax3.set_title('Shannon Index Distribution by Phase')
    ax3.legend()

    # 4. Biodiversity Impact
    ax4 = axes[1, 0]
    impact_stats = df.groupby('phase')['biodiversity_impact'].agg(['mean', 'std'])
    bars = ax4.bar(impact_stats.index, impact_stats['mean'], yerr=impact_stats['std'],
                   color=['#e41a1c', '#ff7f00', '#984ea3', '#4daf4a'])
    ax4.set_xlabel('Phase')
    ax4.set_ylabel('Biodiversity Impact (Δ Shannon)')
    ax4.set_title('Projected Biodiversity Impact by Phase')
    ax4.set_xticklabels([f'Phase {i}' for i in impact_stats.index])

    # 5. Cluster 类型分布
    ax5 = axes[1, 1]
    cluster_counts = df.groupby(['phase', 'cluster']).size().unstack(fill_value=0)
    cluster_counts.plot(kind='bar', stacked=True, ax=ax5,
                        color=['#2ca02c', '#9467bd', '#8c564b', '#1f77b4'])
    ax5.set_xlabel('Phase')
    ax5.set_ylabel('Farm Count')
    ax5.set_title('Cluster Distribution by Phase')
    ax5.legend(title='Cluster', loc='upper right')
    ax5.set_xticklabels([f'Phase {i}' for i in cluster_counts.index], rotation=0)

    # 6. 种植潜力 vs 面积
    ax6 = axes[1, 2]
    scatter = ax6.scatter(df['area_sqm'], df['leafy_capacity'],
                         c=df['phase'], cmap='viridis', alpha=0.6, s=50)
    ax6.set_xlabel('Farm Area (sqm)')
    ax6.set_ylabel('Leafy Vegetable Capacity')
    ax6.set_title('Planting Capacity vs Farm Area')
    plt.colorbar(scatter, ax=ax6, label='Phase')

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'phase_summary_charts.png', dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: {OUTPUT_DIR / 'phase_summary_charts.png'}")


def create_cluster_analysis_charts(df):
    """创建 Cluster 分析图表"""
    fig, axes = plt.subplots(2, 2, figsize=(14, 12))

    # 1. Cluster 类型的特征雷达图
    ax1 = axes[0, 0]
    cluster_stats = df.groupby('cluster').agg({
        'area_sqm': 'mean',
        'food_connections': 'mean',
        'current_shannon': 'mean',
        'biodiversity_impact': 'mean',
        'leafy_capacity': 'mean'
    }).reset_index()

    # 归一化
    for col in cluster_stats.columns[1:]:
        cluster_stats[col] = (cluster_stats[col] - cluster_stats[col].min()) / (cluster_stats[col].max() - cluster_stats[col].min() + 1e-10)

    categories = ['Area', 'Food Conn.', 'Shannon', 'Impact', 'Capacity']
    angles = np.linspace(0, 2*np.pi, len(categories), endpoint=False).tolist()
    angles += angles[:1]

    ax1 = plt.subplot(221, polar=True)
    for idx, row in cluster_stats.iterrows():
        values = row.iloc[1:].tolist()
        values += values[:1]
        ax1.plot(angles, values, 'o-', linewidth=2, label=row['cluster'])
        ax1.fill(angles, values, alpha=0.1)

    ax1.set_xticks(angles[:-1])
    ax1.set_xticklabels(categories)
    ax1.set_title('Cluster Characteristics (Normalized)')
    ax1.legend(loc='upper right', bbox_to_anchor=(1.3, 1.0))

    # 2. 各 Cluster 的 Shannon 指数箱线图
    ax2 = axes[0, 1]
    clusters = df['cluster'].unique()
    data = [df[df['cluster'] == c]['current_shannon'] for c in clusters]
    bp = ax2.boxplot(data, labels=clusters, patch_artist=True)
    colors = ['#2ca02c', '#9467bd', '#8c564b', '#1f77b4']
    for patch, color in zip(bp['boxes'], colors[:len(clusters)]):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
    ax2.set_xlabel('Cluster')
    ax2.set_ylabel('Shannon Diversity Index')
    ax2.set_title('Shannon Index by Cluster')
    ax2.tick_params(axis='x', rotation=15)

    # 3. 连接数量 vs Shannon 指数
    ax3 = axes[1, 0]
    for cluster in df['cluster'].unique():
        cluster_data = df[df['cluster'] == cluster]
        ax3.scatter(cluster_data['food_connections'], cluster_data['current_shannon'],
                   label=cluster, alpha=0.6, s=50)
    ax3.set_xlabel('Food Connections')
    ax3.set_ylabel('Shannon Diversity Index')
    ax3.set_title('Food Connections vs Biodiversity')
    ax3.legend()

    # 4. Typology 分布
    ax4 = axes[1, 1]
    typology_stats = df.groupby(['typology', 'phase']).size().unstack(fill_value=0)
    typology_stats.plot(kind='bar', ax=ax4,
                        color=['#e41a1c', '#ff7f00', '#984ea3', '#4daf4a'])
    ax4.set_xlabel('Typology')
    ax4.set_ylabel('Farm Count')
    ax4.set_title('Farm Distribution by Typology and Phase')
    ax4.legend(title='Phase')
    ax4.set_xticklabels(ax4.get_xticklabels(), rotation=0)

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'cluster_analysis_charts.png', dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: {OUTPUT_DIR / 'cluster_analysis_charts.png'}")


def create_top_farms_chart(df, n=20):
    """创建 Top N Farms 图表"""
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))

    # 1. Top 20 by Food Connections
    ax1 = axes[0, 0]
    top_food = df.nlargest(n, 'food_connections')[['farm_id', 'food_connections', 'cluster']]
    colors = {'Cultural-Economic': '#2ca02c', 'Economic-Only': '#9467bd',
              'Low-Activity': '#8c564b', 'Socio-Economic': '#1f77b4'}
    bar_colors = [colors[c] for c in top_food['cluster']]
    ax1.barh(range(n), top_food['food_connections'], color=bar_colors)
    ax1.set_yticks(range(n))
    ax1.set_yticklabels([f"Farm {fid}" for fid in top_food['farm_id']])
    ax1.set_xlabel('Food Connections')
    ax1.set_title(f'Top {n} Farms by Food Connections')
    ax1.invert_yaxis()

    # 2. Top 20 by Area
    ax2 = axes[0, 1]
    top_area = df.nlargest(n, 'area_sqm')[['farm_id', 'area_sqm', 'cluster']]
    bar_colors = [colors[c] for c in top_area['cluster']]
    ax2.barh(range(n), top_area['area_sqm'], color=bar_colors)
    ax2.set_yticks(range(n))
    ax2.set_yticklabels([f"Farm {fid}" for fid in top_area['farm_id']])
    ax2.set_xlabel('Area (sqm)')
    ax2.set_title(f'Top {n} Farms by Area')
    ax2.invert_yaxis()

    # 3. Top 20 by Biodiversity Impact
    ax3 = axes[1, 0]
    top_impact = df.nlargest(n, 'biodiversity_impact')[['farm_id', 'biodiversity_impact', 'cluster']]
    bar_colors = [colors[c] for c in top_impact['cluster']]
    ax3.barh(range(n), top_impact['biodiversity_impact'], color=bar_colors)
    ax3.set_yticks(range(n))
    ax3.set_yticklabels([f"Farm {fid}" for fid in top_impact['farm_id']])
    ax3.set_xlabel('Biodiversity Impact (Δ Shannon)')
    ax3.set_title(f'Top {n} Farms by Biodiversity Impact Potential')
    ax3.invert_yaxis()

    # 4. Top 20 by Planting Capacity
    ax4 = axes[1, 1]
    top_capacity = df.nlargest(n, 'leafy_capacity')[['farm_id', 'leafy_capacity', 'cluster']]
    bar_colors = [colors[c] for c in top_capacity['cluster']]
    ax4.barh(range(n), top_capacity['leafy_capacity'], color=bar_colors)
    ax4.set_yticks(range(n))
    ax4.set_yticklabels([f"Farm {fid}" for fid in top_capacity['farm_id']])
    ax4.set_xlabel('Leafy Vegetable Capacity')
    ax4.set_title(f'Top {n} Farms by Planting Capacity')
    ax4.invert_yaxis()

    # 添加图例
    legend_elements = [plt.Rectangle((0,0),1,1, facecolor=c, label=l)
                       for l, c in colors.items()]
    fig.legend(handles=legend_elements, loc='lower center', ncol=4,
               bbox_to_anchor=(0.5, 0.01))

    plt.tight_layout(rect=[0, 0.05, 1, 1])
    plt.savefig(OUTPUT_DIR / 'top_farms_charts.png', dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: {OUTPUT_DIR / 'top_farms_charts.png'}")


def create_summary_stats(df):
    """创建统计摘要"""
    stats = {
        'Total Farms': len(df),
        'Total Area (sqm)': df['area_sqm'].sum(),
        'Total Food Connections': df['food_connections'].sum(),
        'Total Restaurants': df['restaurant_count'].sum(),
        'Average Shannon Index': df['current_shannon'].mean(),
        'Average Projected Shannon': df['projected_shannon'].mean(),
        'Average Biodiversity Impact': df['biodiversity_impact'].mean(),
        'Total Leafy Capacity': df['leafy_capacity'].sum(),
    }

    # Phase 统计
    phase_stats = df.groupby('phase').agg({
        'farm_id': 'count',
        'area_sqm': 'sum',
        'food_connections': 'sum',
        'current_shannon': 'mean',
        'biodiversity_impact': 'mean'
    }).round(3)
    phase_stats.columns = ['Farms', 'Area (sqm)', 'Food Conn.', 'Avg Shannon', 'Avg Impact']

    # Cluster 统计
    cluster_stats = df.groupby('cluster').agg({
        'farm_id': 'count',
        'area_sqm': 'sum',
        'food_connections': 'sum',
        'current_shannon': 'mean',
        'biodiversity_impact': 'mean'
    }).round(3)
    cluster_stats.columns = ['Farms', 'Area (sqm)', 'Food Conn.', 'Avg Shannon', 'Avg Impact']

    return stats, phase_stats, cluster_stats


def main():
    """主函数"""
    print("Loading analysis results...")
    df = pd.read_csv(OUTPUT_DIR / 'farm_micro_analysis.csv')

    print("\nCreating visualization charts...")

    # 创建图表
    create_phase_summary_charts(df)
    create_cluster_analysis_charts(df)
    create_top_farms_chart(df)

    # 打印统计摘要
    stats, phase_stats, cluster_stats = create_summary_stats(df)

    print("\n" + "="*60)
    print("OVERALL STATISTICS")
    print("="*60)
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.3f}")
        else:
            print(f"  {key}: {value:,}")

    print("\n" + "="*60)
    print("STATISTICS BY PHASE")
    print("="*60)
    print(phase_stats.to_string())

    print("\n" + "="*60)
    print("STATISTICS BY CLUSTER")
    print("="*60)
    print(cluster_stats.to_string())

    # 保存统计摘要
    with open(OUTPUT_DIR / 'analysis_summary.txt', 'w', encoding='utf-8') as f:
        f.write("Urban Agroecology Micro-Analysis Summary\n")
        f.write("="*60 + "\n\n")

        f.write("OVERALL STATISTICS\n")
        f.write("-"*40 + "\n")
        for key, value in stats.items():
            if isinstance(value, float):
                f.write(f"  {key}: {value:.3f}\n")
            else:
                f.write(f"  {key}: {value:,}\n")

        f.write("\n\nSTATISTICS BY PHASE\n")
        f.write("-"*40 + "\n")
        f.write(phase_stats.to_string())

        f.write("\n\nSTATISTICS BY CLUSTER\n")
        f.write("-"*40 + "\n")
        f.write(cluster_stats.to_string())

    print(f"\nSaved summary to {OUTPUT_DIR / 'analysis_summary.txt'}")
    print("\nDone!")


if __name__ == "__main__":
    main()
