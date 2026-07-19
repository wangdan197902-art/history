.PHONY: help setup test lint build e2e mock-server hugo-server pipeline perf clean

help: ## 显示所有可用命令
	@echo "可用命令:"
	@echo "  make setup        - 创建 .venv + 安装依赖 + Hugo mod deps"
	@echo "  make mock-server  - 启动 Mock Server (本地全链路模拟)"
	@echo "  make hugo-server  - 启动 Hugo 本地开发服务器"
	@echo "  make pipeline     - 运行内容生产管道编排器"
	@echo "  make build        - Hugo 构建站点 (--minify --gc)"
	@echo "  make test         - 运行 pytest 测试套件 + 覆盖率"
	@echo "  make e2e          - 本地端到端测试一键脚本"
	@echo "  make perf         - 性能监控看板生成"
	@echo "  make lint         - ruff 代码检查"
	@echo "  make clean        - 清理 .venv / public / resources / .cache"

setup: ## 创建虚拟环境并安装依赖
	python3 -m venv .venv
	. .venv/bin/activate && pip install -r requirements.txt
	cd site && hugo mod deps

mock-server: ## 启动 Mock Server
	. .venv/bin/activate && python -m src.mock_server.app

hugo-server: ## 启动 Hugo 开发服务器
	cd site && hugo server -D --bind 0.0.0.0

pipeline: ## 运行内容生产管道
	. .venv/bin/activate && python -m src.pipeline.orchestrator

build: ## Hugo 构建站点
	cd site && hugo --minify --gc

test: ## 运行测试
	. .venv/bin/activate && pytest tests/ -v --cov=src --cov-report=term-missing

e2e: ## 本地端到端测试
	. .venv/bin/activate && bash scripts/local_e2e.sh

perf: ## 性能监控看板
	. .venv/bin/activate && python scripts/perf_dashboard.py

lint: ## 代码检查
	. .venv/bin/activate && ruff check src tests scripts

clean: ## 清理产物
	rm -rf .venv site/public site/resources .cache
