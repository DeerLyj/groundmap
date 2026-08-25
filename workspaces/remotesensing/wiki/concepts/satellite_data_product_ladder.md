---
title: "卫星遥感数据产品梯级"
type: concept
created_date: 2026-08-26
last_modified: 2026-08-26
last_modified_by: LLM
status: draft
confidence: high
source_count: 3
sources:
  - "[[wiki/sources/75m_polar_system_spec]]"
  - "[[wiki/sources/software_data_introduction]]"
  - "[[wiki/sources/automated_products_software_poster]]"
tags:
  - data-products
  - processing-pipeline
  - remote-sensing
---

# 卫星遥感数据产品梯级

> 卫星遥感数据产品梯级描述数据从原始信号、校正产品到专题分析和行业应用的逐级增值过程。

## 定义与背景

工程链路通常从解调后的 L0 数据开始，经几何定位和辐射定标生成 L1B，再生成 L2/L3 海洋产品。[[raw/papers/5米极轨和2跟7.3米静止技术指标.md#^p-45-519dcb]]

## 核心原理

运营材料进一步细分为 L1A 传感器校正、L2A 几何正射、L2B 地表反射率、L3A 专题参数、L3B 合成产品，以及 L4A 行业应用、L4B 多要素融合和 L4C 专题掩膜。[[raw/papers/软件和数据介绍.md#^t-35-41b85b]]

## 应用与实例

- 自动化产品包括海表温度、叶绿素、海面高度、风场、波高、盐度、悬浮泥沙、漫射衰减系数和 NDVI。[[raw/assets/4ea0f97c12b207b5718b84eb03743f9e.md#^h-2-1-53bb0c]]
- 产品通过自动解码、校正、反演、入库和分发流水线生成。[[raw/assets/4ea0f97c12b207b5718b84eb03743f9e.md#^h-2-2-0bfedd]]

## 与其他概念的关系

- [[wiki/concepts/satellite_ground_station]]
- [[wiki/concepts/marine_remote_sensing_applications]] — 为应用层提供标准产品。

## 来源

- [[wiki/sources/75m_polar_system_spec]]
- [[wiki/sources/software_data_introduction]]
- [[wiki/sources/automated_products_software_poster]]
