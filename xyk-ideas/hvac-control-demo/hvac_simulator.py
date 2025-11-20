"""
HVAC Control Strategy Simulator
模拟ASHP、ERV、DEH三设备的动态控制策略
生成温湿度、能耗、电费和控制动作序列的时序数据
"""

import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class DeviceType(Enum):
    """设备类型"""
    ASHP = "ASHP"  # 空气源热泵
    ERV = "ERV"    # 能量回收通风
    DEH = "DEH"    # 除湿机


class ActionType(Enum):
    """动作类型"""
    # ASHP 动作
    ASHP_ON = "ASHP开启"
    ASHP_OFF = "ASHP关闭"
    ASHP_TEMP_UP = "ASHP设定温度上升"
    ASHP_TEMP_DOWN = "ASHP设定温度下降"
    ASHP_FAN_UP = "ASHP风速上升"
    ASHP_FAN_DOWN = "ASHP风速下降"
    ASHP_COOLING = "ASHP制冷模式"
    ASHP_HEATING = "ASHP制热模式"
    ASHP_DEHUMID = "ASHP除湿模式"

    # ERV 动作
    ERV_ON = "ERV开启"
    ERV_OFF = "ERV关闭"
    ERV_FAN_UP = "ERV风速上升"
    ERV_FAN_DOWN = "ERV风速下降"

    # DEH 动作
    DEH_ON = "DEH开启"
    DEH_OFF = "DEH关闭"


@dataclass
class ControlAction:
    """控制动作"""
    timestamp: datetime
    device: DeviceType
    action: ActionType
    is_instant: bool  # True=瞬时动作(竖线), False=持续动作(覆盖色)
    duration: float = 0.0  # 持续时间（分钟），瞬时动作为0


@dataclass
class HVACState:
    """HVAC系统状态"""
    timestamp: datetime
    # 温湿度
    temperature: float  # 实测温度 (°C)
    humidity: float  # 实测湿度 (%)
    temp_pred: Optional[float] = None  # 预测温度
    hum_pred: Optional[float] = None  # 预测湿度

    # 能耗
    ashp_power: float = 0.0  # ASHP功率 (kW)
    erv_power: float = 0.0   # ERV功率 (kW)
    deh_power: float = 0.0   # DEH功率 (kW)
    total_power: float = 0.0  # 总功率 (kW)
    power_pred: Optional[float] = None  # 预测功率 (kW)

    # 电费
    electricity_price: float = 0.0  # 电价 (元/kWh)
    cost: float = 0.0  # 电费 (元)
    cost_pred: Optional[float] = None  # 预测电费 (元)

    # 设备状态
    ashp_on: bool = False
    ashp_mode: str = "待机"  # 制冷/制热/除湿/待机
    ashp_setpoint: float = 22.0  # 设定温度
    ashp_fan_speed: int = 1  # 风速档位 1-5

    erv_on: bool = False
    erv_fan_speed: int = 1  # 风速档位 1-3

    deh_on: bool = False

    # 控制策略
    strategy: str = "自适应控制"
    status: str = "正常"  # 正常/预警/故障
    comfort_score: float = 100.0  # 舒适度评分 0-100


