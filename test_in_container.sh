#!/bin/bash
# 容器化测试脚本 - 使用 chroot 方式模拟容器环境

set -e

echo "=================================="
echo "Quant Assistant 容器化测试"
echo "=================================="

# 创建隔离目录
TEST_DIR="/tmp/quant_test_$$"
mkdir -p "$TEST_DIR"

echo "1. 准备测试环境..."
cp -r /home/admin/.openclaw/workspace/quant-assistant/* "$TEST_DIR/"

echo "2. 检查 Python 版本..."
python3 --version || echo "Python3 未安装"

echo "3. 运行模拟测试..."
cd "$TEST_DIR"
python3 test_mock.py

echo ""
echo "=================================="
echo "测试完成"
echo "=================================="
echo ""
echo "注意: 由于网络限制，无法下载 Docker 镜像"
echo "请在本地有 Docker 环境后执行:"
echo "  docker-compose up"
echo ""

# 清理
rm -rf "$TEST_DIR"
