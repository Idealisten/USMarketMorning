# USMarketMorning

每天北京时间 06:00 自动生成中文美股收盘晨报，发送到 Gmail，并在网站上保存历史文章。

## 内容范围

- 数据罗列：纳斯达克100、标普500、韩国股市指数、日本股市指数、香港恒生科技、恒生消费、国际黄金、短期/中期/长期美债收益率、原油、贵金属。
- 个股筛选：纳斯达克100、标普500 各自涨幅前10和跌幅前10。
- 事实陈述：过去24小时影响市场的战争、能源、科技、AI、特朗普相关公开言论和宏观新闻。
- 分析总结：把事实线索与各品类涨跌、重点个股异动对应起来。

## 本地运行

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m usmarketmorning.app
```

打开终端输出里的地址。默认从 `8000` 开始，如果端口被占用会自动向后寻找可用端口。

手动生成一篇晨报：

```bash
python -m usmarketmorning.cli generate
```

生成并发送邮件：

```bash
python -m usmarketmorning.cli generate --send
```

## Gmail 配置

编辑 `.env`：

```bash
SMTP_USER=你的 Gmail 地址
SMTP_PASSWORD=你的 Gmail App Password
EMAIL_FROM=你的 Gmail 地址
EMAIL_TO=prometheus.mr.cy@gmail.com
```

Gmail 一般需要开启两步验证后创建 App Password，不能直接使用账号登录密码。

## AI 分析

不配置 `OPENAI_API_KEY` 时，系统会用内置规则生成保守版分析。配置后会调用模型生成更完整的中文分析：

```bash
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

## Docker 部署

```bash
cp .env.example .env
vim .env
./scripts/run.sh
```

`scripts/run.sh` 会：

- 从宿主机 `8000` 开始寻找可用端口；
- 构建 Docker 镜像；
- 挂载 `./data` 到容器内，确保历史文章持久保存；
- 使用 `--restart unless-stopped` 保持服务运行。

## 服务器端更新

首次部署后，后续更新代码：

```bash
./scripts/update_server.sh
```

等价于：

```bash
git pull --ff-only
./scripts/run.sh
```

历史文章保存在 `data/reports`，脚本重启容器不会删除历史。

## 定时任务

应用启动时默认启用后台定时任务：

```bash
RUN_SCHEDULER=true
REPORT_TIMEZONE=Asia/Shanghai
REPORT_HOUR=6
REPORT_MINUTE=0
```

也可以把 `RUN_SCHEDULER=false`，改用服务器 cron：

```cron
0 6 * * * cd /path/to/USMarketMorning && .venv/bin/python -m usmarketmorning.cli generate --send
```

## 数据源说明

行情默认使用 Yahoo/yfinance；成分股默认从 Wikipedia 抓取；新闻默认使用 Google News RSS 查询。若 Yahoo 更改符号，可在 `.env` 中覆盖：

```bash
HK_INDEX_SYMBOLS=HSTECH.HK,159699.SZ
BOND_SYMBOLS=^IRX,^FVX,^TNX,^TYX
```

说明：Yahoo 对部分港股行业指数没有稳定代码，默认用 `159699.SZ` 作为“恒生消费”代理；如果你有更稳定的数据源或代码，可以直接在 `.env` 覆盖。

特朗普相关内容默认从过去24小时新闻中筛选；如果你有稳定的 X/Truth Social RSS 或镜像源，可配置：

```bash
TRUMP_SOURCE_URL=https://example.com/rss
```