class HVACControlSimulator:
    """HVAC控制策略模拟器"""

    def __init__(self, start_time: datetime = None, timestep_minutes: int = 5):
        """
        初始化模拟器

        Args:
            start_time: 起始时间
            timestep_minutes: 时间步长（分钟）
        """
        self.start_time = start_time or datetime.now()
        self.timestep_minutes = timestep_minutes
        self.current_step = 0

        # 系统状态
        self.state = HVACState(
            timestamp=self.start_time,
            temperature=22.0,
            humidity=60.0
        )

        # 历史数据
        self.history: List[HVACState] = []
        self.actions: List[ControlAction] = []

        # 峰谷电价设定 (元/kWh)
        self.peak_price = 1.2  # 高峰电价 8:00-22:00
        self.valley_price = 0.4  # 低谷电价 22:00-8:00

        # 随机种子（用于可重复的模拟）
        np.random.seed(42)

    def _get_electricity_price(self, timestamp: datetime) -> float:
        """获取当前时段电价"""
        hour = timestamp.hour
        if 8 <= hour < 22:
            return self.peak_price
        else:
            return self.valley_price

    def _generate_temperature_actual(self) -> float:
        """生成实测温度"""
        # 基础温度 + 日周期波动 + 随机噪声
        base_temp = 22.0
        hour = self.state.timestamp.hour

        # 日周期：白天稍高，夜间稍低
        daily_variation = 2.0 * np.sin(2 * np.pi * (hour - 6) / 24)

        # 控制器影响
        if self.state.ashp_on:
            if self.state.ashp_mode == "制冷":
                control_effect = -(self.state.temperature - self.state.ashp_setpoint) * 0.3
            elif self.state.ashp_mode == "制热":
                control_effect = (self.state.ashp_setpoint - self.state.temperature) * 0.3
            else:
                control_effect = 0
        else:
            control_effect = 0

        # 随机噪声
        noise = np.random.normal(0, 0.2)

        new_temp = self.state.temperature + (daily_variation + control_effect + noise) * 0.1
        return np.clip(new_temp, 18.0, 28.0)

    def _generate_humidity_actual(self) -> float:
        """生成实测湿度"""
        # 基础湿度 + 随机波动
        base_hum = 60.0

        # DEH除湿影响
        if self.state.deh_on:
            dehumid_effect = -2.0
        elif self.state.ashp_mode == "除湿":
            dehumid_effect = -1.0
        else:
            dehumid_effect = 0

        # ERV新风影响（假设外部湿度更高）
        if self.state.erv_on:
            erv_effect = 0.5 * self.state.erv_fan_speed
        else:
            erv_effect = 0

        # 随机噪声
        noise = np.random.normal(0, 1.0)

        new_hum = self.state.humidity + (dehumid_effect + erv_effect + noise) * 0.2
        return np.clip(new_hum, 40.0, 80.0)

    def _generate_prediction(self, steps_ahead: int = 5) -> Tuple[float, float, float, float]:
        """
        生成预测值（提前steps_ahead步）

        Returns:
            (预测温度, 预测湿度, 预测功率, 预测电费)
        """
        # 简单的线性预测模型
        if len(self.history) >= 3:
            recent_temps = [s.temperature for s in self.history[-3:]]
            temp_trend = np.mean(np.diff(recent_temps))
            temp_pred = self.state.temperature + temp_trend * steps_ahead

            recent_hums = [s.humidity for s in self.history[-3:]]
            hum_trend = np.mean(np.diff(recent_hums))
            hum_pred = self.state.humidity + hum_trend * steps_ahead

            recent_powers = [s.total_power for s in self.history[-3:]]
            power_trend = np.mean(np.diff(recent_powers))
            power_pred = self.state.total_power + power_trend * steps_ahead

            recent_costs = [s.cost for s in self.history[-3:]]
            cost_trend = np.mean(np.diff(recent_costs))
            cost_pred = self.state.cost + cost_trend * steps_ahead
        else:
            # 初始阶段，预测值接近当前值
            temp_pred = self.state.temperature + np.random.normal(0, 0.5)
            hum_pred = self.state.humidity + np.random.normal(0, 2.0)
            power_pred = self.state.total_power + np.random.normal(0, 0.2)
            cost_pred = self.state.cost + np.random.normal(0, 0.01)

        return (
            np.clip(temp_pred, 18.0, 28.0),
            np.clip(hum_pred, 40.0, 80.0),
            max(0, power_pred),
            max(0, cost_pred)
        )

    def _calculate_power_consumption(self) -> Dict[str, float]:
        """计算各设备功率消耗"""
        ashp_power = 0.0
        if self.state.ashp_on:
            # 基础功率 + 风速影响 + 负荷影响
            base_power = 3.0  # kW
            fan_factor = 1.0 + (self.state.ashp_fan_speed - 1) * 0.15

            # 制冷/制热负荷
            if self.state.ashp_mode == "制冷":
                load_factor = abs(self.state.temperature - self.state.ashp_setpoint) * 0.1
            elif self.state.ashp_mode == "制热":
                load_factor = abs(self.state.ashp_setpoint - self.state.temperature) * 0.12
            else:  # 除湿
                load_factor = 0.5

            ashp_power = base_power * fan_factor * (1 + load_factor)

        erv_power = 0.0
        if self.state.erv_on:
            # 风机功率
            erv_power = 0.2 * self.state.erv_fan_speed  # kW

        deh_power = 0.0
        if self.state.deh_on:
            deh_power = 1.5  # kW

        total_power = ashp_power + erv_power + deh_power

        return {
            'ashp': ashp_power,
            'erv': erv_power,
            'deh': deh_power,
            'total': total_power
        }

    def _calculate_comfort_score(self) -> float:
        """计算舒适度评分"""
        # 理想温度范围: 22-24°C
        temp_score = 100 - abs(self.state.temperature - 23.0) * 10
        temp_score = max(0, min(100, temp_score))

        # 理想湿度范围: 50-60%
        hum_score = 100 - abs(self.state.humidity - 55.0) * 2
        hum_score = max(0, min(100, hum_score))

        # 综合评分
        comfort_score = 0.6 * temp_score + 0.4 * hum_score
        return round(comfort_score, 1)

    def _generate_control_actions(self) -> List[ControlAction]:
        """生成控制动作序列 - 更积极的自适应控制"""
        actions = []
        current_time = self.state.timestamp
        temp = self.state.temperature
        hum = self.state.humidity

        # ========== ASHP 温度控制（更灵敏的阈值） ==========
        # 温度过高 -> 制冷
        if temp > 23.5 and not self.state.ashp_on:
            actions.append(ControlAction(
                timestamp=current_time, device=DeviceType.ASHP,
                action=ActionType.ASHP_ON, is_instant=True
            ))
            actions.append(ControlAction(
                timestamp=current_time, device=DeviceType.ASHP,
                action=ActionType.ASHP_COOLING, is_instant=False, duration=40.0
            ))
            self.state.ashp_on = True
            self.state.ashp_mode = "制冷"
            self.state.ashp_setpoint = 22.0

        # 温度过低 -> 制热
        elif temp < 21.5 and not self.state.ashp_on:
            actions.append(ControlAction(
                timestamp=current_time, device=DeviceType.ASHP,
                action=ActionType.ASHP_ON, is_instant=True
            ))
            actions.append(ControlAction(
                timestamp=current_time, device=DeviceType.ASHP,
                action=ActionType.ASHP_HEATING, is_instant=False, duration=40.0
            ))
            self.state.ashp_on = True
            self.state.ashp_mode = "制热"
            self.state.ashp_setpoint = 23.0

        # 温度达标 -> 关闭ASHP
        elif self.state.ashp_on and 22.0 <= temp <= 23.0:
            if np.random.random() < 0.5:  # 50%概率关闭 - 更频繁
                actions.append(ControlAction(
                    timestamp=current_time, device=DeviceType.ASHP,
                    action=ActionType.ASHP_OFF, is_instant=True
                ))
                self.state.ashp_on = False
                self.state.ashp_mode = "待机"

        # ========== ASHP 模式切换（运行时微调） ==========
        if self.state.ashp_on:
            # 设定温度微调
            if np.random.random() < 0.45:  # 45%概率调整设定温度 - 更频繁
                if temp > self.state.ashp_setpoint + 0.5:
                    actions.append(ControlAction(
                        timestamp=current_time, device=DeviceType.ASHP,
                        action=ActionType.ASHP_TEMP_DOWN, is_instant=False, duration=20.0
                    ))
                    self.state.ashp_setpoint = max(20.0, self.state.ashp_setpoint - 0.5)
                elif temp < self.state.ashp_setpoint - 0.5:
                    actions.append(ControlAction(
                        timestamp=current_time, device=DeviceType.ASHP,
                        action=ActionType.ASHP_TEMP_UP, is_instant=False, duration=20.0
                    ))
                    self.state.ashp_setpoint = min(26.0, self.state.ashp_setpoint + 0.5)

            # 风速调节（更频繁）
            if np.random.random() < 0.5:  # 50%概率调整风速 - 更频繁
                temp_diff = abs(temp - self.state.ashp_setpoint)
                if temp_diff > 1.0 and self.state.ashp_fan_speed < 5:
                    actions.append(ControlAction(
                        timestamp=current_time, device=DeviceType.ASHP,
                        action=ActionType.ASHP_FAN_UP, is_instant=False, duration=25.0
                    ))
                    self.state.ashp_fan_speed = min(5, self.state.ashp_fan_speed + 1)
                elif temp_diff < 0.5 and self.state.ashp_fan_speed > 1:
                    actions.append(ControlAction(
                        timestamp=current_time, device=DeviceType.ASHP,
                        action=ActionType.ASHP_FAN_DOWN, is_instant=False, duration=25.0
                    ))
                    self.state.ashp_fan_speed = max(1, self.state.ashp_fan_speed - 1)

            # 除湿模式切换
            if hum > 65 and self.state.ashp_mode != "除湿" and np.random.random() < 0.35:
                actions.append(ControlAction(
                    timestamp=current_time, device=DeviceType.ASHP,
                    action=ActionType.ASHP_DEHUMID, is_instant=False, duration=35.0
                ))
                self.state.ashp_mode = "除湿"

        # ========== DEH 除湿控制（更灵敏） ==========
        if hum > 65 and not self.state.deh_on:
            actions.append(ControlAction(
                timestamp=current_time, device=DeviceType.DEH,
                action=ActionType.DEH_ON, is_instant=True
            ))
            self.state.deh_on = True
        elif hum < 58 and self.state.deh_on:
            actions.append(ControlAction(
                timestamp=current_time, device=DeviceType.DEH,
                action=ActionType.DEH_OFF, is_instant=True
            ))
            self.state.deh_on = False

        # ========== ERV 通风控制（更动态） ==========
        hour = current_time.hour
        if 7 <= hour < 21 and not self.state.erv_on:
            actions.append(ControlAction(
                timestamp=current_time, device=DeviceType.ERV,
                action=ActionType.ERV_ON, is_instant=True
            ))
            self.state.erv_on = True
            self.state.erv_fan_speed = 2
        elif (hour >= 21 or hour < 7) and self.state.erv_on:
            actions.append(ControlAction(
                timestamp=current_time, device=DeviceType.ERV,
                action=ActionType.ERV_OFF, is_instant=True
            ))
            self.state.erv_on = False

        # ERV风速动态调节
        if self.state.erv_on and np.random.random() < 0.4:  # 40%概率调整 - 更频繁
            if hum > 60 and self.state.erv_fan_speed < 3:
                actions.append(ControlAction(
                    timestamp=current_time, device=DeviceType.ERV,
                    action=ActionType.ERV_FAN_UP, is_instant=False, duration=30.0
                ))
                self.state.erv_fan_speed = min(3, self.state.erv_fan_speed + 1)
            elif hum < 55 and self.state.erv_fan_speed > 1:
                actions.append(ControlAction(
                    timestamp=current_time, device=DeviceType.ERV,
                    action=ActionType.ERV_FAN_DOWN, is_instant=False, duration=30.0
                ))
                self.state.erv_fan_speed = max(1, self.state.erv_fan_speed - 1)

        return actions

    def step(self) -> HVACState:
        """
        执行一个时间步的模拟

        Returns:
            当前时刻的系统状态
        """
        # 更新时间
        self.current_step += 1
        self.state.timestamp = self.start_time + timedelta(minutes=self.timestep_minutes * self.current_step)

        # 生成控制动作
        new_actions = self._generate_control_actions()
        self.actions.extend(new_actions)

        # 更新温湿度
        self.state.temperature = self._generate_temperature_actual()
        self.state.humidity = self._generate_humidity_actual()

        # 生成预测
        self.state.temp_pred, self.state.hum_pred, self.state.power_pred, self.state.cost_pred = self._generate_prediction(steps_ahead=5)

        # 计算功率
        power = self._calculate_power_consumption()
        self.state.ashp_power = power['ashp']
        self.state.erv_power = power['erv']
        self.state.deh_power = power['deh']
        self.state.total_power = power['total']

        # 计算电费
        self.state.electricity_price = self._get_electricity_price(self.state.timestamp)
        # 电费 = 功率(kW) × 时间(h) × 电价(元/kWh)
        self.state.cost = self.state.total_power * (self.timestep_minutes / 60.0) * self.state.electricity_price

        # 计算舒适度
        self.state.comfort_score = self._calculate_comfort_score()

        # 状态评估
        if self.state.comfort_score < 60:
            self.state.status = "预警"
        elif np.random.random() < 0.02:  # 2%概率模拟故障
            self.state.status = "故障"
            self.state.strategy = "故障诊断中"
        else:
            self.state.status = "正常"
            self.state.strategy = "自适应控制"

        # 保存历史
        self.history.append(self.state)

        # 创建新状态副本（避免引用问题）
        from copy import deepcopy
        self.state = deepcopy(self.state)

        return self.history[-1]

    def simulate(self, num_steps: int) -> Tuple[List[HVACState], List[ControlAction]]:
        """
        运行多步模拟

        Args:
            num_steps: 模拟步数

        Returns:
            (状态历史, 动作历史)
        """
        for _ in range(num_steps):
            self.step()

        return self.history, self.actions

    def reset(self):
        """重置模拟器"""
        self.current_step = 0
        self.state = HVACState(
            timestamp=self.start_time,
            temperature=22.0,
            humidity=60.0
        )
        self.history = []
        self.actions = []


if __name__ == "__main__":
    # 测试代码
    print("HVAC Control Simulator Test")
    print("=" * 50)

    simulator = HVACControlSimulator(timestep_minutes=5)
    history, actions = simulator.simulate(num_steps=20)

    print(f"\n模拟了 {len(history)} 个时间步")
    print(f"生成了 {len(actions)} 个控制动作")

    print("\n最后5个状态:")
    for state in history[-5:]:
        print(f"  {state.timestamp.strftime('%H:%M')} - "
              f"温度: {state.temperature:.1f}°C, "
              f"湿度: {state.humidity:.1f}%, "
              f"功率: {state.total_power:.2f}kW, "
              f"舒适度: {state.comfort_score:.1f}")

    print("\n最后5个动作:")
    for action in actions[-5:]:
        print(f"  {action.timestamp.strftime('%H:%M')} - "
              f"{action.device.value}: {action.action.value} "
              f"({'瞬时' if action.is_instant else f'持续{action.duration}min'})")
