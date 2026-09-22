# 交互原型

可预览、可交互的前端原型，覆盖 4 个核心页面。

## 在线预览

**👉 [https://zhengxinyu31-byte.github.io/paris-storymap/demo/](https://zhengxinyu31-byte.github.io/paris-storymap/demo/)**

已通过 GitHub Pages 部署（`main` 分支 `/ (root)`），点开即用。

**本地跑**

```bash
git clone https://github.com/zhengxinyu31-byte/paris-storymap.git
cd paris-storymap/demo
python3 -m http.server 8080
# 浏览器打开 http://localhost:8080
```

> ⚠️ 必须通过 HTTP 服务访问，**不能直接双击 index.html**——这是 ES module 构建产物，`file://` 协议下会被 CORS 策略拦住。

---

## 覆盖的页面与交互

| 页面 | 可交互的点 |
|---|---|
| **首页：全城地图 + 时间轴** | 真实街道级底图，滚轮缩放 / 拖拽平移；时间轴拖动时 POI marker 显隐与计数实时同步；主题筛选；hover 出卡片、单击出浮层、双击进详情 |
| **搜索** | 五维匹配（中文名 / 法文原名 / 英文名 / 关联名人 / 关联影视），**每条建议都标明匹配原因与命中类型**；片名代号映射（搜 `GEMINI` 命中《碟中谍6》取景地） |
| **人格测试 + 结果页** | 12 题单题单屏，**点击选项即自动进入下一题**（无「下一题」按钮），答完自动进结果页（无「提交」按钮）；可返回上一题改选 |
| **主题线页** | 左侧站点时间轴 ⟷ 右侧地图轨迹双向联动；自动播放逐站推进；URL hash 同步 |
| **POI 详情页** | 关联名人 / 作品 / 影视场景，置信度徽章，辟谣卡片，小地图与周边 POI |

**搜索值得单独试一下**——它不是「按名字找地方」，而是按人、按作品找地方。搜「萨特」出 5 条：前两条是名字里含萨特的 POI（合葬墓、故居），后三条是**他在那儿待过**（伽利玛出版社、双叟、花神），每条都写明命中原因。

## 底图方案

**MapLibre GL JS + [OpenFreeMap](https://openfreemap.org/) positron** —— 真正零 key、无配额、无需注册的矢量瓦片服务。

可缩放至单栋建筑级别（`maxZoom: 20`），街道名称清晰可读。positron 为低饱和浅灰白，让彩色 POI marker 成为画面主体，与全站「老地图 / 旧书封面 / 法式海报」的视觉语言统一。

attribution 显示 `© OpenStreetMap contributors © OpenFreeMap`。

> ⚠️ **踩过的坑**：初版用的是 CARTO 的**矢量**瓦片端点，它需要 API key。未授权时它不报错，而是返回一张印着 `API KEY REQUIRED` 却同时画了淡灰街道线和 `PARIS` 字样的**占位纹理**——乍看很像成功加载的复古地图，极易误判。识别方法：放大后看不到任何街道名。详见 [requirements.md](../specs/requirements.md) §4.2.1。

---

## 说明

- 原型内的巴黎内容是**真实素材**（存在主义线 8 站、花神煤炉故事、萨特故居两次被炸、皮雅芙铭牌辟谣等），不是 lorem ipsum。
- 原型是**需求沟通载体**，不是最终代码。正式实现走 `research/` 下的语料 → 构建管道 → 静态站。
- 发布前已移除构建期注入的内部埋点、APM 上报与 sourcemap。
