---
title: "静止卫星接收系统"
type: concept
created_date: 2026-08-26
last_modified: 2026-08-26
last_modified_by: LLM
status: draft
confidence: high
source_count: 3
sources:
  - "[[wiki/sources/5m_polar_2x73m_geo_system_spec]]"
  - "[[wiki/sources/75m_polar_system_spec]]"
  - "[[wiki/sources/brochure_cn_en_2026]]"
tags:
  - geostationary
  - antenna
  - receiving-system
---

# 静止卫星接收系统

> 静止卫星接收系统面向固定轨位卫星进行长时间连续接收，适合高频区域气象与环境观测。

## 定义与背景

中孟站配置两套 7.3 米 L 频段静止天线，采用方位俯仰座架、正交线极化，支持程序跟踪和手动跟踪。[[raw/papers/5米极轨和2跟7.3米静止技术指标.md#^p-10-b4b9ac]][[raw/papers/5米极轨和2跟7.3米静止技术指标.md#^p-15-bd8a23]]

## 核心原理

静止卫星相对地面站方向基本稳定，接收系统以固定轨位指向和长期连续运行获得高时间分辨率数据。当前公开材料把两套天线任务分别表述为 FY-4B 和 Himawari-9。[[raw/papers/brochure_CN-EN(1).md#^h-2-2-a9ae57]]

## 应用与实例

- FY-4B 和 Himawari-9 支持气象云图与连续区域观测。[[raw/papers/brochure_CN-EN(1).md#^h-2-3-851902]]
- 静止高频数据可与极轨高空间分辨率数据协同。[[raw/papers/软件和数据介绍.md#^p-10-3fcf56]]

## 与其他概念的关系

- [[wiki/concepts/satellite_ground_station|PART_OF]]
- [[wiki/concepts/polar_orbit_receiving_system]] — 在轨道与重访特性上形成互补。

## 来源

- [[wiki/sources/5m_polar_2x73m_geo_system_spec]]
- [[wiki/sources/75m_polar_system_spec]]
- [[wiki/sources/brochure_cn_en_2026]]

> [!WARNING] 知识更新冲突 — 2026-08-26
> **旧观点**：工程规格把两套静止天线任务写为 FY4-HRIT1 与 FY4-HRIT2 通道 [[raw/papers/7.5米极轨技术指标.md#^p-376-c2903c]][[raw/papers/7.5米极轨技术指标.md#^p-377-1cfd47]]。
> **新证据**：建成后的宣传册写为 FY-4B 与 Himawari-9 [[raw/papers/brochure_CN-EN(1).md#^h-2-2-a9ae57]]。
> **LLM 判断**：更可能是设计任务与建成运行任务的阶段差异，仍需运行记录确认。
> **状态**：⏳ 待人类判别
