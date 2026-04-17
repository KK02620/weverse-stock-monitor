# Mac 打包说明

## GitHub 打包优先

如果你要**手动再打包一份 mac 版 `.dmg`**，并且**必须通过 GitHub 打包**，请优先使用仓库：

- `https://github.com/KK02620/weverse-stock-monitor`

当前仓库已经有 GitHub Actions 工作流：

- `.github/workflows/build-mac.yml`

它支持：

- 推送到 `main` / `master` 时自动构建
- 在 GitHub 页面中手动点击 `Run workflow` 触发构建
- 生成 `WeverseStockMonitor-macOS.dmg`
- 上传到 Actions Artifact
- 在 `main` 分支 push 时自动创建 Release

## 推荐方式：通过 GitHub 手动打包 mac 版 DMG

适用场景：

- 当前电脑不是 Mac
- 需要使用 GitHub 的 macOS Runner 统一构建
- 需要重新手动打一份 mac 版 `.dmg`

操作步骤：

1. 先把最新代码推送到 GitHub 仓库
2. 打开仓库页面：`https://github.com/KK02620/weverse-stock-monitor`
3. 进入 `Actions`
4. 选择工作流 `Build Mac App`
5. 点击右侧 `Run workflow`
6. 选择需要构建的分支（通常是 `main`）
7. 点击 `Run workflow` 开始打包
8. 等待 `build` 任务完成
9. 在工作流运行结果中下载 Artifact：`WeverseStockMonitor-macOS`
10. 解压后即可得到 `WeverseStockMonitor-macOS.dmg`

说明：

- 这就是“通过 GitHub 手动再打包一份 mac 版 `.dmg`”的标准做法
- 如果你推送到了 `main`，工作流完成后还会自动创建 Release
- 如果只是想临时重新打一份，不一定需要发版，直接下载 Artifact 即可

## 打包前准备

### 1. 安装依赖

```bash
cd weverse-stock-monitor
pip install -r requirements.txt
```

### 2. 确保所有文件存在

检查以下文件是否都在项目目录中：
- main.py (程序入口)
- config.py (配置)
- cookie_manager.py (Cookie 管理)
- crawler.py (异步爬虫)
- weverse_crawler.py (同步爬虫)
- gui.py (GUI 界面)
- monitor.py (监控逻辑)
- notifier.py (通知模块)
- storage.py (数据存储)
- models.py (数据模型)
- build_mac.py (打包脚本)

## 打包步骤

### 方式一：使用打包脚本（推荐）

```bash
# 基础打包
python build_mac.py

# 清理后重新打包
python build_mac.py --clean

# 打包并创建 DMG 安装包
python build_mac.py --dmg
```

打包完成后，会在 `dist/` 目录下生成：
- `WeverseStockMonitor.app` - 应用程序
- `WeverseStockMonitor.dmg` (如果使用 --dmg) - 安装包

### 方式一补充：通过 GitHub Actions 构建（非 Mac 环境优先）

如果你当前不是在 macOS 上操作，或者明确要求**一定通过 GitHub 打包**，请不要在本地执行 `build_mac.py`，直接使用上面的 GitHub 手动打包流程。

### 方式二：手动打包

```bash
# 安装 pyinstaller
pip install pyinstaller

# 生成 spec 文件并打包
python build_mac.py --clean
```

## 打包输出

### 应用位置
```
dist/
└── WeverseStockMonitor.app/
    └── Contents/
        ├── MacOS/           # 可执行文件
        ├── Resources/       # 资源文件
        └── Info.plist       # 应用配置
```

### 数据存储位置
打包后的应用会将数据存储在用户主目录：
```
~/Library/Application Support/WeverseStockMonitor/data/
├── products.xlsx    # 商品数据
└── monitor.log      # 运行日志
```

## 运行应用

### 方式一：双击运行
直接双击 `dist/WeverseStockMonitor.app`

**注意**：首次运行可能需要：
1. 右键点击应用 → 选择"打开"
2. 在系统偏好设置 → 安全性与隐私中允许运行

### 方式二：命令行运行
```bash
open dist/WeverseStockMonitor.app
```

## 常见问题

### 1. 应用无法打开（安全性警告）
**原因**：Mac 的 Gatekeeper 阻止了未签名应用

**解决**：
- 右键点击应用 → 选择"打开"
- 或前往 系统偏好设置 → 安全性与隐私 → 允许从此开发者

### 2. 数据文件找不到
**原因**：应用没有正确创建数据目录

**解决**：
```bash
# 手动创建数据目录
mkdir -p ~/Library/Application\ Support/WeverseStockMonitor/data
```

### 3. 缺少依赖
**错误信息**：`ModuleNotFoundError`

**解决**：
```bash
pip install pandas openpyxl httpx
```

### 4. 打包失败
**检查步骤**：
1. 确保所有 Python 文件语法正确
2. 确保 pyinstaller 已安装
3. 查看 `build/` 目录下的日志文件

## 技术细节

### 无硬编码路径
- 使用 `sys._MEIPASS` 检测打包环境
- 数据目录使用 `~/Library/Application Support/`
- 所有路径通过 `pathlib.Path` 处理

### 包含的依赖
- pandas - Excel 处理
- openpyxl - Excel 引擎
- httpx - HTTP 请求
- certifi - SSL 证书
- tkinter - GUI (系统自带)

### 应用信息
- Bundle ID: `com.weverse.stockmonitor`
- 版本: 1.0.0
- 最小 macOS 版本: 10.13+

## 重新打包

如果需要修改代码后重新打包：

```bash
# 清理旧的构建文件
python build_mac.py --clean

# 重新打包
python build_mac.py --dmg
```

## 分发应用

打包完成后，可以将以下文件分发给用户：
1. `WeverseStockMonitor.app` - 直接运行
2. `WeverseStockMonitor.dmg` - 安装包（推荐）
3. `WeverseStockMonitor-macOS.dmg` - GitHub Actions 构建产物

用户无需安装 Python 或任何依赖，双击即可运行。
