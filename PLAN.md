# Devin Token Monitor — 长线迭代计划

目标：把监控工具打磨成"看起来像苹果/谷歌第一方"的成熟 macOS 应用。
设计语言参照 **Apple Liquid Glass**（磨砂半透明、深度分层、物理感动效）与 **Material Design 3**（色彩系统、状态层、弹性动效），全程非线性动画。

## 设计原则

- **Material**: `rgba` 磨砂卡片 + `backdrop-filter: blur+saturate`，页面底层用低饱和渐变光斑，营造玻璃悬浮感
- **层级**: 背景 → 玻璃卡（blur 20px）→ 浮起元素（shadow + border 1px rgba white)
- **动效**: 非线性曲线 `cubic-bezier(.34,1.4,.4,1)` 过冲 / `(0.16,1,.3,1)` 缓出；入场 stagger、数字滚动、图表描绘、抽屉弹簧滑入；尊重 `prefers-reduced-motion`
- **色彩**: 低饱和、双主题（light/dark via `prefers-color-scheme`)，语义色克制
- **排版**: SF Pro 字阶、tabular-nums、8pt 间距栅格

## Phase 0 — 资产管线 ✅

- [x] 可安装 DMG + .app (py2app)
- [x] **App 图标 .icns**:PIL 程序化生成（圆角玻璃底 + 渐变闪电）→ `tools/make_icon.py` → `assets/AppIcon.icns`，进 py2app `iconfile`
- [x] Dock/Finder 图标生效（CFBundleIconFile=AppIcon.icns)
- [ ] DMG 精修：窗口定位、Applications 拖拽引导（osascript .DS_Store，可降级）

## Phase 1 — 设计系统 v2(Liquid Glass)✅

- [x] CSS token 全套：双主题变量、玻璃卡 `backdrop-filter`、层级阴影、三色渐变背景光斑
- [x] 非线性动效：卡片入场 stagger(rise 60ms 间隔）、数值 count-up(easeOutQuint + rAF)、图表 path 描绘动画、抽屉 spring 滑入、按钮按压 .94、seg 滑块 thumb、图例/弧段过渡
- [x] KPI/图表/环形图/表格视觉重制（毛玻璃 + 微质感）
- [x] `prefers-color-scheme` 暗色模式 + `prefers-reduced-motion` 全关动效

## Phase 2 — 结构 UX 升级 ✅（本期完成）

- [x] **侧边导航布局**：概览 / 模型 / 会话 / 请求 / 设置 五视图，玻璃 sidebar（含今日速览 footer)，视图切换 fadeUp 过渡
- [x] **设置视图**：预算输入（写回 prices.json)、登录自启开关（native bridge)、数据路径、编辑价格表、导出、关于
- [x] 骨架屏 shimmer(KPI 首载）+ 空状态
- [x] 键盘导航（⌘1-5 切视图、/ 聚焦搜索、Esc 关抽屉）

## Phase 3 — 状态栏整合 ✅

- [x] `gui.py` 内置 NSStatusItem:bolt.fill SF Symbol + 今日费用，下拉含今日摘要 + 打开主面板 + 退出
- [x] 关窗不退出（常驻状态栏）,Dock 点击重开窗口
- [ ] （后续）状态栏图标样式可选：图标+费用 / 仅图标 / 仅费用

## Phase 4 — 发布打磨（部分）

- [ ] DMG 精修（图标定位/背景图）
- [ ] README 截图（需屏幕录制权限，未能自动截）
- [ ] 版本号策略 + CHANGELOG
- [ ] （可选）自更新检查

## 已知边界

- ACU/credits 不在本地库，费用始终为估算
- 参考 skill:`frontend-design` 流程（层级→实现→视觉 QA)；`Taste/UI UX Pro Max/Impeccable` 本机不存在，按其理念执行

## 下一轮候选

- 请求流实时渐入动画（新行滑入）
- 会话/模型视图内嵌小型 sparkline
- DMG 窗口布局精修 + 欢迎页
- 通知中心小组件式卡片（超预算时的历史峰值展示）
