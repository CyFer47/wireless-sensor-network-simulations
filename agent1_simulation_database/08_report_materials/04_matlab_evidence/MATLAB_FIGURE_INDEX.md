# MATLAB Figure Index

## Overview
This document indexes all MATLAB-generated figures included in the report materials. Each figure is sourced from MATLAB verification runs (S8, S9, S10, S11) and represents key network performance metrics.

## Figure Categories

### Energy Analysis Figures

| Run ID | Figure Name | Description | Report Chapter | Caption | Report Ready |
|--------|-------------|-------------|-----------------|---------|--------------|
| run_1026 | run_1026_energy_timeline.png | Energy consumption over time for S9 Stage A scenario | Energy & Longevity | "Energy consumption timeline showing deployment, network operation, and failure progression" | Yes |
| run_1026 | run_1026_node_energy.png | Per-node energy distribution and variance | Energy & Longevity | "Node-level energy residuals showing heterogeneity in energy consumption patterns" | Yes |
| run_1036 | run_1036_energy_timeline.png | Energy consumption over time for S9 Stage B scenario | Energy & Longevity | "Energy consumption timeline with self-healing recovery phases" | Yes |
| run_1036 | run_1036_node_energy.png | Per-node energy distribution for S9 Stage B | Energy & Longevity | "Node-level energy analysis across self-healing scenarios" | Yes |
| run_1039 | run_1039_energy_timeline.png | Energy consumption for S9 Stage C comparison | Energy & Longevity | "Energy consumption comparison: H0 baseline vs. active healing" | Yes |
| run_1039 | run_1039_node_energy.png | Per-node energy for Stage C | Energy & Longevity | "Node-level energy distribution in comparison scenarios" | Yes |
| run_1063 | run_1063_energy_timeline.png | Energy consumption for S11 scenario | Energy & Longevity | "Energy consumption in large-scale (5000-node) network" | Yes |
| run_1063 | run_1063_node_energy.png | Per-node energy for S11 | Energy & Longevity | "Large-scale network node energy analysis" | Yes |

### Cluster Topology Figures

| Run ID | Figure Name | Description | Report Chapter | Caption | Report Ready |
|--------|-------------|-------------|-----------------|---------|--------------|
| run_1026 | run_1026_cluster_trends.png | Cluster formation and evolution over time | Topology & Recovery | "Cluster topology trends showing formation and decay phases" | Yes |
| run_1026 | run_1026_cluster_heatmap.png | Cluster membership heatmap | Topology & Recovery | "Heatmap of cluster membership across time steps" | Yes |
| run_1036 | run_1036_cluster_trends.png | Cluster evolution in S9 Stage B | Topology & Recovery | "Cluster trends with self-healing recovery events" | Yes |
| run_1036 | run_1036_cluster_heatmap.png | Cluster membership heatmap Stage B | Topology & Recovery | "Cluster membership changes during recovery phase" | Yes |
| run_1039 | run_1039_cluster_trends.png | Cluster comparison H0 vs. healing | Topology & Recovery | "Cluster trends: H0 baseline vs. active healing comparison" | Yes |
| run_1039 | run_1039_cluster_heatmap.png | Cluster heatmap comparison | Topology & Recovery | "Cluster membership patterns in comparison scenarios" | Yes |
| run_1063 | run_1063_cluster_trends.png | Large-scale cluster trends (S11) | Topology & Recovery | "Cluster formation and recovery in 5000-node network" | Yes |
| run_1063 | run_1063_cluster_heatmap.png | Large-scale cluster heatmap | Topology & Recovery | "Large-scale cluster topology heatmap" | Yes |

### Network Timeline Figures

| Run ID | Figure Name | Description | Report Chapter | Caption | Report Ready |
|--------|-------------|-------------|-----------------|---------|--------------|
| run_1026 | run_1026_aggregate_timeline.png | Aggregate network statistics timeline | Network Performance | "Aggregate network statistics over simulation time" | Yes |
| run_1026 | run_1026_raw_timeline.png | Raw event timeline (low-level detail) | Network Performance | "Detailed timeline of network events and transitions" | Yes |
| run_1036 | run_1036_aggregate_timeline.png | Aggregate timeline Stage B | Network Performance | "Aggregate statistics with recovery phase annotation" | Yes |
| run_1036 | run_1036_raw_timeline.png | Raw timeline Stage B | Network Performance | "Event-level detail showing self-healing recovery" | Yes |
| run_1039 | run_1039_aggregate_timeline.png | Aggregate comparison H0 vs. healing | Network Performance | "Comparative timelines: H0 vs. active healing" | Yes |
| run_1039 | run_1039_raw_timeline.png | Raw event comparison | Network Performance | "Event timeline comparison across scenarios" | Yes |
| run_1063 | run_1063_aggregate_timeline.png | Large-scale aggregate timeline | Network Performance | "Aggregate performance metrics in 5000-node network" | Yes |
| run_994 | run_994_aggregate_timeline.png | Alternative aggregate timeline | Network Performance | "Aggregate timeline from secondary run" | Yes |

### Node Residual & Heatmaps

| Run ID | Figure Name | Description | Report Chapter | Caption | Report Ready |
|--------|-------------|-------------|-----------------|---------|--------------|
| run_1026 | run_1026_node_residual_heatmap.png | Node state residuals heatmap | Node Status | "Node state transitions and residual lifespan heatmap" | Yes |
| run_1036 | run_1036_node_residual_heatmap.png | Node residuals with recovery | Node Status | "Node residuals showing failure and recovery patterns" | Yes |
| run_1039 | run_1039_node_residual_heatmap.png | Comparison node residuals | Node Status | "Node residual comparison between scenarios" | Yes |
| run_1063 | run_1063_node_residual_heatmap.png | Large-scale node residuals | Node Status | "Large-scale network node state heatmap" | Yes |
| run_994 | run_994_node_residual_heatmap.png | Alternative node residuals | Node Status | "Node residuals from verification run" | Yes |

## Usage Guidelines

### For Main Report

**Prioritized for final report:**
- `run_1039_energy_timeline.png` - Direct H0 vs. healing comparison
- `run_1039_cluster_trends.png` - Cluster topology comparison
- `run_1063_energy_timeline.png` - Large-scale validation
- `run_1063_cluster_heatmap.png` - 5000-node topology proof

### For Appendices

**Useful for supplementary evidence:**
- Per-node energy heatmaps (run_1026, run_1036, run_1039, run_1063)
- Cluster membership progression (all stages)
- Raw timelines for methodology detail

### For Viva Presentation

**Best for visual communication:**
- Cluster trend figures (showing network recovery)
- Energy comparison figures (showing efficiency gains)
- Large-scale validation figures (S11)

## Data Source

- **S8 runs:** Runs 4, multiple stages validation
- **S9 runs:** Runs 1026, 1036, 1039 (stages A, B, C)
- **S10 runs:** Validation in comparison scenarios
- **S11 runs:** Run 1063 (large-scale 5000-node validation)

## Figure Formats

All figures provided in **PNG format** for:
- Embedding in PDF reports
- Web viewing and sharing
- Publication-ready resolution

PDF versions available separately in verification outputs if needed.

---

**Created:** 2025-05-12  
**MATLAB Version:** Referenced in verification documents  
**Network Simulator:** WSN Self-Healing BSBSSP
