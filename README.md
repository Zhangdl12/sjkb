# 素材分析看板

一个基于 `Streamlit` 的 Excel 驱动型数据看板项目。首页只负责上传一次共享 Excel，侧栏中的 3 个业务页面复用同一份会话内数据源，分别完成：

- 标签检验表
- 素材分析
- 广告数据汇总

项目当前重点不是“通用 BI 平台”，而是围绕固定业务表结构做快速分析、汇总和展示。

## 1. 项目目标

这个项目解决的是同一份 Excel 数据在多个看板里重复上传、重复解析、重复写逻辑的问题。

当前方案的核心思路是：

1. 首页上传共享 Excel。
2. `app/core/shared_source.py` 把文件名、原始字节、缓存 token 存进 `st.session_state`。
3. 各业务页通过 `app/core/loader.py` 统一加载工作簿。
4. 每个看板只关心自己的配置、数据加工、指标计算和 UI 渲染。

这样分层以后，新增页面不需要再复制上传逻辑，也不需要在页面里混写所有业务代码。

## 2. 功能概览

### 2.1 首页

- 上传共享 Excel 数据源
- 显示当前数据源名称
- 清空当前会话中的共享数据源

### 2.2 标签检验表

- 关键词标签检验
- 人群标签检验
- SKU 标签检验
- 使用 AgGrid 树形表展示“分类 -> 子项”的两级结构

### 2.3 素材分析

- 侧边栏联动筛选
- 核心指标卡
- 分组透视表
- 明细预览与 CSV 导出

### 2.4 广告数据汇总

- 按季度、月、周、日四个周期汇总
- 生成各周期汇总表与总计表
- 计算环比、同比、ROI、费比、目标完成进度等指标

## 3. 技术栈

- `Python`
- `Streamlit`
- `pandas`
- `numpy`
- `streamlit-aggrid`
- `unittest`

说明：

- 仓库里目前没有 `requirements.txt` 或 `pyproject.toml`。
- 依赖是从源码导入关系反推出来的，后续建议补一个依赖文件。

## 4. 启动方式

先安装依赖：

```bash
pip install streamlit pandas numpy streamlit-aggrid
```

启动项目：

```bash
streamlit run main.py
```

启动后流程：

1. 先在首页上传 Excel。
2. 再从 Streamlit 侧栏进入业务页面。
3. 所有业务页面共享当前会话中的同一份 Excel 数据源。

## 5. 数据流说明

完整数据流如下：

```text
Excel 文件
  -> main.py 上传
  -> app/core/shared_source.py 写入 session_state
  -> app/core/loader.py 解析整个 workbook
  -> 各页面 select_required_sheets() 取本页需要的工作表
  -> dashboard/config.py 定义字段与表名
  -> dashboard/processor.py 做清洗、合并、派生字段
  -> dashboard/metrics.py 计算指标（部分页面）
  -> dashboard/ui.py 渲染页面
```

分层职责：

- `main.py`
  只负责共享数据源管理，不做业务分析。
- `pages/*.py`
  只做页面编排，不承载复杂业务细节。
- `app/core/*`
  放跨看板通用能力。
- `app/dashboards/*`
  放具体业务看板实现。
- `tests/*`
  放关键逻辑的回归测试。

## 6. 目录结构

下面是当前仓库中“源码和文档层面”的有效目录结构，`__pycache__`、`.pyc` 这类运行产物未展开：

