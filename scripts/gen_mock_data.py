#!/usr/bin/env python3
"""
生成 30 地区 × 366 天 = 10,980 个 Mock 事件池 JSON

用法:
    python scripts/gen_mock_data.py

输出:
    tests/fixtures/mock_responses/wikipedia/{MM-DD}_{COUNTRY}.json
"""
import json
import sys
from datetime import date, timedelta
from pathlib import Path

# 添加项目根到 path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.models.event import Event, EventPool
from src.models.countries import ALL_COUNTRIES, COUNTRY_NAMES

# === Mock 事件模板 ===
# 每个地区预置 5 条事件模板(年份/标题/描述),按日期偏移取模选择
MOCK_EVENT_TEMPLATES = {
    "CN": [
        (1921, "中国共产党成立", "中国共产党第一次全国代表大会在上海召开,标志着中国共产党成立。"),
        (1949, "中华人民共和国成立", "毛泽东在北京天安门城楼宣告中华人民共和国中央人民政府成立。"),
        (1911, "辛亥革命", "孙中山领导的辛亥革命推翻了清朝统治,结束了中国两千多年的封建君主制。"),
        (1976, "唐山大地震", "河北省唐山市发生7.8级强烈地震,造成24万余人死亡。"),
        (2008, "北京奥运会", "第29届夏季奥林匹克运动会在北京国家体育场(鸟巢)开幕。"),
    ],
    "US": [
        (1776, "美国独立宣言", "第二届大陆会议通过《独立宣言》,标志着美国建国。"),
        (1865, "林肯遇刺", "美国总统亚伯拉罕·林肯在福特剧院遇刺身亡。"),
        (1945, "二战结束", "日本投降,第二次世界大战正式结束。"),
        (1969, "阿波罗11号登月", "美国宇航员尼尔·阿姆斯特朗成为第一个登上月球的人。"),
        (2001, "9·11恐怖袭击", "恐怖分子劫持民航客机撞击世界贸易中心和五角大楼。"),
    ],
    "JP": [
        (1868, "明治维新", "明治天皇即位,日本开始明治维新,走向近代化。"),
        (1945, "广岛原爆", "美国在日本广岛投下原子弹,加速了二战结束。"),
        (1964, "东京奥运会", "第18届夏季奥林匹克运动会在东京开幕,亚洲首次举办奥运。"),
        (2011, "东日本大地震", "日本东北地方太平洋海域发生9.0级地震,引发福岛核事故。"),
        (2019, "令和开元", "日本改元令和,明仁天皇退位,德仁天皇即位。"),
    ],
    "KR": [
        (1945, "光复节", "朝鲜半岛脱离日本殖民统治获得独立。"),
        (1950, "朝鲜战争爆发", "朝鲜人民军越过三八线南下,朝鲜战争爆发。"),
        (1988, "汉城奥运会", "第24届夏季奥林匹克运动会在汉城(今首尔)开幕。"),
        (2018, "平昌冬奥会", "第23届冬季奥林匹克运动会在平昌开幕。"),
        (2022, "梨泰院踩踏事故", "首尔梨泰院发生严重踩踏事故,造成159人死亡。"),
    ],
    "UK": [
        (1066, "黑斯廷斯战役", "诺曼底公爵威廉征服英格兰,建立诺曼底王朝。"),
        (1215, "大宪章签署", "英王约翰被迫签署《大宪章》,限制王权。"),
        (1707, "联合法案", "英格兰与苏格兰合并,形成大不列颠王国。"),
        (1940, "不列颠空战", "英国皇家空军击败德国空军,保卫了英国本土。"),
        (1952, "伊丽莎白二世即位", "伊丽莎白二世继位,成为英国女王。"),
    ],
    "DE": [
        (1871, "德意志帝国建立", "普鲁士国王威廉一世在凡尔赛宫加冕为德意志皇帝。"),
        (1919, "魏玛共和国建立", "德国国民议会在魏玛召开,魏玛共和国成立。"),
        (1933, "希特勒上台", "希特勒被任命为德国总理,纳粹党开始执政。"),
        (1945, "德国投降", "纳粹德国无条件投降,二战欧洲战场结束。"),
        (1990, "两德统一", "东德正式加入西德,德国重新统一。"),
    ],
    "FR": [
        (1789, "法国大革命", "巴黎民众攻占巴士底狱,法国大革命爆发。"),
        (1804, "拿破仑称帝", "拿破仑·波拿巴在巴黎圣母院加冕为法国皇帝。"),
        (1871, "巴黎公社", "巴黎工人起义,建立巴黎公社政权。"),
        (1944, "巴黎解放", "盟军解放巴黎,结束纳粹德国占领。"),
        (2015, "巴黎气候协定", "《巴黎协定》在联合国气候变化大会上通过。"),
    ],
}

