# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## 启动命令

```bash
streamlit run main.py
```

主要依赖：`streamlit`、`pandas`、`numpy`、`streamlit-aggrid`、`openpyxl`。

## 架构概览

这是一个基于 Streamlit 多页面模式的数据分析看板。首页上传业务数据源和打标文件，各页面复用 `app/core/` 中的共享会话、Excel 加载和筛选器能力。

```text
main.py                     -> 首页：上传 Excel 并写入 session_state
pages/*.py                  -> 页面入口：检查数据源、加载数据、调用业务模块渲染
app/core/                   -> 公共能力：session_state、Excel 加载、筛选器、页面状态
app/dashboards/<name>/      -> 业务层：config、processor、service、tree_builder、ui
tests/                      -> 回归测试
```

## 当前业务页面

| 页面 | 模块 | 说明 |
|---|---|---|
| 标签检验表 | `tag_validation` | 关键词、人群、SKU 标签检验 |
| 广告数据汇总 | `ad_summary` | 多来源广告与店铺数据周期汇总 |
| 渠道分析 | `channel_analysis` | 按渠道、商品和时间分析广告表现 |
| 关键词分析 | `keyword_analysis` | 按词性、关键词和时间分析投放表现 |
| 人群分析 | `audience_analysis` | 按人群分类和时间分析投放表现 |
| CPS分析 | `cps_analysis` | 按团长、日期、产品汇总 CPS 计佣金额和佣金 |

## 页面编写模式

1. `st.set_page_config(...)` 设置页面。
2. `has_shared_source()` 和需要时的 `has_tag_source()` 做数据源检查。
3. 读取共享文件字节和 token。
4. 调用对应 service 的 dataset 加载函数。
5. 使用 `render_sidebar_filters()` 渲染筛选器。
6. 调用 payload 加载函数生成最终展示表。
7. 调用业务模块的 `ui.py` 渲染页面。

## 开发要求

- 保持页面薄、业务逻辑进 `app/dashboards/<name>/`。
- 新增看板优先沿用现有 `config / processor / service / tree_builder / ui` 结构。
- Excel 字段名集中写入 `AppConfig`，不要散落在页面里。
- 运行验证优先使用：

```bash
python -m unittest discover tests
```
