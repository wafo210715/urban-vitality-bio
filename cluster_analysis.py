"""
K-Means Clustering on Diversity Dimensions
k=4 clusters
"""

import geopandas as gpd
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt

# 读取数据
gdf = gpd.read_file('data/fishnet_diversity.geojson')
print(f"Total grids: {len(gdf)}")

# 聚类特征
features = ['cultural_shannon_norm', 'economic_shannon_norm', 'social_shannon_norm', 'eco_shannon']
X = gdf[features].copy()

# 标准化
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# K-Means 聚类
kmeans = KMeans(n_clusters=4, random_state=42, n_init=10)
gdf['cluster'] = kmeans.fit_predict(X_scaled)

# 分析每个 cluster 的特征
print("\n" + "=" * 60)
print("Cluster Analysis")
print("=" * 60)

cluster_stats = gdf.groupby('cluster')[features].mean()
cluster_counts = gdf.groupby('cluster').size()

print("\nCluster Sizes:")
for c in sorted(gdf['cluster'].unique()):
    print(f"  Cluster {c}: {cluster_counts[c]} grids ({cluster_counts[c]/len(gdf)*100:.1f}%)")

print("\nCluster Characteristics (mean normalized diversity):")
print(cluster_stats.round(3).to_string())

# 给 cluster 起名
def name_cluster(row):
    """根据特征给 cluster 命名"""
    cultural = row['cultural_shannon_norm']
    economic = row['economic_shannon_norm']
    social = row['social_shannon_norm']
    eco = row['eco_shannon']

    # 判断主导特征
    high_cultural = cultural > 0.2
    high_economic = economic > 0.3
    high_social = social > 0.2
    high_eco = eco > 0.2

    if high_cultural and high_economic:
        return "Cultural-Economic"
    elif high_social and high_economic:
        return "Socio-Economic"
    elif high_economic and not high_cultural and not high_social:
        return "Economic-Only"
    elif not high_cultural and not high_economic and not high_social:
        return "Low-Activity"
    else:
        return "Mixed"

cluster_names = cluster_stats.apply(name_cluster, axis=1)
print("\nCluster Names:")
for c, name in cluster_names.items():
    print(f"  Cluster {c}: {name}")

# 创建 cluster label 列
name_map = cluster_names.to_dict()
gdf['cluster_label'] = gdf['cluster'].map(name_map)

# 保存结果
gdf.to_file('data/fishnet_clusters.geojson', driver='GeoJSON')
gdf.to_file('data/fishnet_clusters.shp')
print("\nSaved: data/fishnet_clusters.geojson")
print("Saved: data/fishnet_clusters.shp")

# 可视化
fig, axes = plt.subplots(1, 2, figsize=(14, 6))

colors = ['#e41a1c', '#377eb8', '#4daf4a', '#984ea3']

# 图1: 空间分布
ax1 = axes[0]
for c in sorted(gdf['cluster'].unique()):
    subset = gdf[gdf['cluster'] == c]
    subset.plot(ax=ax1, color=colors[c], markersize=0.5)
ax1.set_title('Cluster Spatial Distribution')
ax1.set_axis_off()

# 手动添加图例
from matplotlib.patches import Patch
legend_elements = [Patch(facecolor=colors[c], label=f'C{c}: {name_map[c]}') for c in sorted(gdf['cluster'].unique())]
ax1.legend(handles=legend_elements, loc='upper left', fontsize=8)

# 图2: 雷达图
ax2 = axes[1]
ax2.remove()  # 移除原来的 ax2
ax2 = fig.add_subplot(122, polar=True)

angles = np.linspace(0, 2*np.pi, len(features), endpoint=False).tolist()
angles += angles[:1]

for c in sorted(gdf['cluster'].unique()):
    values = cluster_stats.loc[c].values.tolist()
    values += values[:1]
    ax2.plot(angles, values, 'o-', linewidth=2, label=f'C{c}: {name_map[c]}', color=colors[c])
    ax2.fill(angles, values, alpha=0.15, color=colors[c])

ax2.set_xticks(angles[:-1])
ax2.set_xticklabels(['Cultural', 'Economic', 'Social', 'Eco'])
ax2.set_title('Cluster Profiles')
ax2.legend(loc='upper right', bbox_to_anchor=(1.35, 1), fontsize=8)

plt.tight_layout()
plt.savefig('data/cluster_analysis.png', dpi=150, bbox_inches='tight')
print("Saved: data/cluster_analysis.png")

print("\n" + "=" * 60)
print("Done! Import fishnet_clusters.shp into ArcGIS Pro to visualize.")
print("=" * 60)
