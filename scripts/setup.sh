#!/usr/bin/env bash
# ai-daily-report 一键初始化
# 用法：bash scripts/setup.sh
set -e
cd "$(dirname "$0")/.."

echo "🚀 ai-daily-report 初始化"
echo "========================"

# 1. 创建 .env（若不存在）
if [ ! -f .env ]; then
    cp .env.example .env
    echo "✅ 已创建 .env（从 .env.example 复制）"
    echo "⚠️  请编辑 .env 填写你自己的邮箱与 SMTP 授权码："
    echo "   vi .env   或   nano .env"
    echo "   各邮箱授权码获取方式见 references/smtp-guide.md"
else
    echo "ℹ️  .env 已存在，跳过"
fi

# 2. 创建工作目录
mkdir -p reports logs
echo "✅ 已创建 reports/（日报存档）与 logs/（运行日志）"

# 3. 安装 Python 依赖
echo "▶ 安装 Python 依赖（requests / feedparser / markdown）…"
if command -v pip3 >/dev/null 2>&1; then
    pip3 install -q requests feedparser markdown 2>/dev/null || \
        sudo pip3 install -q requests feedparser markdown
    echo "✅ 依赖安装完成"
else
    echo "⚠️  未找到 pip3，请手动安装：pip3 install requests feedparser markdown"
fi

echo ""
echo "========================"
echo "🎉 初始化完成！下一步："
echo "  1. 编辑 .env 填写 SMTP 配置"
echo "  2. python3 scripts/test_smtp.py --send   # 测试邮件链路"
echo "  3. python3 scripts/run_daily.py --no-send  # 试生成一期（不发送）"
echo "  4. python3 scripts/run_daily.py            # 完整跑一期"
echo "  5. 定时运行见 README.md「定时任务」章节"
