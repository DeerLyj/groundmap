---
title: "卫星遥感地面站"
type: concept
created_date: 2026-08-26
last_modified: 2026-08-26
last_modified_by: LLM
status: draft
confidence: high
source_count: 5
sources:
  - "[[wiki/sources/5m_polar_2x73m_geo_system_spec]]"
  - "[[wiki/sources/75m_polar_system_spec]]"
  - "[[wiki/sources/brochure_cn_en_2026]]"
  - "[[wiki/sources/software_data_introduction]]"
  - "[[wiki/sources/receiving_capability_poster]]"
tags:
  - satellite-ground-station
  - remote-sensing
  - infrastructure
---

# 卫星遥感地面站

> 卫星遥感地面站是把卫星下行信号转化为标准数据、专题产品和业务服务的地面基础设施。

## 定义与背景

典型系统同时包含天线与射频前端、伺服跟踪、解调记录、站控监视、数据预处理、产品生产、存储和分发。中孟项目以多套极轨和静止天线构成统一站网，并要求全天候、无人值守和远程控制。[[raw/papers/5米极轨和2跟7.3米静止技术指标.md#^p-33-5f06ef]][[raw/papers/7.5米极轨技术指标.md#^p-238-618e3c]]

## 核心原理

数据链从轨道预报和天线指向开始，经信号捕获、跟踪、解调形成 L0 数据，再进行几何定位、辐射定标和专题反演，生成 L1B、L2、L3 及更高层业务产品。[[raw/papers/5米极轨和2跟7.3米静止技术指标.md#^p-45-519dcb]][[raw/assets/0b9c3539d1d35daa6bf515328c88b526.md#^h-2-3-23bc38]]

## 应用与实例

- 多星接收与气象、海洋、环境数据服务。[[raw/papers/brochure_CN-EN(1).md#^h-2-3-851902]]
- 赤潮、气旋、洪水和渔业等专题应用。[[raw/papers/brochure_CN-EN(1).md#^h-2-4-1e5f7f]][[raw/papers/brochure_CN-EN(1).md#^h-2-7-2b1889]]
- 产品推送、数据看板和业务软件定制。[[raw/papers/brochure_CN-EN(1).md#^h-2-9-c37683]]

## 与其他概念的关系

- [[wiki/concepts/polar_orbit_receiving_system]] — 极轨任务接收子系统。
- [[wiki/concepts/geostationary_receiving_system]] — 静止卫星连续观测子系统。
- [[wiki/concepts/satellite_data_product_ladder]] — 数据加工与产品分级。
- [[wiki/concepts/three_level_station_management]] — 跨站运控与管理架构。

## 来源

- [[wiki/sources/5m_polar_2x73m_geo_system_spec]]
- [[wiki/sources/75m_polar_system_spec]]
- [[wiki/sources/brochure_cn_en_2026]]
- [[wiki/sources/software_data_introduction]]
- [[wiki/sources/receiving_capability_poster]]