```text
素材分析看板/
├─ main.py
├─ README.md
├─ CLAUDE.md
├─ 重构后开发说明.md
├─ 惠氏数据源(新).xlsx
├─ pages/
│  ├─ 01_标签检验表.py
│  ├─ 02_素材分析.py
│  └─ 03_广告数据汇总.py
├─ app/
│  ├─ __init__.py
│  ├─ core/
│  │  ├─ __init__.py
│  │  ├─ shared_source.py
│  │  ├─ loader.py
│  │  └─ filters.py
│  └─ dashboards/
│     ├─ __init__.py
│     ├─ tag_validation/
│     │  ├─ __init__.py
│     │  ├─ config.py
│     │  ├─ loader.py
│     │  ├─ processor.py
│     │  ├─ tree_builder.py
│     │  └─ ui.py
│     ├─ material_analysis/
│     │  ├─ __init__.py
│     │  ├─ config.py
│     │  ├─ loader.py
│     │  ├─ processor.py
│     │  ├─ metrics.py
│     │  └─ ui.py
│     └─ ad_summary/
│        ├─ __init__.py
│        ├─ config.py
│        ├─ processor.py
│        ├─ metrics.py
│        └─ ui.py
└─ tests/
   ├─ test_tag_validation_sku_name.py
   └─ test_ad_summary_metrics.py
```

## 7. 每一层是干什么的

### 7.1 顶层文件

#### `main.py`

项目首页入口。

负责：

- 设置首页标题和页面布局
- 上传共享 Excel
- 调用 `set_shared_source()` 保存文件到 `session_state`
- 显示当前共享数据源
- 提供“清空数据源”按钮

不负责：

- 业务数据加工
- 指标计算
- 具体看板展示

#### `README.md`

项目说明文档，也就是你现在看到的这份文件。

#### `CLAUDE.md`

协作/开发约束文档，主要给编码代理或协作者看，不参与业务运行。

#### `重构后开发说明.md`

历史重构说明文档，用来说明此前的重构思路和目录约定。它是辅助文档，不是运行入口。

#### `惠氏数据源(新).xlsx`

本地示例数据源文件。它更像开发测试数据，不属于应用代码。

## 8. `pages/` 页面入口层

`pages/` 是 Streamlit 的多页面入口目录。这里的文件会自动出现在侧栏。

这一层的原则是：

- 负责页面编排
- 负责调用公共层与看板层
- 不把复杂业务逻辑堆在页面文件里

### `pages/01_标签检验表.py`

标签检验页入口。

主要流程：

1. 校验首页是否已上传共享数据源。
2. 加载整个 workbook。
3. 一次性取出关键词、人群、SKU 需要的 6 张表。
4. 分别调用 `processor.py` 生成 3 份明细数据。
5. 调用 `tree_builder.py` 组装树形表数据。
6. 调用 `ui.py` 渲染 3 个标签页。

### `pages/02_素材分析.py`

素材分析页入口。

主要流程：

1. 校验共享数据源。
2. 取出素材分析需要的 3 张表。
3. 调用 `build_analysis_dataset()` 生成分析宽表。
4. 调用 `render_sidebar_filters()` 渲染联动筛选器。
5. 调用 `calculate_summary_metrics()` 和 `build_pivot_table()` 产出指标与透视表。
6. 调用 `ui.py` 渲染指标卡、透视表、明细区。

### `pages/03_广告数据汇总.py`

广告数据汇总页入口。

主要流程：

1. 校验共享数据源。
2. 取出广告、店铺、SKU、计划、目标共 5 张表。
3. 调用 `build_ad_summary_dataset()` 整合成日级明细。
4. 使用通用筛选器按时间和业务维度过滤。
5. 分别按季度、月、周、日生成汇总表和总计表。
6. 调用 `ad_summary/ui.py` 渲染结果。

## 9. `app/core/` 公共能力层

这一层放的是多个页面可复用的“基础设施”能力。

### `app/__init__.py`

声明 `app` 是应用主包，本身不承载业务逻辑。

### `app/core/__init__.py`

声明 `core` 是公共能力包。

### `app/core/shared_source.py`

共享数据源会话管理模块。

核心作用：

- 把首页上传的文件缓存到 `st.session_state`
- 维护 3 个关键键值：
  - `shared_source_name`
  - `shared_source_bytes`
  - `shared_source_token`

主要函数：

