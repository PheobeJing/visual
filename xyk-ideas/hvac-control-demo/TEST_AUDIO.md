# 音效系统测试指南

## 快速测试步骤

### 1. 启动应用
```bash
python app.py
```
访问: http://127.0.0.1:8050/

### 2. 测试音效系统

#### 测试前准备
1. 确保系统音量已开启
2. 确保浏览器允许音频播放（某些浏览器可能需要用户交互后才能播放音频）
3. 打开浏览器控制台（F12）查看是否有JavaScript错误

#### 基础功能测试
1. **启动模拟**
   - 点击 ▶️播放 按钮
   - 等待2-3秒，观察是否有动作发生
   - 如果听到音效，说明系统正常工作

2. **静音功能测试**
   - 点击 🔊音效 按钮（绿色）
   - 按钮应变为 🔇静音（红色）
   - 此时不应再听到音效
   - 再次点击切换回音效模式

3. **不同动作音效测试**
   - 继续观察右侧动作日志
   - 不同类型的动作应有不同音调：
     * ASHP开启：清脆高音（叮）
     * ASHP制冷模式：双音和弦（噔噔）
     * ASHP制热模式：温暖和弦（当当）
     * ERV/DEH开启：中等音调
     * 温度/风速调节：较长持续音

## 常见问题排查

### 问题1：听不到任何音效
**可能原因**:
- 系统音量关闭或过小
- 浏览器静音
- 浏览器不支持Web Audio API（极少见）
- 音效按钮处于静音状态（红色🔇）

**解决方案**:
1. 检查系统音量
2. 检查浏览器音量
3. 点击音效按钮确保显示🔊（绿色）
4. 尝试更换浏览器（推荐Chrome/Edge）

### 问题2：有JavaScript错误
**检查步骤**:
1. 打开浏览器控制台（F12 → Console标签）
2. 查看是否有红色错误信息
3. 如果看到"Cannot read properties of undefined"错误：
   - 刷新页面重试
   - 如果持续出现，可能是callback依赖问题

**临时解决方案**:
- 关闭音效功能：点击🔇静音按钮
- 继续使用可视化功能

### 问题3：音效断断续续
**可能原因**:
- 系统性能不足
- 播放速度设置过快

**解决方案**:
1. 降低播放速度（设置为0.5x或1x）
2. 关闭其他占用资源的程序
3. 如果问题持续，可以暂时关闭音效

## 音效映射参考

| 设备 | 动作 | 频率(Hz) | 时长(秒) | 描述 |
|------|------|----------|----------|------|
| ASHP | 开启 | 523 (C5) | 0.15 | 清脆高音 |
| ASHP | 关闭 | 262 (C4) | 0.15 | 低沉音 |
| ASHP | 温度上升 | 659 (E5) | 0.30 | 上升感 |
| ASHP | 温度下降 | 440 (A4) | 0.30 | 下降感 |
| ASHP | 风速上升 | 784 (G5) | 0.25 | 高能量 |
| ASHP | 风速下降 | 294 (D4) | 0.25 | 低能量 |
| ASHP | 制冷模式 | 349+440 (F4+A4) | 0.40 | 清凉和弦 |
| ASHP | 制热模式 | 659+784 (E5+G5) | 0.40 | 温暖和弦 |
| ASHP | 除湿模式 | 494 (B4) | 0.35 | 独特音 |
| ERV | 开启 | 392 (G4) | 0.15 | 中音 |
| ERV | 关闭 | 294 (D4) | 0.15 | 低音 |
| ERV | 风速上升 | 440 (A4) | 0.25 | 标准音 |
| ERV | 风速下降 | 349 (F4) | 0.25 | 柔和音 |
| DEH | 开启 | 330 (E4) | 0.15 | 简单音 |
| DEH | 关闭 | 262 (C4) | 0.15 | 结束音 |

## 技术验证

### 浏览器控制台测试
可以在浏览器控制台手动测试音频系统：

```javascript
// 测试单音
const audioCtx = new AudioContext();
const oscillator = audioCtx.createOscillator();
const gainNode = audioCtx.createGain();
oscillator.connect(gainNode);
gainNode.connect(audioCtx.destination);
oscillator.frequency.value = 440; // A4音
oscillator.type = 'sine';
gainNode.gain.setValueAtTime(0, audioCtx.currentTime);
gainNode.gain.linearRampToValueAtTime(0.3, audioCtx.currentTime + 0.01);
gainNode.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.3);
oscillator.start(audioCtx.currentTime);
oscillator.stop(audioCtx.currentTime + 0.3);
```

如果以上代码能播放音效，说明浏览器支持Web Audio API。

## 性能监控

正常情况下：
- CPU使用率应< 30%
- 内存使用应< 200MB
- 音效播放无明显延迟（< 100ms）
- 无JavaScript错误

## 反馈信息

如果遇到问题，请收集以下信息：
1. 浏览器类型和版本
2. 操作系统版本
3. 控制台错误信息（如有）
4. 具体触发问题的操作步骤
