#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
延时摄影程序测试脚本
用于快速测试延时摄影功能
"""

import cv2
import os
import time
from datetime import datetime
from pathlib import Path

def test_camera_basic():
    """基本摄像头测试"""
    print("正在测试摄像头...")
    
    # 尝试打开摄像头
    camera = cv2.VideoCapture(0)
    
    if not camera.isOpened():
        print("❌ 无法打开摄像头 0")
        return False
    
    # 读取一帧
    ret, frame = camera.read()
    if ret:
        height, width = frame.shape[:2]
        print(f"✅ 摄像头测试成功")
        print(f"   分辨率: {width}x{height}")
        
        # 保存测试图片
        test_dir = "./test_output"
        Path(test_dir).mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        test_image = os.path.join(test_dir, f"test_frame_{timestamp}.jpg")
        
        cv2.imwrite(test_image, frame)
        print(f"   测试图片已保存: {test_image}")
        
        camera.release()
        return True
    else:
        print("❌ 无法读取摄像头画面")
        camera.release()
        return False

def test_short_timelapse():
    """短时间延时摄影测试"""
    print("\n正在进行短时间延时摄影测试...")
    print("参数: 间隔2秒，总共拍摄5张照片")
    
    camera = cv2.VideoCapture(0)
    
    if not camera.isOpened():
        print("❌ 无法打开摄像头")
        return False
    
    # 创建输出目录
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = f"./test_output/timelapse_test_{timestamp}"
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    print(f"输出目录: {output_dir}")
    
    # 拍摄参数
    interval = 2  # 秒
    total_frames = 5
    
    print("开始拍摄...")
    
    for i in range(total_frames):
        ret, frame = camera.read()
        if ret:
            filename = f"frame_{i+1:03d}.jpg"
            filepath = os.path.join(output_dir, filename)
            
            success = cv2.imwrite(filepath, frame)
            if success:
                current_time = datetime.now().strftime("%H:%M:%S")
                print(f"  [{current_time}] 第 {i+1}/{total_frames} 帧已保存")
            else:
                print(f"❌ 保存第 {i+1} 帧失败")
        else:
            print(f"❌ 读取第 {i+1} 帧失败")
        
        # 等待下一次拍摄（最后一帧不需要等待）
        if i < total_frames - 1:
            print(f"  等待 {interval} 秒...")
            time.sleep(interval)
    
    camera.release()
    print(f"✅ 测试完成！共拍摄 {total_frames} 帧")
    print(f"   文件保存在: {output_dir}")
    
    return True

def main():
    """主函数"""
    print("=" * 50)
    print("延时摄影程序测试")
    print("=" * 50)
    
    # 基本摄像头测试
    if not test_camera_basic():
        print("\n❌ 基本摄像头测试失败，请检查摄像头连接")
        return
    
    # 询问是否进行延时摄影测试
    print("\n是否进行短时间延时摄影测试？(y/n): ", end="")
    choice = input().lower().strip()
    
    if choice in ['y', 'yes', '是', '好']:
        test_short_timelapse()
    else:
        print("跳过延时摄影测试")
    
    print("\n测试完成！")
    print("\n提示:")
    print("- 如果基本测试成功，说明摄像头工作正常")
    print("- 可以使用 timelapse_gui.py 进行图形界面操作")
    print("- 可以使用 timelapse_camera.py 进行命令行操作")

if __name__ == "__main__":
    main()