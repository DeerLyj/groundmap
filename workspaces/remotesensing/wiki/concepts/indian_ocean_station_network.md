---
title: "环印度洋卫星地面站网络"
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
  - "[[wiki/sources/software_data_introduction]]"
tags:
  - station-network
  - indian-ocean
  - distributed-system
---

# 环印度洋卫星地面站网络

> 环印度洋卫星地面站网络是以中心站统筹多个海外接收站，通过专网回传和统一处理扩大卫星覆盖与区域服务能力的分布式体系。

## 定义与背景

工程材料规划 A、B、C、D 四站点，分布于东亚、南亚和非洲东海岸，覆盖环印度洋大范围区域。[[raw/papers/5米极轨和2跟7.3米静止技术指标.md#^p-44-d09ae5]]

## 核心原理

外站承担本地卫星接收、预处理和缓存，三级产品、设备状态、频谱和监控信息通过 VPN 或其他链路回传中心站，中心站完成融合、发布和统一运控。[[raw/papers/7.5米极轨技术指标.md#^p-494-1cf377]][[raw/papers/5米极轨和2跟7.3米静止技术指标.md#^p-45-519dcb]]

## 应用与实例

运营材料将临安、吉大港、阿曼和马达加斯加列为四个核心节点，其中部分节点仍处于建设或投运阶段。[[raw/papers/软件和数据介绍.md#^p-5-b49208]]

## 与其他概念的关系

- [[wiki/concepts/three_level_station_management]] — 网络运行依赖分层站控。
- [[wiki/entities/china_bangladesh_ground_station]] — 吉大港节点是南亚站点。
- [[wiki/concepts/satellite_ground_station]] — 多站协同的地面站体系。

## 来源

- [[wiki/sources/5m_polar_2x73m_geo_system_spec]]
- [[wiki/sources/75m_polar_system_spec]]
- [[wiki/sources/software_data_introduction]]
