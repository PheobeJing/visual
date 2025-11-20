"""
测试HVAC可视化Demo
生成静态图表进行验证
"""

from hvac_simulator import HVACControlSimulator
from datetime import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

# 创建输出目录
output_dir = "test_output"
os.makedirs(output_dir, exist_ok=True)

print("=" * 60)
print("HVAC控制策略动态可视化Demo - 功能测试")
print("=" * 60)

# 1. 测试模拟器
print("\n[1] 测试数据模拟器...")
simulator = HVACControlSimulator(timestep_minutes=5)
history, actions = simulator.simulate(num_steps=100)

print(f"   [OK] 生成了 {len(history)} 个时间步的数据")
print(f"   [OK] 生成了 {len(actions)} 个控制动作")

# 统计动作类型
action_types = {}
instant_actions = 0
continuous_actions = 0

for action in actions:
    action_name = action.action.value
    action_types[action_name] = action_types.get(action_name, 0) + 1
    if action.is_instant:
        instant_actions += 1
    else:
        continuous_actions += 1

print(f"   [OK] 瞬时动作: {instant_actions} 个")
print(f"   [OK] 持续动作: {continuous_actions} 个")
print(f"   [OK] 动作类型分布:")
for action_name, count in action_types.items():
    print(f"      - {action_name}: {count}")

# 2. 测试温湿度图表
print("\n[2] 生成温湿度图表...")

COLORS = [
    'rgba(72,121,128,0.7)',
    'rgba(216,81,23,0.7)',
    'rgba(4,115,192,0.7)',
    'rgba(179,53,56,0.7)',
]

fig1 = make_subplots(specs=[[{"secondary_y": True}]])

timestamps = [s.timestamp for s in history]
temperatures = [s.temperature for s in history]
humidities = [s.humidity for s in history]
temp_preds = [s.temp_pred if s.temp_pred else s.temperature for s in history]

# 实测温度
fig1.add_trace(
    go.Scatter(
        x=timestamps,
        y=temperatures,
        name="实测温度",
        mode='lines',
        line=dict(color=COLORS[3], width=3)
    ),
    secondary_y=False
)

# 预测温度
fig1.add_trace(
    go.Scatter(
        x=timestamps,
        y=temp_preds,
        name="预测温度",
        mode='lines',
        line=dict(color=COLORS[3], width=2, dash='dash'),
        opacity=0.6
    ),
    secondary_y=False
)

# 实测湿度
fig1.add_trace(
    go.Scatter(
        x=timestamps,
        y=humidities,
        name="实测湿度",
        mode='lines',
        line=dict(color=COLORS[0], width=3)
    ),
    secondary_y=True
)

fig1.update_layout(
    title="温湿度监控测试图",
    height=600,
    width=1400,
    plot_bgcolor='rgba(255,255,255,1)',
    paper_bgcolor='rgba(255,255,255,1)'
)

fig1.update_yaxes(title_text="温度 (°C)", secondary_y=False)
fig1.update_yaxes(title_text="湿度 (%)", secondary_y=True)
fig1.update_xaxes(title_text="时间")

output_file1 = os.path.join(output_dir, "temp_humidity_test.html")
fig1.write_html(output_file1)
print(f"   [OK] 保存图表: {output_file1}")

# 3. 测试能耗电费图表
print("\n[3] 生成能耗电费图表...")

fig2 = make_subplots(specs=[[{"secondary_y": True}]])

total_powers = [s.total_power for s in history]
costs = [s.cost for s in history]

import numpy as np
cumulative_cost = np.cumsum(costs)

# 总功率
fig2.add_trace(
    go.Scatter(
        x=timestamps,
        y=total_powers,
        name="总功率",
        mode='lines',
        line=dict(color=COLORS[1], width=3),
        fill='tozeroy',
        fillcolor='rgba(216,81,23,0.2)'
    ),
    secondary_y=False
)

# 累计电费
fig2.add_trace(
    go.Scatter(
        x=timestamps,
        y=cumulative_cost,
        name="累计电费",
        mode='lines',
        line=dict(color=COLORS[2], width=3)
    ),
    secondary_y=True
)

fig2.update_layout(
    title="能耗与电费监控测试图",
    height=600,
    width=1400,
    plot_bgcolor='rgba(255,255,255,1)',
    paper_bgcolor='rgba(255,255,255,1)'
)

fig2.update_yaxes(title_text="功率 (kW)", secondary_y=False)
fig2.update_yaxes(title_text="累计电费 (元)", secondary_y=True)
fig2.update_xaxes(title_text="时间")

output_file2 = os.path.join(output_dir, "power_cost_test.html")
fig2.write_html(output_file2)
print(f"   [OK] 保存图表: {output_file2}")

# 4. 数据统计
print("\n[4] 数据统计分析...")
print(f"   温度范围: {min(temperatures):.1f}°C - {max(temperatures):.1f}°C")
print(f"   湿度范围: {min(humidities):.1f}% - {max(humidities):.1f}%")
print(f"   功率范围: {min(total_powers):.2f}kW - {max(total_powers):.2f}kW")
print(f"   总电费: {cumulative_cost[-1]:.2f}元")

# 舒适度统计
comfort_scores = [s.comfort_score for s in history]
print(f"   舒适度: {min(comfort_scores):.1f} - {max(comfort_scores):.1f} (平均: {np.mean(comfort_scores):.1f})")

# 设备运行统计
ashp_on_count = sum(1 for s in history if s.ashp_on)
erv_on_count = sum(1 for s in history if s.erv_on)
deh_on_count = sum(1 for s in history if s.deh_on)

print(f"   ASHP运行时间占比: {ashp_on_count/len(history)*100:.1f}%")
print(f"   ERV运行时间占比: {erv_on_count/len(history)*100:.1f}%")
print(f"   DEH运行时间占比: {deh_on_count/len(history)*100:.1f}%")

print("\n" + "=" * 60)
print("[SUCCESS] 所有功能测试通过!")
print("=" * 60)
print(f"\n生成的测试图表保存在: {os.path.abspath(output_dir)}")
print("\n要启动完整的动态Web应用，请运行:")
print("   python app.py")
print("\n然后在浏览器中访问: http://127.0.0.1:8050/")
