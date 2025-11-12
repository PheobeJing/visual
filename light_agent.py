#!/usr/bin/env python3
# plant_pp_assistant.py
"""
植物光周期自动调控助手（sigma 固定 2.0 天）
"""
from dotenv import load_dotenv
load_dotenv()

import asyncio
import os
import csv
import math
from typing import Dict
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter1d

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.messages import TextMessage

BASE_PATH = r"d:/pi_programs/visual" 

# ---------- 1. 核心工具 ----------
def calc_photoperiod(
        days: int,
        h_min: float,
        h_max: float,
        h_ave: float
) -> Dict[str, any]:
    """三段光周期 + 高斯平滑（σ 固定为 2）"""
    if h_max > 24:
        raise ValueError("最大光周期不能超过 24 小时")
    if not (0 <= h_min <= h_ave <= h_max):
        raise ValueError("必须满足 0 ≤ h_min ≤ h_ave ≤ h_max")
    if days <= 0:
        raise ValueError("栽培天数必须为正整数")

    # 原始三段
    d1 = int(math.floor(days * (h_max - h_ave) / (h_max - h_min)))
    d3 = int(math.floor(days * (h_ave - h_min) / (h_max - h_min)))
    d2 = days - d1 - d3
    pp1, pp3 = h_min, h_max
    pp2 = (days * h_ave - d1 * h_min - d3 * h_max) if d2 == 1 else 0.0

    # 展开 -> 平滑（σ=2）-> 压回
    daily = np.array([pp1] * d1 + [pp2] * d2 + [pp3] * d3, dtype=float)
    smoothed = gaussian_filter1d(daily, sigma=2.0, mode='nearest')

    s1 = smoothed[:d1].mean() if d1 else 0.0
    s2 = smoothed[d1:d1 + d2].mean() if d2 else 0.0
    s3 = smoothed[d1 + d2:].mean() if d3 else 0.0

    total_smooth = d1 * s1 + d2 * s2 + d3 * s3

    return {
        "stage1_days": d1,
        "stage1_pp": round(s1, 2),
        "stage2_days": d2,
        "stage2_pp": round(s2, 2),
        "stage3_days": d3,
        "stage3_pp": round(s3, 2),
        "total_pp_check": round(total_smooth, 2),
        "daily_schedule": smoothed.round(2).tolist()
    }


# ---------- 2. LLM 客户端 ----------
model_client = OpenAIChatCompletionClient(
    model="deepseek-chat",
    base_url="https://api.deepseek.com",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    model_info={
        "name": "deepseek-chat",
        "family": "gpt-4o",
        "vision": False,
        "json_output": True,
        "structured_output": False,  # <- 新增字段，消除 Warning
        "function_calling": True,
        "parameters": {"temperature": 0, "top_p": 0.9, "max_tokens": 2048}
    }
)

# ---------- 3. Agent ----------
agent = AssistantAgent(
    name="LightAgent",
    model_client=model_client,
    system_message=(
        "你是叶用生菜光周期调控助手。当用户提供栽培参数（总天数、最小光周期、最大光周期、平均光周期）时，"\
        "请调用calc_photoperiod函数计算光周期方案，然后用**一句话**向种植者说明核心要点及相比恒定光周期的好处。"
    ),
    tools=[calc_photoperiod]
)

# ---------- 6. 写出每日光照表 ----------
def write_daily_csv(daily_schedule: list[float]) -> Path:
    """把 daily_schedule 写成 csv → BASE_PATH/config/daily_light.csv"""
    root = Path(BASE_PATH).expanduser().resolve()  # 支持 ~ 符号
    folder = root / "config"
    folder.mkdir(exist_ok=True, parents=True)      # 一次性建好

    csv_path = folder / "daily_light.csv"
    with csv_path.open("w", newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["day", "light_hours"])
        for day, hrs in enumerate(daily_schedule, 1):
            writer.writerow([day, hrs])
    return csv_path


# ---------- 4. 交互入口 ----------
async def main() -> None:
    print("=== 植物光周期自动调控助手 ===")
    days = int(input("总栽培天数："))
    h_min = float(input("最小光周期（h）："))
    h_max = float(input("最大光周期（h）："))
    h_ave = float(input("平均光周期（h）："))

    task_text = (
        f"我需要为叶用生菜制定光周期方案，参数如下：总天数={days}天，最小光周期={h_min}h，"
        f"最大光周期={h_max}h，平均光周期={h_ave}h。请帮我计算并解释方案。"
    )

    # 改用 run() 即可 await
    result = await agent.run(task=task_text)
    # 把助手返回的内容打印出来
    for msg in result.messages:
        if isinstance(msg, TextMessage):
            print(msg.content)

    # ===== 写出每日光照表 =====
    calc = calc_photoperiod(days, h_min, h_max, h_ave)
    csv_file = write_daily_csv(calc["daily_schedule"])
    print(f"每日光照表已生成：{csv_file}")

# ---------- 5. 启动 ----------
if __name__ == "__main__":
    asyncio.run(main())
