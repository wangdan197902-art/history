# scripts/ 目录说明

本目录存放项目所有自动化脚本。

## 脚本清单

| 脚本 | 用途 | 阶段 |
|------|------|------|
| check_hardware.py | Mac 硬件评估,决定 Hugo 构建策略 | Phase 0 |
| gen_mock_data.py | 生成 366×30=10,980 个 Mock 事件池 | Phase 0 |
| gen_detailed_fixtures.py | 生成 5×30×10=1,500 个详细 fixture | Phase 1 |
| validate_fixtures.py | 校验 fixture 完整性 | Phase 1 |
| local_e2e.sh | 本地端到端测试一键脚本 | Phase 3 |
| gen_blank_pages.py | 生成 109,800 个 Hugo Markdown | Phase 3 |
| hugo_batch_build.sh | Hugo 分批构建脚本 | Phase 3 |
| perf_dashboard.py | 性能监控看板生成 | Phase 2 |

## 使用方式

所有脚本均需在项目根目录执行,且需先激活 Python 虚拟环境:

```bash
. .venv/bin/activate
python scripts/check_hardware.py
```
