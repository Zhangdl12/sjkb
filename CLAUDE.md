# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 启动命令

```bash
streamlit run main.py
```

依赖项（无 requirements.txt）：`streamlit`、`pandas`、`numpy`、`st-aggrid`（仅标签检验表使用）。

## 架构概览

基于 Streamlit 多页面模式的数据看板系统，用于分析广告创意数据。**一个共享 Excel 数据源，多个业务看板复用。** 架构采用工具库模式——每个页面独立编写完整的数据加载、加工、筛选、渲染流程，共用 `app/core/` 下的工具函数。

### 分层结构

```
main.py                     → 首页：上传 Excel → 存入 session_state
pages/*.py                  → 看板页面：独立完整的数据分析流程
app/core/                   → 工具层：session_state 管理、Excel 加载、筛选器
app/dashboards/<name>/      → 业务层：config（列名常量）+ processor/metrics/ui
```

### 共享数据源机制

`app/core/shared_source.py` 管理三个 session_state 键：

- `shared_source_name` — 文件名（显示用）
- `shared_source_bytes` — 原始文件字节
- `shared_source_token` — `md5(bytes)`，用作缓存键

`load_shared_workbook` 在 `app/core/loader.py` 中，用 `@st.cache_data` 缓存，确保同一文件只解析一次。

### 页面编写模式

每个看板页面按固定步骤编写，控制流在页面文件中显式可见：

```
1. st.set_page_config(...)                  # 页面配置
2. has_shared_source() 检查                 # 确保已上传数据源
3. load_shared_workbook()                   # 缓存加载 Excel
4. select_required_sheets(workbook, {...})  # 按别名提取工作表
5. build_dataset(tables, config)            # 业务加工 → 分析宽表
6. render_sidebar_filters() + apply_filters()  # 可选，筛选器
7. 空数据检查 → render_empty_state()
8. 指标计算 + 透视表构建
9. render_summary() → render_pivot_table() → render_detail_section()
```

### 筛选器联动收敛

`app/core/filters.py` 中的 `render_sidebar_filters` 按分组渲染多选筛选器。每次渲染下一个筛选器时，先用已选值过滤数据，再提取可选值——实现下游选项随上游选择动态收敛。

### 新增看板步骤

1. 在 `app/dashboards/<name>/` 创建目录，至少包含 `config.py`（列名常量的 `AppConfig` dataclass）
2. 可选：`processor.py`（数据加工）、`metrics.py`（指标）、`ui.py`（渲染）
3. 在 `pages/` 下新建 `0X_名称.py`，按上述页面编写模式实现完整流程
4. 无需修改 `main.py`、`app/core/` 中任何文件或其他页面

### 两个业务看板

| 看板 | 数据表 | 功能 |
|---|---|---|
| 素材分析 | 3 张（计划类型匹配、创意数据、商品匹配） | 展现/点击/花费/GMV 指标卡 + 分组透视表 + CSV 导出，7 个筛选器 |
| 标签检验 | 2 张（关键词匹配、关键词数据） | st_aggrid 两级树状表（类别→关键词），按费用降序，无筛选器 |
