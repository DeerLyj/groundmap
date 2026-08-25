---
title: "三级卫星地面站管理体系"
type: concept
created_date: 2026-08-26
last_modified: 2026-08-26
last_modified_by: LLM
status: draft
confidence: high
source_count: 2
sources:
  - "[[wiki/sources/75m_polar_system_spec]]"
  - "[[wiki/sources/automated_products_software_poster]]"
tags:
  - station-control
  - operations
  - distributed-system
---

# 三级卫星地面站管理体系

> 三级站管体系以中心运控、站级一体化管理和设备前端控制分层管理跨地域地面站。

## 定义与背景

总体方案采用一级运控/数据处理中心、二级站级一体化运管和三级前端站控结构，各站设备配置与任务信息向中心汇聚。[[raw/papers/7.5米极轨技术指标.md#^p-238-618e3c]]

## 核心原理

一级负责全局任务、数据融合和运维统筹；二级负责单站任务编排、状态汇总与本地业务；三级直接控制天线、接收设备、供配电和环境监控。软件层对应天线控制、实时数据处理、卫星状态监控和数据管理模块。[[raw/assets/4ea0f97c12b207b5718b84eb03743f9e.md#^h-2-3-436252]]

## 应用与实例

- 外站脱网时可保留任务参数并独立运行，恢复网络后再同步状态与数据。[[raw/papers/7.5米极轨技术指标.md#^p-209-53fdd9]]
- 中心站通过 VPN 接收外站产品与设备信息。[[raw/papers/7.5米极轨技术指标.md#^p-494-1cf377]]

## 与其他概念的关系

- [[wiki/concepts/satellite_ground_station]]
- [[wiki/concepts/indian_ocean_station_network]]

## 来源

- [[wiki/sources/75m_polar_system_spec]]
- [[wiki/sources/automated_products_software_poster]]
