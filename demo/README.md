# 交互原型

可预览、可交互的前端原型，覆盖 4 个核心页面。

## 在线预览

原型是纯静态站，任意静态托管都能跑。

**方式一：GitHub Pages**（推荐，配置一次即可持续访问）

1. 仓库页面 → **Settings** → 左侧 **Pages**
2. **Source** 选 `Deploy from a branch`
3. **Branch** 选 `main`，目录选 `/ (root)`，点 **Save**
4. 等 1–2 分钟，访问：

   ```
   https://zhengxinyu31-byte.github.io/paris-storymap/demo/
   ```

**方式二：本地跑**

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
| **人格测试 + 结果页** | 12 题单题单屏，**点击选项即自动进入下一题**（无「下一题」按钮），答完自动进结果页（无「提交」按钮）；可返回上一题改选 |
| **主题线页** | 左侧站点时间轴 ⟷ 右侧地图轨迹双向联动；自动播放逐站推进；URL hash 同步 |
| **POI 详情页** | 关联名人 / 作品 / 影视场景，置信度徽章，辟谣卡片，小地图与周边 POI |

## 底图方案

**MapLibre GL JS + CARTO basemaps**（公开瓦片，无需 key）。

项目明确不商业化，底图选型以「能用好用」为准。详见 [requirements.md](../specs/requirements.md) §4.2.1 的三级兜底路径。

底图配色取低饱和单色调，让彩色 POI marker 成为画面主体，与全站「老地图 / 旧书封面 / 法式海报」的视觉语言统一。

> 若打开后看到「地图瓦片加载失败」，说明当前网络访问不到 CARTO 的瓦片服务，换网络或代理即可。attribution 显示 `© OpenStreetMap contributors © CARTO` 表示底图已正确接入。

---

## 说明

- 原型内的巴黎内容是**真实素材**（存在主义线 8 站、花神煤炉故事、萨特故居两次被炸、皮雅芙铭牌辟谣等），不是 lorem ipsum。
- 原型是**需求沟通载体**，不是最终代码。正式实现走 `research/` 下的语料 → 构建管道 → 静态站。
- 发布前已移除构建期注入的内部埋点、APM 上报与 sourcemap。