- `set_shared_source()`：保存上传文件
- `clear_shared_source()`：清空当前会话数据源
- `has_shared_source()`：判断是否已上传
- `get_shared_source_name()`：取文件名
- `get_shared_source_bytes()`：取原始字节
- `get_shared_source_token()`：取 md5 token，供缓存使用

### `app/core/loader.py`

通用 Excel 加载层。

核心作用：

- 读取 Excel
- 缓存整个 workbook
- 从 workbook 中提取页面所需工作表

主要函数：

- `load_excel_sheets()`：独立读取指定工作表
- `load_shared_workbook()`：从共享字节加载并缓存整本工作簿
- `select_required_sheets()`：按映射提取页面需要的表

这个文件是“上传文件”和“业务页面”之间的桥梁。

### `app/core/filters.py`

通用侧边栏筛选器模块。

核心作用：

- 定义筛选器结构 `FilterField`
- 渲染按组展示的侧边栏多选器
- 支持联动收敛选项
- 按声明顺序对 DataFrame 应用筛选

主要函数：

- `build_filter_options()`
- `render_sidebar_filters()`
- `apply_filters()`

这个模块目前被：

- `pages/02_素材分析.py`
- `pages/03_广告数据汇总.py`

共同复用。

## 10. `app/dashboards/` 业务看板层

这里是一页一模块的业务实现层。每个子目录原则上独立维护自己的：

- 配置
- 数据结构
- 数据加工
- 指标计算
- 页面渲染

---

### 10.1 `tag_validation/` 标签检验表模块

负责“关键词 / 人群 / SKU”三类标签检验。

#### `app/dashboards/tag_validation/__init__.py`

声明该目录是标签检验模块包。

#### `app/dashboards/tag_validation/config.py`

标签检验模块的配置中心。

负责定义：

- 6 张源表名称
- 关键词、人群、SKU 的字段名
- UI 展示列名
- `(空白)` 这类通用常量
- `required_sheets` 属性，统一告诉页面需要加载哪些表

这个文件的价值是把所有“表名/列名常量”集中管理，避免散落硬编码。

#### `app/dashboards/tag_validation/loader.py`

数据载体定义层。

定义了 3 个 dataclass：

- `SourceTables`：关键词页所需源表
- `AudienceSourceTables`：人群页所需源表
- `SkuSourceTables`：SKU 页所需源表

它不直接读取 Excel，主要作用是让后续处理代码拿到更明确的命名输入。

#### `app/dashboards/tag_validation/processor.py`

标签检验的数据清洗与合并层。

核心函数：

- `build_keyword_dataset()`
- `build_audience_dataset()`
- `build_sku_dataset()`

职责：

- 文本归一化
- 费用列转数值
- 关联匹配表补分类
- 处理空白分类
- 输出给树形表构造器使用的明细数据

其中 SKU 路径的特点是：

- 事实表和匹配表的关联键列名不同
- 额外补出了商品名称列，供 UI 展示

#### `app/dashboards/tag_validation/tree_builder.py`

树形表数据组装层。

职责：

- 把明细数据加工成 AgGrid tree data 结构
- 生成 `path` 列，构造“父节点 -> 子节点”路径
- 按分类费用降序、分类内子项费用降序排序

核心函数：

- `build_keyword_tree_payload()`
- `build_audience_tree_payload()`
- `build_sku_tree_payload()`

通用底层函数：

- `_build_tree_rows()`

#### `app/dashboards/tag_validation/ui.py`

标签检验页面渲染层。

职责：

- 统一构建 AgGrid 树形表 `gridOptions`
- 分别渲染关键词、人群、SKU 三张树表
- 在空数据时展示 warning

核心函数：

- `render_keyword_table()`
- `render_audience_table()`
- `render_sku_table()`
- `render_empty_state()`

技术特点：

- 使用 `st_aggrid`
- 使用 `JsCode` 控制树列展示细节

---

### 10.2 `material_analysis/` 素材分析模块

负责创意素材数据的宽表分析。

#### `app/dashboards/material_analysis/__init__.py`

