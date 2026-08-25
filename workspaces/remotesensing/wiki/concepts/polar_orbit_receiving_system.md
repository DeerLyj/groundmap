---
title: "极轨卫星接收系统"
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
  - "[[wiki/sources/receiving_capability_poster]]"
tags:
  - polar-orbit
  - antenna
  - receiving-system
---

# 极轨卫星接收系统

> 极轨卫星接收系统通过高动态天线跟踪中低轨卫星，在短过境窗口内完成信号捕获、接收和记录。

## 定义与背景

中孟站配置 7.5 米和 5 米两套极轨接收系统，兼顾 HY、NOAA、SNPP、Aqua/Terra、Metop 等卫星任务。[[raw/papers/7.5米极轨技术指标.md#^p-5-20d22e]][[raw/papers/5米极轨和2跟7.3米静止技术指标.md#^p-3-754464]]

## 核心原理

极轨天线根据轨道预报快速指向并连续跟踪卫星。7.5 米系统支持 X 频段并可扩展 S 频段，伺服系统强调转动加速度、指向精度和程序/自动跟踪；5 米系统支持 X/L 双频。[[raw/papers/7.5米极轨技术指标.md#^p-27-75c88c]][[raw/papers/7.5米极轨技术指标.md#^p-42-fb9ed9]][[raw/papers/5米极轨和2跟7.3米静止技术指标.md#^t-7-eba595]]

## 应用与实例

- 7.5 米系统优先承担 HY-2 系列等任务，5 米系统覆盖 HY-1、Aqua/Terra、SNPP、NOAA 等并可互为补充。[[raw/papers/7.5米极轨技术指标.md#^p-375-9090ad]]
- 极轨数据进入统一解调、预处理和产品链。[[raw/assets/0b9c3539d1d35daa6bf515328c88b526.md#^h-2-3-23bc38]]

## 与其他概念的关系

- [[wiki/concepts/satellite_ground_station|PART_OF]]
- [[wiki/concepts/geostationary_receiving_system]] — 两者面向不同轨道任务，在接收体系中互补。

## 来源

- [[wiki/sources/5m_polar_2x73m_geo_system_spec]]
- [[wiki/sources/75m_polar_system_spec]]
- [[wiki/sources/receiving_capability_poster]]
