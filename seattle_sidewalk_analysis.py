# Seattle Sidewalk Accessibility Analysis
# DubsTech Datathon 2026
# Team: DJR

# flake8: noqa

import pandas as pd
import plotly.express as px
import folium
from folium.plugins import HeatMap

# 1. LOAD & CLEAN DATA

df = pd.read_csv("Access_to_Everyday_Life_Dataset.csv")
print(f"Loaded {len(df):,} rows")

# rename columns to something easier to type
df = df.rename(columns={
    "geometry/coordinates/0": "longitude",
    "geometry/coordinates/1": "latitude",
    "properties/label_type":  "label_type",
    "properties/neighborhood": "neighborhood",
    "properties/severity":    "severity",
    "properties/is_temporary": "is_temporary",
})

# severity has missing vals. fill with median (3 or 4)
# using median because severity is ordinal (1-5), mean would give decimals
missing_sev = df["severity"].isna().sum()
df["severity"] = df["severity"].fillna(df["severity"].median())
print(f"Imputed {missing_sev} missing severity values")

# remove 0,0 coordinates and NaNs
bad_coords = (((df["longitude"] == 0) & (df["latitude"] == 0)) 
              | df["longitude"].isna() 
              | df["latitude"].isna())
df = df[~bad_coords].copy()
print(f"Clean data: {len(df):,} rows\n")

# 2. ANALYSIS & RANKING

# Create the "Mobility Friction Index"
# Logic: Volume * Intensity. A neighborhood needs both high counts and 
# high severity to rank at the top.
stats = (
    df.groupby("neighborhood")
    .agg(
        total_barriers=("severity", "count"),
        avg_severity=("severity", "mean"),
    )
    .reset_index()
)

stats["barrier_density_index"] = (stats["total_barriers"] * stats["avg_severity"])

# Rounding for cleaner display
stats["avg_severity"] = stats["avg_severity"].round(2)
stats["barrier_density_index"] = stats["barrier_density_index"].round(1)

# Sort by new index
stats = (
    stats
    .sort_values("barrier_density_index", ascending=False)
    .reset_index(drop=True)
)

top10 = stats.head(10).copy()

# Print the text table (for the console output/report)
print("TOP 10 MOST INACCESSIBLE NEIGHBORHOODS (by Barrier Density Index)")
print("-" * 65)
print(top10.to_string(
    index=False,
    columns=["neighborhood", "total_barriers", "avg_severity", "barrier_density_index"],
    header=["Neighborhood", "Barriers", "Avg Severity", "Index"],
))
print("-" * 65)

# 3. VISUALIZATIONS

# A. Horizontal Bar Chart (Plotly)
print("\nGenerating Chart 1 (Bar Chart)...")

fig = px.bar(
    top10.sort_values("total_barriers", ascending=True),
    x="total_barriers",
    y="neighborhood",
    orientation="h",
    color="avg_severity",
    color_continuous_scale="YlOrRd",
    labels={
        "total_barriers": "Total Barrier Count",
        "neighborhood": "Neighborhood",
        "avg_severity": "Avg Severity (1-5)",
    },
    title="<b>Top 10 Most Inaccessible Seattle Neighborhoods</b><br><sup>Barrier count colored by average severity</sup>",
    template="plotly_white",
)

fig.update_layout(
    font=dict(family="Arial, sans-serif", size=13),
    title_font_size=18,
    coloraxis_colorbar=dict(title="Avg<br>Severity", tickvals=[1, 2, 3, 4, 5]),
    margin=dict(l=160, r=40, t=80, b=60),
)

fig.update_traces(texttemplate="%{x:,.0f}", textposition="outside")
fig.write_html("chart_top10_barriers.html")
print("Saved -> chart_top10_barriers.html")


# B. Interactive Map (Folium)
print("Generating Chart 2 (Map)...")

center_lat = df["latitude"].mean()
center_lon = df["longitude"].mean()

m = folium.Map(location=[center_lat, center_lon], zoom_start=12, tiles="CartoDB positron")

# Layer 1: Heatmap (shows density of ALL barriers)
heat_data = df[["latitude", "longitude", "severity"]].values.tolist()
HeatMap(
    heat_data,
    radius=10,
    blur=15,
    min_opacity=0.4,
    gradient={0.2: "blue", 0.4: "lime", 0.6: "yellow", 0.8: "orange", 1.0: "red"},
).add_to(m)

# Layer 2: Markers for Severity 5 (Critical Issues)
# Only showing the worst ones to avoid cluttering the map
severe_df = df[df["severity"] >= 5].head(900)

for _, row in severe_df.iterrows():
    folium.CircleMarker(
        location=[row["latitude"], row["longitude"]],
        radius=3,
        color="red",
        fill=True,
        fill_color="red",
        popup=folium.Popup(f"<b>{row['label_type']}</b><br>{row['neighborhood']}", max_width=200),
    ).add_to(m)

# little legend in the corner
legend_html = """
<div style="
    position: fixed; bottom: 30px; left: 30px; z-index: 1000;
    background: white; padding: 12px 16px; border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.25);
    font-family: Arial, sans-serif; font-size: 13px; line-height: 1.6;
">
    <b>Seattle Accessibility Hotspots</b><br>
    <span style="color:red;">&#9679;</span> Severity-5 Barrier (Danger Zone)<br>
    <span style="background: linear-gradient(to right, blue, lime, yellow, orange, red);
          display:inline-block; width:80px; height:10px; border-radius:3px;"></span>
    Heatmap Density
</div>
"""

m.get_root().html.add_child(folium.Element(legend_html))

m.save("seattle_accessibility_hotspots.html")
print("Saved -> seattle_accessibility_hotspots.html")


# C. Barrier Type Pie Chart (Plotly)
print("Generating Chart 3 (Pie Chart)...")

# Get top 5 barrier types
type_counts = df['label_type'].value_counts().head(5).reset_index()
type_counts.columns = ['Barrier Type', 'Count']

fig_pie = px.pie(
    type_counts, 
    values='Count', 
    names='Barrier Type', 
    title='<b>The Face of Friction</b><br><sup>Breakdown of the Most Common Barrier Types</sup>',
    color_discrete_sequence=px.colors.sequential.RdBu,
    template='plotly_white'
)
fig_pie.write_html("chart_barrier_types.html")
print("Saved -> chart_barrier_types.html")

# 4. SUMMARY

print("\n" + "=" * 65)
print("FINAL SUMMARY FOR REPORT")
print("=" * 65)

# Temp vs Perm stats
perm_stats = df['is_temporary'].value_counts(normalize=True) * 100
print(f"Permanent Barriers: {perm_stats.get(False, 0):.1f}%")
print(f"Temporary Barriers: {perm_stats.get(True, 0):.1f}%")

# Quick Insight check
n1 = top10.iloc[0]
n2 = top10.iloc[1]
print(f"\nInsight: {n1['neighborhood']} is #1 with {n1['total_barriers']:,} barriers.")
print(f"Insight: {n2['neighborhood']} is #2 but has higher severity ({n2['avg_severity']}).")

# Export full stats
stats.to_csv("neighborhood_barrier_stats.csv", index=False)
print("\nDone! Open the .html files to see your charts.")