这个包做了统一导出，便于外部直接从模块包导入常用对象和函数。

#### `app/dashboards/material_analysis/config.py`

素材分析配置中心。

负责定义：

- 源工作表名
- 关键关联列
- 派生维度列
- 指标列
- 未知分类/未知渠道/爱他美标记等常量

#### `app/dashboards/material_analysis/loader.py`

定义 `SourceTables` 数据载体，封装：

- `creative`
- `plan`
- `sku`

当前页面主流程直接使用的是 `app/core/loader.py`，这里更偏向类型表达和模块边界清晰化。

#### `app/dashboards/material_analysis/processor.py`

素材分析的数据加工核心。

核心函数：

- `build_analysis_dataset()`

主要做 5 件事：

1. 判断是否属于爱他美品牌。
2. 关联计划类型表补渠道字段。
3. 关联商品匹配表补分类字段。
4. 解析日期并派生年、月、日。
5. 填充未知分类和缺失渠道。

输出是一张适合筛选、聚合、透视的分析宽表。

#### `app/dashboards/material_analysis/metrics.py`

素材分析指标计算层。

包含：

- `SummaryMetrics`：顶部指标卡的数据结构
- `calculate_summary_metrics()`：计算汇总指标
- `build_pivot_table()`：按维度生成透视表

指标包括：

- 展现数
- 点击数
- 花费
- 总订单金额
- 总订单行
- CTR
- CVR
- ROI

#### `app/dashboards/material_analysis/ui.py`

素材分析 UI 渲染层。

负责 4 个区域：

- `render_summary()`：顶部指标卡
- `render_pivot_table()`：透视分析表
- `render_detail_section()`：明细预览与 CSV 导出
- `render_empty_state()`：空结果提示

---

### 10.3 `ad_summary/` 广告数据汇总模块

负责把广告数据、店铺经营数据和目标数据做多周期汇总。

#### `app/dashboards/ad_summary/__init__.py`

声明该目录是广告汇总模块包。

#### `app/dashboards/ad_summary/config.py`

广告汇总配置中心。

负责定义：

- 5 张输入工作表
- 广告表、店铺表、SKU 表、计划表、目标表的列名
- 时间维度列名
- 展示列顺序 `display_columns`
- 特殊尾部列名

这个文件对广告汇总模块非常关键，因为汇总列很多，格式也比较固定。

#### `app/dashboards/ad_summary/processor.py`

广告汇总的数据整合核心。

核心函数：

- `build_ad_summary_dataset()`

内部步骤：

1. 把广告表聚合为日级广告数据
2. 把店铺表聚合为日级店铺数据
3. 整理 SKU 映射
4. 整理计划类型映射
5. 整理日级目标数据
6. 多表关联
7. 补齐商品名、品牌、分类、渠道、目标和各类缺失值
8. 派生年、季、月、周、日字段

输出是一张可被后续多周期汇总复用的“日级综合明细表”。

#### `app/dashboards/ad_summary/metrics.py`

广告汇总指标与周期表生成层。

核心函数：

- `build_period_summary()`：按指定周期生成汇总表
- `filter_detail_by_summary_scope()`：用汇总结果反筛明细范围
- `build_total_row_for_scope()`：基于当前范围重算总计行
- `build_summary_and_total()`：一次返回明细汇总表和总计表

负责计算的重点指标包括：

- 广告费用
- 投放 GMV
- 店铺 GMV
- 广告 GMV 贡献
- 广告 ROI
- 费比
- 店铺 GMV 目标
- 店铺完成进度
- 广告点击季度同比
- 多类环比指标

#### `app/dashboards/ad_summary/ui.py`

广告汇总 UI 渲染层。

职责：

- 渲染普通周期汇总表
- 渲染总计表
- 格式化百分比、小数、整数
- 对不同指标区块做底色区分
- 对环比/同比做正负颜色高亮

核心函数：

- `render_summary_table()`
- `render_total_table()`
- `render_empty_state()`

## 11. `tests/` 测试层

