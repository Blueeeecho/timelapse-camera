#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
延时摄影拍摄程序
功能：调用电脑摄像头进行延时摄影拍摄
作者：Assistant
日期：2025-01-20
"""

import cv2
import os
import time
import json
import argparse
import threading
from datetime import datetime, timedelta
from pathlib import Path
import signal
import sys

class TimelapseCamera:
    def __init__(self, config_file=None):
        """
        初始化延时摄影相机
        
        Args:
            config_file (str): 配置文件路径
        """
        self.camera = None
        self.is_recording = False
        self.frame_count = 0
        self.start_time = None
        self.config = self.load_default_config()
        
        if config_file and os.path.exists(config_file):
            self.load_config(config_file)
        
        # 设置信号处理器，用于优雅退出
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def load_default_config(self):
        """
        加载默认配置
        
        Returns:
            dict: 默认配置字典
        """
        return {
            "camera_index": 0,  # 摄像头索引
            "interval_seconds": 5,  # 拍摄间隔（秒）
            "duration_minutes": 60,  # 拍摄时长（分钟）
            "resolution": {
                "width": 1920,
                "height": 1080
            },
            "output_dir": "./timelapse_output",  # 输出目录
            "image_format": "jpg",  # 图片格式
            "image_quality": 95,  # 图片质量（1-100）
            "filename_prefix": "timelapse",  # 文件名前缀
            "auto_exposure": True,  # 自动曝光
            "brightness": 0,  # 亮度调整（-100到100）
            "contrast": 0,  # 对比度调整（-100到100）
            "saturation": 0,  # 饱和度调整（-100到100）
            "create_video": True,  # 是否创建视频
            "video_fps": 30,  # 视频帧率
            "video_format": "mp4",  # 视频格式
            "cleanup_images": False,  # 是否清理原始图片
            "preview_window": True,  # 是否显示预览窗口
            "log_level": "INFO"  # 日志级别
        }
    
    def load_config(self, config_file):
        """
        从文件加载配置
        
        Args:
            config_file (str): 配置文件路径
        """
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
                self.config.update(user_config)
            print(f"配置已从 {config_file} 加载")
        except Exception as e:
            print(f"加载配置文件失败: {e}")
    
    def save_config(self, config_file):
        """
        保存配置到文件
        
        Args:
            config_file (str): 配置文件路径
        """
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            print(f"配置已保存到 {config_file}")
        except Exception as e:
            print(f"保存配置文件失败: {e}")
    
    def initialize_camera(self):
        """
        初始化摄像头
        
        Returns:
            bool: 初始化是否成功
        """
        try:
            self.camera = cv2.VideoCapture(self.config["camera_index"])
            
            if not self.camera.isOpened():
                print(f"无法打开摄像头 {self.config['camera_index']}")
                return False
            
            # 设置分辨率
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.config["resolution"]["width"])
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config["resolution"]["height"])
            
            # 设置其他参数
            if not self.config["auto_exposure"]:
                self.camera.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
            
            if self.config["brightness"] != 0:
                self.camera.set(cv2.CAP_PROP_BRIGHTNESS, self.config["brightness"] / 100.0)
            
            if self.config["contrast"] != 0:
                self.camera.set(cv2.CAP_PROP_CONTRAST, self.config["contrast"] / 100.0)
            
            if self.config["saturation"] != 0:
                self.camera.set(cv2.CAP_PROP_SATURATION, self.config["saturation"] / 100.0)
            
            print(f"摄像头初始化成功，分辨率: {int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))}")
            return True
            
        except Exception as e:
            print(f"摄像头初始化失败: {e}")
            return False
    
    def create_output_directory(self):
        """
        创建输出目录
        
        Returns:
            str: 输出目录路径
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.join(self.config["output_dir"], f"{self.config['filename_prefix']}_{timestamp}")
        
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        print(f"输出目录已创建: {output_dir}")
        return output_dir
    
    def capture_frame(self, output_dir, frame_number):
        """
        捕获单帧图像
        
        Args:
            output_dir (str): 输出目录
            frame_number (int): 帧编号
        
        Returns:
            bool: 捕获是否成功
        """
        try:
            ret, frame = self.camera.read()
            if not ret:
                print("无法读取摄像头画面")
                return False
            
            # 生成文件名
            filename = f"{self.config['filename_prefix']}_{frame_number:06d}.{self.config['image_format']}"
            filepath = os.path.join(output_dir, filename)
            
            # 设置图片质量参数
            if self.config["image_format"].lower() == "jpg":
                encode_params = [cv2.IMWRITE_JPEG_QUALITY, self.config["image_quality"]]
            elif self.config["image_format"].lower() == "png":
                encode_params = [cv2.IMWRITE_PNG_COMPRESSION, 9 - (self.config["image_quality"] // 10)]
            else:
                encode_params = []
            
            # 保存图片
            success = cv2.imwrite(filepath, frame, encode_params)
            
            if success:
                current_time = datetime.now().strftime("%H:%M:%S")
                elapsed = datetime.now() - self.start_time
                print(f"[{current_time}] 帧 {frame_number:06d} 已保存 | 已运行: {str(elapsed).split('.')[0]}")
                
                # 显示预览窗口
                if self.config["preview_window"]:
                    # 缩放图片以适应预览窗口
                    preview_frame = cv2.resize(frame, (640, 480))
                    cv2.putText(preview_frame, f"Frame: {frame_number:06d}", (10, 30), 
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                    cv2.putText(preview_frame, f"Time: {current_time}", (10, 70), 
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                    cv2.imshow("Timelapse Preview", preview_frame)
                    
                    # 检查是否按下ESC键退出
                    key = cv2.waitKey(1) & 0xFF
                    if key == 27:  # ESC键
                        print("检测到ESC键，停止拍摄...")
                        self.is_recording = False
                
                return True
            else:
                print(f"保存图片失败: {filepath}")
                return False
                
        except Exception as e:
            print(f"捕获帧失败: {e}")
            return False
    
    def create_video(self, output_dir):
        """
        从图片序列创建视频
        
        Args:
            output_dir (str): 图片目录
        """
        try:
            print("正在创建延时视频...")
            
            # 获取所有图片文件
            image_files = sorted([f for f in os.listdir(output_dir) 
                                if f.endswith(f".{self.config['image_format']}")])
            
            if not image_files:
                print("没有找到图片文件")
                return
            
            # 读取第一张图片获取尺寸
            first_image = cv2.imread(os.path.join(output_dir, image_files[0]))
            height, width, _ = first_image.shape
            
            # 设置视频编码器
            if self.config["video_format"].lower() == "mp4":
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                video_filename = f"{self.config['filename_prefix']}_timelapse.mp4"
            elif self.config["video_format"].lower() == "avi":
                fourcc = cv2.VideoWriter_fourcc(*'XVID')
                video_filename = f"{self.config['filename_prefix']}_timelapse.avi"
            else:
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                video_filename = f"{self.config['filename_prefix']}_timelapse.mp4"
            
            video_path = os.path.join(output_dir, video_filename)
            video_writer = cv2.VideoWriter(video_path, fourcc, self.config["video_fps"], (width, height))
            
            # 写入视频帧
            for i, image_file in enumerate(image_files):
                image_path = os.path.join(output_dir, image_file)
                frame = cv2.imread(image_path)
                video_writer.write(frame)
                
                # 显示进度
                progress = (i + 1) / len(image_files) * 100
                print(f"\r视频创建进度: {progress:.1f}%", end="")
            
            video_writer.release()
            print(f"\n延时视频已创建: {video_path}")
            
            # 清理原始图片（如果配置要求）
            if self.config["cleanup_images"]:
                print("正在清理原始图片...")
                for image_file in image_files:
                    os.remove(os.path.join(output_dir, image_file))
                print("原始图片已清理")
                
        except Exception as e:
            print(f"创建视频失败: {e}")
    
    def start_recording(self):
        """
        开始延时拍摄
        """
        if not self.initialize_camera():
            return False
        
        output_dir = self.create_output_directory()
        
        # 保存当前配置到输出目录
        config_path = os.path.join(output_dir, "config.json")
        self.save_config(config_path)
        
        self.is_recording = True
        self.frame_count = 0
        self.start_time = datetime.now()
        
        # 计算总拍摄时间和预计帧数
        total_seconds = self.config["duration_minutes"] * 60
        estimated_frames = total_seconds // self.config["interval_seconds"]
        
        print(f"开始延时拍摄...")
        print(f"拍摄间隔: {self.config['interval_seconds']}秒")
        print(f"拍摄时长: {self.config['duration_minutes']}分钟")
        print(f"预计帧数: {estimated_frames}")
        print(f"输出目录: {output_dir}")
        print("按ESC键或Ctrl+C停止拍摄\n")
        
        try:
            end_time = self.start_time + timedelta(minutes=self.config["duration_minutes"])
            
            while self.is_recording and datetime.now() < end_time:
                # 捕获帧
                if self.capture_frame(output_dir, self.frame_count):
                    self.frame_count += 1
                
                # 等待下一次拍摄
                time.sleep(self.config["interval_seconds"])
            
            print(f"\n拍摄完成！总共捕获 {self.frame_count} 帧")
            
            # 创建视频
            if self.config["create_video"] and self.frame_count > 0:
                self.create_video(output_dir)
            
            return True
            
        except KeyboardInterrupt:
            print("\n用户中断拍摄")
            return False
        
        finally:
            self.cleanup()
    
    def cleanup(self):
        """
        清理资源
        """
        self.is_recording = False
        
        if self.camera:
            self.camera.release()
        
        if self.config["preview_window"]:
            cv2.destroyAllWindows()
        
        print("资源已清理")
    
    def signal_handler(self, signum, frame):
        """
        信号处理器，用于优雅退出
        
        Args:
            signum: 信号编号
            frame: 当前栈帧
        """
        print(f"\n接收到信号 {signum}，正在停止拍摄...")
        self.is_recording = False
    
    def interactive_config(self):
        """
        交互式配置
        """
        print("=== 延时摄影配置 ===")
        
        # 摄像头索引
        camera_index = input(f"摄像头索引 (当前: {self.config['camera_index']}): ").strip()
        if camera_index:
            self.config["camera_index"] = int(camera_index)
        
        # 拍摄间隔
        interval = input(f"拍摄间隔(秒) (当前: {self.config['interval_seconds']}): ").strip()
        if interval:
            self.config["interval_seconds"] = float(interval)
        
        # 拍摄时长
        duration = input(f"拍摄时长(分钟) (当前: {self.config['duration_minutes']}): ").strip()
        if duration:
            self.config["duration_minutes"] = float(duration)
        
        # 分辨率
        width = input(f"图片宽度 (当前: {self.config['resolution']['width']}): ").strip()
        if width:
            self.config["resolution"]["width"] = int(width)
        
        height = input(f"图片高度 (当前: {self.config['resolution']['height']}): ").strip()
        if height:
            self.config["resolution"]["height"] = int(height)
        
        # 输出目录
        output_dir = input(f"输出目录 (当前: {self.config['output_dir']}): ").strip()
        if output_dir:
            self.config["output_dir"] = output_dir
        
        # 图片格式
        image_format = input(f"图片格式 (jpg/png) (当前: {self.config['image_format']}): ").strip()
        if image_format:
            self.config["image_format"] = image_format
        
        # 图片质量
        quality = input(f"图片质量 (1-100) (当前: {self.config['image_quality']}): ").strip()
        if quality:
            self.config["image_quality"] = int(quality)
        
        # 是否创建视频
        create_video = input(f"创建视频 (y/n) (当前: {'y' if self.config['create_video'] else 'n'}): ").strip()
        if create_video:
            self.config["create_video"] = create_video.lower() == 'y'
        
        # 视频帧率
        if self.config["create_video"]:
            fps = input(f"视频帧率 (当前: {self.config['video_fps']}): ").strip()
            if fps:
                self.config["video_fps"] = int(fps)
        
        print("\n配置完成！")


def main():
    """
    主函数
    """
    parser = argparse.ArgumentParser(description="延时摄影拍摄程序")
    parser.add_argument("-c", "--config", help="配置文件路径")
    parser.add_argument("-i", "--interactive", action="store_true", help="交互式配置")
    parser.add_argument("--interval", type=float, help="拍摄间隔(秒)")
    parser.add_argument("--duration", type=float, help="拍摄时长(分钟)")
    parser.add_argument("--width", type=int, help="图片宽度")
    parser.add_argument("--height", type=int, help="图片高度")
    parser.add_argument("--output", help="输出目录")
    parser.add_argument("--format", help="图片格式 (jpg/png)")
    parser.add_argument("--quality", type=int, help="图片质量 (1-100)")
    parser.add_argument("--no-video", action="store_true", help="不创建视频")
    parser.add_argument("--no-preview", action="store_true", help="不显示预览窗口")
    
    args = parser.parse_args()
    
    # 创建延时摄影对象
    timelapse = TimelapseCamera(args.config)
    
    # 应用命令行参数
    if args.interval:
        timelapse.config["interval_seconds"] = args.interval
    if args.duration:
        timelapse.config["duration_minutes"] = args.duration
    if args.width:
        timelapse.config["resolution"]["width"] = args.width
    if args.height:
        timelapse.config["resolution"]["height"] = args.height
    if args.output:
        timelapse.config["output_dir"] = args.output
    if args.format:
        timelapse.config["image_format"] = args.format
    if args.quality:
        timelapse.config["image_quality"] = args.quality
    if args.no_video:
        timelapse.config["create_video"] = False
    if args.no_preview:
        timelapse.config["preview_window"] = False
    
    # 交互式配置
    if args.interactive:
        timelapse.interactive_config()
    
    # 开始拍摄
    try:
        success = timelapse.start_recording()
        if success:
            print("延时拍摄成功完成！")
        else:
            print("延时拍摄失败")
            sys.exit(1)
    except Exception as e:
        print(f"程序运行出错: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()