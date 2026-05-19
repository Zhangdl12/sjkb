# 数据分析看板

一个基于 `Streamlit` 的 Excel 驱动型数据看板项目。首页上传业务数据源和打标文件后，各业务页面从会话状态中复用同一份文件内容，避免重复上传和重复解析。

## 当前页面

- 标签检验表
- 广告数据汇总
- 渠道分析
- 关键词分析
- 人群分析
- CPS分析

## 启动方式

```bash
streamlit run main.py
```

启动后：

1. 在首页上传业务数据源 Excel。
2. 需要打标能力的页面继续上传打标 Excel。
3. 从 Streamlit 侧栏进入对应业务页面。

## 核心结构

```text
main.py
pages/
├─ 01_标签检验表.py
├─ 03_广告数据汇总.py
├─ 04_渠道分析.py
├─ 05_关键词分析.py
├─ 06_人群分析.py
└─ 07_CPS分析.py
app/
├─ core/
│  ├─ filters.py
│  ├─ loader.py
│  ├─ page_state.py
│  ├─ session_loader.py
│  └─ shared_source.py
└─ dashboards/
   ├─ ad_summary/
   ├─ audience_analysis/
   ├─ channel_analysis/
   ├─ cps_analysis/
   ├─ keyword_analysis/
   └─ tag_validation/
tests/
```

## 数据流

```text
Excel 文件
  -> main.py 上传
  -> app/core/shared_source.py 写入 session_state
  -> app/core/loader.py 按需读取 sheet
  -> app/dashboards/<dashboard>/processor.py 归一化明细
  -> app/dashboards/<dashboard>/service.py 应用筛选并缓存展示载荷
  -> app/dashboards/<dashboard>/ui.py 渲染 AgGrid 或 Streamlit 组件
```

## 开发约定

- `main.py` 只负责共享数据源和打标文件上传管理。
- `pages/*.py` 只做页面编排，不承载复杂业务逻辑。
- `app/core/*` 放跨看板复用能力。
- `app/dashboards/*` 放具体业务看板实现。
- 新增页面时优先复用现有 `config / processor / service / tree_builder / ui` 分层。
- 修改前后运行 `python -m unittest discover tests` 做回归验证。

## 测试

```bash
python -m unittest discover tests
```

当前测试覆盖共享加载、筛选器、标签检验、广告汇总、渠道分析、关键词分析、人群分析、CPS分析等核心逻辑。