项目当前已经有两组单元测试，说明核心逻辑不是纯手点页面验证。

### `tests/test_tag_validation_sku_name.py`

主要验证：

- SKU 数据集是否能正确补出商品名称
- SKU 树形数据是否只在子节点保留商品名称和 SKU
- 关键词、人群、SKU 的树结构配置是否符合预期
- AgGrid 列定义是否包含应展示字段

这组测试重点保护的是“标签检验表”的数据结构和 UI 配置约定。

### `tests/test_ad_summary_metrics.py`

主要验证：

- 广告、店铺、目标等数据能否正确整合
- 各周期汇总值是否正确
- 日级目标完成进度是否正确
- 缺失值、空值、0 值下的环比/同比逻辑是否稳定
- 总计行是否按当前筛选范围重新计算

这组测试重点保护的是“广告数据汇总”的加工和指标逻辑。

## 12. 当前模块关系图

```text
main.py
  -> app/core/shared_source.py

pages/01_标签检验表.py
  -> app/core/loader.py
  -> app/dashboards/tag_validation/config.py
  -> app/dashboards/tag_validation/processor.py
  -> app/dashboards/tag_validation/tree_builder.py
  -> app/dashboards/tag_validation/ui.py

pages/02_素材分析.py
  -> app/core/loader.py
  -> app/core/filters.py
  -> app/dashboards/material_analysis/config.py
  -> app/dashboards/material_analysis/processor.py
  -> app/dashboards/material_analysis/metrics.py
  -> app/dashboards/material_analysis/ui.py

pages/03_广告数据汇总.py
  -> app/core/loader.py
  -> app/core/filters.py
  -> app/dashboards/ad_summary/config.py
  -> app/dashboards/ad_summary/processor.py
  -> app/dashboards/ad_summary/metrics.py
  -> app/dashboards/ad_summary/ui.py
```

## 13. 新增一个看板时该怎么放文件

建议继续沿用现有分层，不要把逻辑重新塞回 `pages/`。

推荐结构：

```text
app/dashboards/<new_dashboard>/
├─ __init__.py
├─ config.py
├─ processor.py
├─ metrics.py        # 如果有指标计算
├─ ui.py
└─ loader.py         # 如果需要命名化源表对象
```

对应新增页面入口：

```text
pages/04_<新页面名>.py
```

页面文件建议只做这些事：

1. 校验共享数据源是否存在
2. 通过 `load_shared_workbook()` 和 `select_required_sheets()` 取数据
3. 调用本模块 `processor / metrics / ui`

## 14. 当前项目的优点和限制

### 优点

- 共享数据源机制清晰，避免重复上传
- 页面入口和业务逻辑已经分层
- 通用筛选能力可复用
- 核心复杂逻辑已有测试保护
- 新增看板的扩展路径比较明确

### 限制

- 还没有依赖文件
- 还没有统一异常展示封装
- `material_analysis/loader.py` 目前更多是类型定义，和页面主流程的直接集成不算强
- 顶层示例 Excel 直接放在仓库内，后续要注意体积与敏感数据管理
- 部分 `__init__.py` 只是包声明，尚未统一导出接口

## 15. 建议的后续优化

如果你后面还要继续维护这个项目，建议按优先级做这几件事：

1. 补 `requirements.txt` 或 `pyproject.toml`
2. 增加 `.gitignore`，忽略 `__pycache__/`、`.pyc` 等运行产物
3. 把各页面公共的“检查共享数据源 + 加载 workbook”流程再抽一层
4. 为素材分析模块补测试
5. 给广告汇总和素材分析补更明确的异常提示

## 16. 一句话总结

这个项目已经形成了比较清晰的四层结构：

- `main.py / pages/` 负责入口和页面编排
- `app/core/` 负责共享基础设施
- `app/dashboards/` 负责具体业务实现
- `tests/` 负责关键逻辑回归保护

如果你要继续扩展，这个结构是可以直接沿用的。
