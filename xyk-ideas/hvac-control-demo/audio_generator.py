"""
服务器端音频生成器 - 生成HVAC控制动作优美音效
使用scipy生成多谐波音频波形，模拟真实乐器音色
"""

import numpy as np
import scipy.io.wavfile as wav
import io
import base64
from typing import Dict, List, Tuple
import random


class AudioGenerator:
    """服务器端音频生成器 - 增强版"""

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        np.random.seed(42)  # 确保可重复性

        # 音效映射配置 - 更长的持续时间，让音效更悦耳
        self.sound_configs = {
            # ASHP动作 - 使用钢琴-like音色
            'ASHP开启': {
                'base_freq': 523.25,  # C5
                'duration': 0.8,      # 延长到0.8秒，让铃声更完整
                'type': 'bell',
                'harmonics': [(1.0, 0.8), (2.0, 0.4), (3.0, 0.2), (4.0, 0.1)],
                'attack': 0.05, 'decay': 0.6, 'sustain': 0.1, 'release': 0.15
            },
            'ASHP关闭': {
                'base_freq': 261.63,  # C4
                'duration': 1.0,      # 延长到1.0秒
                'type': 'bell',
                'harmonics': [(1.0, 0.9), (2.0, 0.3), (3.0, 0.15)],
                'attack': 0.08, 'decay': 0.8, 'sustain': 0.1, 'release': 0.12
            },
            'ASHP设定温度上升': {
                'base_freq': 659.25,  # E5
                'duration': 1.2,      # 对应20分钟动作 -> 1.2秒音效
                'type': 'chime',
                'harmonics': [(1.0, 1.0), (2.0, 0.6), (3.0, 0.3), (4.0, 0.2)],
                'attack': 0.1, 'decay': 0.9, 'sustain': 0.2, 'release': 0.2
            },
            'ASHP设定温度下降': {
                'base_freq': 440.0,   # A4
                'duration': 1.2,      # 对应20分钟动作 -> 1.2秒音效
                'type': 'chime',
                'harmonics': [(1.0, 1.0), (2.0, 0.5), (3.0, 0.25)],
                'attack': 0.1, 'decay': 0.9, 'sustain': 0.2, 'release': 0.2
            },
            'ASHP风速上升': {
                'base_freq': 783.99,  # G5
                'duration': 1.4,      # 对应25分钟动作 -> 1.4秒音效
                'type': 'marimba',
                'harmonics': [(1.0, 1.0), (2.0, 0.4), (3.0, 0.2)],
                'attack': 0.05, 'decay': 1.1, 'sustain': 0.2, 'release': 0.25
            },
            'ASHP风速下降': {
                'base_freq': 293.66,  # D4
                'duration': 1.4,      # 对应25分钟动作 -> 1.4秒音效
                'type': 'marimba',
                'harmonics': [(1.0, 1.0), (2.0, 0.4), (3.0, 0.2)],
                'attack': 0.05, 'decay': 1.1, 'sustain': 0.2, 'release': 0.25
            },
            'ASHP制冷模式': {
                'base_freq': 349.23,  # F4
                'duration': 1.8,      # 对应40分钟动作 -> 1.8秒音效
                'type': 'chord',
                'harmonics': [(1.0, 0.8), (1.25, 0.6), (1.5, 0.4)],  # 小三和弦
                'attack': 0.15, 'decay': 1.3, 'sustain': 0.3, 'release': 0.35
            },
            'ASHP制热模式': {
                'base_freq': 659.25,  # E5
                'duration': 1.8,      # 对应40分钟动作 -> 1.8秒音效
                'type': 'chord',
                'harmonics': [(1.0, 0.8), (1.189, 0.6), (1.5, 0.4)],  # 大三和弦
                'attack': 0.15, 'decay': 1.3, 'sustain': 0.3, 'release': 0.35
            },
            'ASHP除湿模式': {
                'base_freq': 493.88,  # B4
                'duration': 1.6,      # 对应35分钟动作 -> 1.6秒音效
                'type': 'bell',
                'harmonics': [(1.0, 1.0), (2.0, 0.5), (3.0, 0.3), (4.0, 0.2), (5.0, 0.1)],
                'attack': 0.08, 'decay': 1.2, 'sustain': 0.3, 'release': 0.32
            },

            # ERV动作 - 使用风琴-like音色
            'ERV开启': {
                'base_freq': 392.0,   # G4
                'duration': 0.9,      # 延长到0.9秒
                'type': 'organ',
                'harmonics': [(1.0, 0.9), (2.0, 0.3), (3.0, 0.1)],
                'attack': 0.05, 'decay': 0.7, 'sustain': 0.15, 'release': 0.15
            },
            'ERV关闭': {
                'base_freq': 293.66,  # D4
                'duration': 1.1,      # 延长到1.1秒
                'type': 'organ',
                'harmonics': [(1.0, 0.8), (2.0, 0.4), (3.0, 0.2)],
                'attack': 0.08, 'decay': 0.9, 'sustain': 0.15, 'release': 0.13
            },
            'ERV风速上升': {
                'base_freq': 440.0,   # A4
                'duration': 1.5,      # 对应30分钟动作 -> 1.5秒音效
                'type': 'flute',
                'harmonics': [(1.0, 1.0), (2.0, 0.3), (3.0, 0.1)],
                'attack': 0.12, 'decay': 1.1, 'sustain': 0.3, 'release': 0.28
            },
            'ERV风速下降': {
                'base_freq': 349.23,  # F4
                'duration': 1.5,      # 对应30分钟动作 -> 1.5秒音效
                'type': 'flute',
                'harmonics': [(1.0, 1.0), (2.0, 0.3), (3.0, 0.1)],
                'attack': 0.12, 'decay': 1.1, 'sustain': 0.3, 'release': 0.28
            },

            # DEH动作 - 使用打击乐音色
            'DEH开启': {
                'base_freq': 329.63,  # E4
                'duration': 0.6,      # 延长到0.6秒
                'type': 'percussion',
                'harmonics': [(1.0, 0.9), (1.5, 0.5), (2.0, 0.3)],
                'attack': 0.02, 'decay': 0.5, 'sustain': 0.05, 'release': 0.08
            },
            'DEH关闭': {
                'base_freq': 261.63,  # C4
                'duration': 0.7,      # 延长到0.7秒
                'type': 'percussion',
                'harmonics': [(1.0, 0.8), (1.3, 0.6), (2.0, 0.2)],
                'attack': 0.03, 'decay': 0.6, 'sustain': 0.05, 'release': 0.07
            }
        }

    def generate_waveform(self, frequency: float, duration: float, waveform_type: str = 'sine') -> np.ndarray:
        """生成不同类型的波形"""
        t = np.linspace(0, duration, int(self.sample_rate * duration), False)

        if waveform_type == 'sine':
            return np.sin(2 * np.pi * frequency * t)
        elif waveform_type == 'triangle':
            return 2 * np.abs(2 * (t * frequency - np.floor(t * frequency + 0.5))) - 1
        elif waveform_type == 'square':
            return np.sign(np.sin(2 * np.pi * frequency * t))
        elif waveform_type == 'sawtooth':
            return 2 * (t * frequency - np.floor(t * frequency + 0.5))
        else:
            return np.sin(2 * np.pi * frequency * t)

    def apply_adsr_envelope(self, audio: np.ndarray, attack: float, decay: float,
                           sustain: float, release: float, sample_rate: int) -> np.ndarray:
        """应用ADSR包络"""
        total_samples = len(audio)
        attack_samples = int(attack * sample_rate)
        decay_samples = int(decay * sample_rate)
        release_samples = int(release * sample_rate)
        sustain_samples = total_samples - attack_samples - decay_samples - release_samples

        if sustain_samples < 0:
            sustain_samples = 0

        envelope = np.ones(total_samples)

        # Attack
        if attack_samples > 0:
            envelope[:attack_samples] = np.linspace(0, 1, attack_samples)

        # Decay
        if decay_samples > 0:
            start_idx = attack_samples
            end_idx = attack_samples + decay_samples
            envelope[start_idx:end_idx] = np.linspace(1, sustain, decay_samples)

        # Sustain
        if sustain_samples > 0:
            start_idx = attack_samples + decay_samples
            end_idx = start_idx + sustain_samples
            envelope[start_idx:end_idx] = sustain

        # Release
        if release_samples > 0:
            start_idx = total_samples - release_samples
            envelope[start_idx:] = np.linspace(sustain, 0, release_samples)

        return audio * envelope

    def add_harmonics(self, base_freq: float, harmonics: List[Tuple[float, float]],
                     duration: float, waveform_type: str = 'sine') -> np.ndarray:
        """生成带谐波的复合音调"""
        total_audio = np.zeros(int(self.sample_rate * duration))

        for harmonic_ratio, amplitude in harmonics:
            freq = base_freq * harmonic_ratio
            wave = self.generate_waveform(freq, duration, waveform_type)
            total_audio += wave * amplitude

        return total_audio

    def add_micro_variations(self, audio: np.ndarray, variation_amount: float = 0.02) -> np.ndarray:
        """添加微小的随机变化，让音效更自然"""
        noise = np.random.normal(0, variation_amount, len(audio))
        return audio + noise

    def generate_sound(self, action_name: str) -> str:
        """生成指定动作的优美音效，返回base64编码的data URL"""
        if action_name not in self.sound_configs:
            return ""

        config = self.sound_configs[action_name]
        base_freq = config['base_freq']
        duration = config['duration']
        sound_type = config['type']
        harmonics = config['harmonics']

        # 根据音效类型选择波形
        waveform_map = {
            'bell': 'sine',
            'chime': 'triangle',
            'marimba': 'sine',
            'organ': 'square',
            'flute': 'sine',
            'chord': 'triangle',
            'percussion': 'sawtooth'
        }
        waveform_type = waveform_map.get(sound_type, 'sine')

        # 生成带谐波的复合音效
        audio = self.add_harmonics(base_freq, harmonics, duration, waveform_type)

        # 应用ADSR包络
        audio = self.apply_adsr_envelope(
            audio,
            config['attack'], config['decay'],
            config['sustain'], config['release'],
            self.sample_rate
        )

        # 添加微小随机变化
        audio = self.add_micro_variations(audio, 0.01)

        # 归一化音量
        if np.max(np.abs(audio)) > 0:
            audio = audio / np.max(np.abs(audio)) * 0.7  # 稍微降低音量避免过响

        # 转换为16位整数
        audio_int16 = (audio * 32767).astype(np.int16)

        # 创建WAV文件缓冲区
        wav_buffer = io.BytesIO()
        wav.write(wav_buffer, self.sample_rate, audio_int16)
        wav_buffer.seek(0)

        # 转换为base64 data URL
        wav_data = base64.b64encode(wav_buffer.read()).decode('utf-8')
        data_url = f"data:audio/wav;base64,{wav_data}"

        return data_url

    def get_all_sound_urls(self) -> Dict[str, str]:
        """预生成所有音效的data URLs"""
        sound_urls = {}
        for action_name in self.sound_configs.keys():
            sound_urls[action_name] = self.generate_sound(action_name)
        return sound_urls


# 全局音频生成器实例
audio_generator = AudioGenerator()


def generate_action_sound(action_name: str) -> str:
    """便捷函数：生成指定动作的音效data URL"""
    return audio_generator.generate_sound(action_name)


# 测试代码
if __name__ == "__main__":
    print("Testing Enhanced AudioGenerator...")

    # 测试生成各种音效
    test_actions = [
        'ASHP开启', 'ASHP关闭', 'ASHP制冷模式',
        'ERV风速上升', 'DEH开启', 'ASHP设定温度上升'
    ]

    for action in test_actions:
        url = generate_action_sound(action)
        if url:
            print(f"✓ {action}: 生成成功 (length: {len(url)} chars)")
        else:
            print(f"✗ {action}: 生成失败")

    print("\nEnhanced AudioGenerator test completed!")
    print("音效特点:")
    print("- Bell: 铃声-like，带有丰富谐波")
    print("- Chime: 风铃-like，三角波音色")
    print("- Marimba: 马林巴琴-like")
    print("- Organ: 管风琴-like，方波音色")
    print("- Flute: 长笛-like")
    print("- Percussion: 打击乐-like，锯齿波")
    print("- Chord: 和弦音效")