# 默认模板(其他 23 个地区使用通用模板)
DEFAULT_TEMPLATE = [
    (1900, "重要历史事件一", "该地区20世纪初的重要历史事件。"),
    (1950, "重要历史事件二", "该地区20世纪中叶的重要历史事件。"),
    (2000, "重要历史事件三", "该地区21世纪初的重要历史事件。"),
    (1800, "古代历史事件", "该地区古代的重要历史事件。"),
    (2020, "当代历史事件", "该地区当代的重要历史事件。"),
]


def get_event_templates(country: str) -> list[tuple[int, str, str]]:
    """获取地区对应的事件模板"""
    return MOCK_EVENT_TEMPLATES.get(country, DEFAULT_TEMPLATE)


def gen_event(date_str: str, country: str, idx: int, year: int, title: str, desc: str) -> Event:
    """生成单个 Mock 事件"""
    return Event(
        id=f"evt_{date_str.replace('-', '')}_{country}_{idx:03d}",
        date=f"2024-{date_str}",
        year=year,
        title=f"[{country}] {title}",
        description=desc,
        wikipedia_url=f"https://en.wikipedia.org/wiki/{country}_{date_str}",
        categories=["mock", country.lower(), "historical"],
        location=country,
        deaths=None,
        injuries=None,
    )


def gen_event_pool(date_str: str, country: str) -> EventPool:
    """生成单日单地区事件池"""
    templates = get_event_templates(country)
    events = []
    # 每日每地区 3 个事件,按日期偏移取模选择
    day_offset = (int(date_str.split("-")[0]) - 1) * 31 + int(date_str.split("-")[1])
    for i in range(3):
        template_idx = (day_offset + i) % len(templates)
        year, title, desc = templates[template_idx]
        events.append(gen_event(date_str, country, i, year, title, desc))

    return EventPool(
        date=f"2024-{date_str}",
        country_code=country,
        events=events,
        source="wikipedia_mock",
        fetched_at="2026-07-19T00:00:00Z",
    )


def main():
    """生成 366 × 30 = 10,980 个 Mock 事件池 JSON"""
    fixture_dir = PROJECT_ROOT / "tests" / "fixtures" / "mock_responses" / "wikipedia"
    fixture_dir.mkdir(parents=True, exist_ok=True)

    # 使用 2024 年(闰年)生成,确保 02-29 有数据
    start_date = date(2024, 1, 1)
    total = 0

    print(f"开始生成 Mock 数据到 {fixture_dir}")
    print(f"地区数: {len(ALL_COUNTRIES)}, 天数: 366, 总文件数: {366 * len(ALL_COUNTRIES)}")

    for day_offset in range(366):
        d = start_date + timedelta(days=day_offset)
        date_str = d.strftime("%m-%d")

        for country in ALL_COUNTRIES:
            pool = gen_event_pool(date_str, country)
            out_file = fixture_dir / f"{date_str}_{country}.json"
            out_file.write_text(
                pool.model_dump_json(indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            total += 1

        # 进度日志(每 30 天一次)
        if (day_offset + 1) % 30 == 0:
            print(f"  进度: {day_offset + 1}/366 天, 已生成 {total} 个文件")

    print(f"\n✅ 完成! 共生成 {total} 个 Mock 事件池文件")
    print(f"   输出目录: {fixture_dir}")

    # 验证总体积
    total_size = sum(f.stat().st_size for f in fixture_dir.glob("*.json"))
    print(f"   总体积: {total_size / 1024 / 1024:.2f} MB")
    print(f"   单文件平均: {total_size / total:.0f} 字节")


if __name__ == "__main__":
    main()
