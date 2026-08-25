---
title: "7.5米极轨卫星接收系统技术指标与总体方案"
type: source_summary
created_date: 2026-08-25
last_modified: 2026-08-25
last_modified_by: LLM
status: draft
confidence: high
source_count: 1
sources:
  - "[[raw/papers/7.5米极轨技术指标.md]]"
tags:
  - polar-orbit
  - antenna-spec
  - station-control
  - data-storage
  - remote-sensing
---

# 7.5米极轨卫星接收系统技术指标与总体方案

> **原始文件**：[[raw/papers/7.5米极轨技术指标.md]]
> **类型**：遥感卫星地面站技术规格书（7.5米极轨系统 + 全站总体方案）
> **覆盖**：系统功能、天馈/伺服/接收/监控/记录分系统、测试设备、可靠性优化、三级站控、存储与分发、预处理

## 核心论点

1. 系统用于搜集接收遥感卫星覆盖范围内的遥感资料，探测海洋气象、海洋水文、海洋生态和地球物理等要素，具备 HY-1C/1D、HY-2B/2C、NOAA18/19/20、SNPP、Metop-B 等多卫星接收能力，一站多星、全天候全天时，覆盖中低轨 300～1500 公里 [[raw/papers/7.5米极轨技术指标.md#^p-3-8dae99]][[raw/papers/7.5米极轨技术指标.md#^p-5-20d22e]][[raw/papers/7.5米极轨技术指标.md#^p-6-672f5e]]。
2. 天馈分系统为不小于 7.3 米卡塞格伦天线，X 频段 7.7～8.5 GHz（可扩充 S 频段 1.6～2.4 GHz），增益 ≥53.7+20log(f/8.2) dBi，RHCP/LHCP，基座为 X/Y+倾斜三轴或 X/Y 型 [[raw/papers/7.5米极轨技术指标.md#^p-27-75c88c]][[raw/papers/7.5米极轨技术指标.md#^p-28-baaca8]][[raw/papers/7.5米极轨技术指标.md#^p-30-380364]][[raw/papers/7.5米极轨技术指标.md#^p-35-6061ed]]。
3. 伺服系统转动加速度 ≥5°/s²，跟踪精度优于 0.1 倍半功率波束宽度，指向精度 ≤0.06°，支持手动、程序、单脉冲自动跟踪 [[raw/papers/7.5米极轨技术指标.md#^p-42-fb9ed9]][[raw/papers/7.5米极轨技术指标.md#^p-43-1b35cc]][[raw/papers/7.5米极轨技术指标.md#^p-44-33ba01]]。
4. 接收信道 LNA 噪声温度 ≤60 K（23℃），解调支持 BPSK/QPSK/8PSK/16QAM/16APSK/32APSK 等，信息速率 1 Mbps～200 Mbps，具备 Viterbi/RS/LDPC/Turbo 译码 [[raw/papers/7.5米极轨技术指标.md#^p-53-c0da86]][[raw/papers/7.5米极轨技术指标.md#^p-112-f72b89]][[raw/papers/7.5米极轨技术指标.md#^p-113-9cde42]]。
5. 记录分系统无人值守自动处理，单轨处理时间小于 2 小时、多源融合处理小于 4 小时，可稳定处理和分发雷达高度计、微波散射计、扫描微波辐射计、校正微波辐射计等试验产品 [[raw/papers/7.5米极轨技术指标.md#^p-153-add585]][[raw/papers/7.5米极轨技术指标.md#^p-154-d0029b]]。

## 数据要点

| 项目 | 指标 |
|---|---|
| 天线口径/型式 | ≥7.3 米卡塞格伦 |
| 工作频段 | X 7.7～8.5 GHz；可扩 S 1.6～2.4 GHz |
| 天线增益 | ≥53.7+20log(f/8.2) dBi |
| 伺服加速度 | ≥5°/s²；指向精度 ≤0.06° |
| LNA 噪声温度 | ≤60 K（23℃） |
| 解调速率 | 1 Mbps～200 Mbps |
| 处理时效 | 单轨 <2 h；多源融合 <4 h |
| A站存储 | 30×8 T HDD RAID5E，实际容量 224 T（可用 218 T），约存 480 天 |
| B/C站存储 | 同规格 224 T，约存 500 天 |

## 方法/做法

- 全系统为“1 级运控/数据处理中心 + A/B/C 站 2 级一体化运管 + 每站 3 级前端站控”三级架构，每站配置 1 套 7.5 米、1 套 5 米、2 套 7.3 米接收站，站点配置相同 [[raw/papers/7.5米极轨技术指标.md#^p-238-618e3c]]。
- 天线任务分工：7.5 米默认接收 HY-2B/2C 并兼顾 HY-1C/1D、NOAA18/19、SNPP、NOAA20、Metop-B；5 米默认接收 HY-1C/1D、AQUA/TERRA、SNPP、NOAA 等并兼顾 HY-2B/2C；7.3 米-1 收 FY4-HRIT1 通道、7.3 米-2 收 FY4-HRIT2 通道 [[raw/papers/7.5米极轨技术指标.md#^p-375-9090ad]][[raw/papers/7.5米极轨技术指标.md#^p-376-c2903c]][[raw/papers/7.5米极轨技术指标.md#^p-377-1cfd47]]。
- 可靠性设计：7.5 米与 5 米链路经射频/中频矩阵互为备份；每站 UPS + 柴油发电机应对异常断电；前端站脱网可保存 72 小时任务参数独立运行；智能 PDU 支持远程加去电；系统虚拟化与远程健康管理 [[raw/papers/7.5米极轨技术指标.md#^p-188-44a203]][[raw/papers/7.5米极轨技术指标.md#^p-199-5ec552]][[raw/papers/7.5米极轨技术指标.md#^p-209-53fdd9]][[raw/papers/7.5米极轨技术指标.md#^p-211-97e5c4]][[raw/papers/7.5米极轨技术指标.md#^p-219-b450ef]]。
- 分工界面：北京无线电测量研究所（23所）与中国电科三十九所（39所）共建，最终用户为海洋二所（2所）；39所负责天线基础、机房与操作台，23所负责杭州远控布局与设备 [[raw/papers/7.5米极轨技术指标.md#^p-232-98444e]]。
- 数据传输：B/C 站通过本地互联网与 A 站运控中心搭建 VPN 隧道回传三级产品、设备状态、频谱与监控信息；数据压缩加速设备实测使外站 100M/北京 300M 带宽回传从 7～8 Mbps 提升至 15～25 Mbps [[raw/papers/7.5米极轨技术指标.md#^p-494-1cf377]][[raw/papers/7.5米极轨技术指标.md#^p-496-00b72a]]。
- 预处理：海洋系列卫星数据先处理成 0 级再处理成 1 级，生成标准 HDF4/HDF5 输出给后端反演系统生产 3 级产品；极轨气象卫星预处理覆盖 NOAA18/19、METOP-B 与 SNPP、NOAA20、AQUA、TERRA 共 7 颗 [[raw/papers/7.5米极轨技术指标.md#^p-508-812671]][[raw/papers/7.5米极轨技术指标.md#^p-523-8c1487]]。

## AI 综合判断（基于 wiki 现状）

### 核心价值

7.5 米极轨系统的完整技术指标与全站总体方案，明确三级站控软件、存储容量规划、VPN 回传与预处理流程，是理解地面站工程实现的骨架文件。

### 关联

- [[wiki/concepts/satellite_ground_station]]：全站总体方案
- [[wiki/concepts/polar_orbit_receiving_system]]：7.5 米极轨子系统
- [[wiki/concepts/three_level_station_management]]：三级站控体系
- [[wiki/concepts/satellite_data_product_ladder]]：0/1 级 HDF 与 3 级产品
- [[wiki/sources/5m_polar_2x73m_geo_system_spec]]：同项目另一份规格书

### 冲突

无实质冲突。宣传册称两套 7.3 米天线当前分别用于 FY-4B 与 Himawari-9，本文规定 7.3 米-1/-2 接收 FY4-HRIT1/2 通道，二者是否同一时期安排需人工确认，已在中英文宣传册摘要页登记。[[raw/papers/brochure_CN-EN(1).md#^h-2-2-a9ae57]][[raw/papers/7.5米极轨技术指标.md#^p-376-c2903c]][[raw/papers/7.5米极轨技术指标.md#^p-377-1cfd47]]
