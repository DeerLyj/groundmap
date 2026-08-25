---
title: "全球卫星测控与地面接收网：软件和数据介绍"
type: source_summary
created_date: 2026-08-25
last_modified: 2026-08-25
last_modified_by: LLM
status: draft
confidence: high
source_count: 1
sources:
  - "[[raw/papers/软件和数据介绍.md]]"
tags:
  - satellite-network
  - ground-station
  - software
  - data-products
  - remote-sensing
---

# 全球卫星测控与地面接收网：软件和数据介绍

> **原始文件**：[[raw/papers/软件和数据介绍.md]]
> **类型**：运营能力与软件平台介绍（PPT 转写）
> **覆盖**：全球四站布局、卫星资源池、数字大脑软件、定标体系、L0-L4 产品与典型应用

## 核心论点

1. 依托国家级重点实验室，全球布局四座核心卫星地面站：杭州临安站（全球运控与数据处理大脑，稳定运营 2 年）、孟加拉吉大港大学站（2500 m²，含 300 m² 专属数据中心，试运营半年）、阿曼苏丹卡布斯大学站、马达加斯加塔那那利佛大学站（预计 2026-12 投运）[[raw/papers/软件和数据介绍.md#^p-5-b49208]]。
2. 全谱系卫星数据资源池覆盖亚米/高分（GF、ZY、吉林一号、吉利星座）、静止高频（FY-4A/4B、Himawari-9，10～15 分钟重访）、宽幅中分（Landsat-8/9、TERRA/AQUA/CBERS）、微波雷达（HY-2A/B/C/D、Metop-B）、高光谱（CM1、HY-1C/1D、HJ）与经典气象海洋（NOAA、SNPP、FY-3D/3E）[[raw/papers/软件和数据介绍.md#^p-10-3fcf56]]。
3. “数字大脑”提供全域数字孪生站管系统（3D 地球实时展示、底层硬件直控、可视化编排接收计划）与 AI 驱动的遥感数据管线；遥感大模型 RS-LLM 正在筹备上线 [[raw/papers/软件和数据介绍.md#^p-13-1a4410]][[raw/papers/软件和数据介绍.md#^p-18-0b9954]]。
4. 分级产品体系为 L1A 传感器校正、L2A 几何正射、L2B 地表反射率、L3A 专题产品、L3B 季度/年度合成、L4A 行业应用、L4B 多要素融合、L4C 专题掩膜，并配套辐射/几何/大气校正与人工抽检质控 [[raw/papers/软件和数据介绍.md#^t-35-41b85b]]。
5. 定向分发支持 FTP、API、硬盘、专线等方式，本地算力可 2 小时内生产应急区产品 [[raw/papers/软件和数据介绍.md#^p-59-4498a3]]。

## 数据要点

| 维度 | 内容 |
|---|---|
| 全球站点 | 临安（运营 2 年）、吉大港（试运营半年）、阿曼、马达加斯加（2026-12 投运） |
| 静止卫星重访 | 10～15 分钟（FY-4A/4B、Himawari-9） |
| 中分宽幅 | 10～30 米，单景可达 185 km 宽幅（Landsat 等） |
| 产品级别 | L1A / L2A / L2B / L3A / L3B / L4A / L4B / L4C |
| 农业效益案例 | 粮食作物亩均增收 150～200 元；经济作物亩均增收 700～1000 元 |
| 农险定损 | 0.5 小时全域扫描、精度 95%、面积误差 <5%、理赔争议下降 70% |

## 方法/做法

- 定标与仪器体系：美国 ASD 高光谱地物光谱仪、SPMR 水下高光谱剖面仪、AC-S 吸收衰减测量仪、自研水下显微成像仪，并计划商业化整合定标场网络 [[raw/papers/软件和数据介绍.md#^p-23-783990]]。
- 应用场景覆盖生态环境监测（水质、火点、违建）、应急防灾（洪涝、森林火灾）、农业（估产、保险定损、碳汇）与海洋（赤潮、海岸线、渔场、围填海监测）[[raw/papers/软件和数据介绍.md#^p-94-79c3ec]][[raw/papers/软件和数据介绍.md#^p-100-3b32ca]][[raw/papers/软件和数据介绍.md#^p-125-be3de5]]。

## AI 综合判断（基于 wiki 现状）

### 核心价值

给出运营级“站网 + 软件 + 产品”全景：四站网络、卫星资源池、L0-L4 产品分级和农业/灾害/海洋应用案例，是对两本技术规格书的商业运营视角补充。

### 关联

- [[wiki/concepts/satellite_ground_station]]：站网与数据链路
- [[wiki/concepts/satellite_data_product_ladder]]：L0-L4 产品分级
- [[wiki/concepts/indian_ocean_station_network]]：全球/环印度洋站点布局
- [[wiki/concepts/marine_remote_sensing_applications]]：海洋应用场景
- [[wiki/entities/china_bangladesh_ground_station]]：南亚节点

### 冲突

无。农业案例数字为商业宣传口径，与规格文件的技术指标不构成冲突。
