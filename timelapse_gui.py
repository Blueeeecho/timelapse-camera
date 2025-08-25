#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
延时摄影GUI程序
功能：提供图形界面的延时摄影拍摄程序
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import cv2
import os
import json
import threading
from datetime import datetime, timedelta
from pathlib import Path
from PIL import Image, ImageTk, ImageEnhance
import numpy as np
import time

class TimelapseGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("延时摄影拍摄程序")
        self.root.geometry("1000x800")
        
        # 初始化变量
        self.camera = None
        self.is_recording = False
        self.is_previewing = False
        self.frame_count = 0
        self.start_time = None
        self.recording_thread = None
        self.preview_thread = None
        self.preview_label = None
        self.countdown_label = None
        self.timer_thread = None
        self.recording_preview_thread = None
        self.last_video_path = None
        self.current_recording_dir = None  # 当前录制项目的目录
        
        # 配置变量
        self.config = {
            "camera_index": tk.IntVar(value=0),
            "interval_seconds": tk.DoubleVar(value=5.0),
            "duration_minutes": tk.DoubleVar(value=60.0),
            "width": tk.IntVar(value=1920),
            "height": tk.IntVar(value=1080),
            "output_dir": tk.StringVar(value="./timelapse_output"),
            "image_format": tk.StringVar(value="jpg"),
            "image_quality": tk.IntVar(value=95),
            "filename_prefix": tk.StringVar(value="timelapse"),
            "brightness": tk.IntVar(value=0),
            "contrast": tk.IntVar(value=0),
            "saturation": tk.IntVar(value=0),
            "create_video": tk.BooleanVar(value=True),
            "video_fps": tk.IntVar(value=30),
            "video_format": tk.StringVar(value="mp4"),
            "cleanup_images": tk.BooleanVar(value=True),
            "auto_exposure": tk.BooleanVar(value=True),
            "recording_time_limit": tk.StringVar(value="无限制"),  # 新增录制时间限制选项
            "use_time_limit": tk.BooleanVar(value=False)  # 是否使用时间限制
        }
        
        # 视频播放相关状态（需要在setup_ui之前初始化）
        self.is_playing_video = False
        self.video_cap = None
        self.video_thread = None
        self.video_paused = False
        self.video_frame_count = 0
        self.video_fps = 30
        self.current_frame = 0
        self.video_progress_var = tk.DoubleVar()
        self.video_progress_bar = None
        
        # 视频制作状态
        self.is_creating_video = False
        self.video_creation_progress = 0
        
        self.setup_ui()
        
        # 默认启动预览
        self.root.after(1000, self.start_preview)  # 延迟1秒启动预览
        
        # 启动系统信息更新
        self.update_system_info()
        
    def setup_ui(self):
        """设置用户界面"""
        # 设置主窗口样式
        self.root.configure(bg='#f0f0f0')
        
        # 创建主容器，使用垂直布局
        main_container = ttk.Frame(self.root)
        main_container.pack(fill="both", expand=True)
        
        # 创建顶部固定区域（不可滚动）
        fixed_top_frame = ttk.Frame(main_container, padding="15")
        fixed_top_frame.pack(side="top", fill="x")
        
        # 标题 - 使用更现代的字体和颜色
        title_label = ttk.Label(fixed_top_frame, text="🎥 延时摄影拍摄程序", font=("SF Pro Display", 18, "bold"))
        title_label.pack(pady=(0, 15))
        
        # 摄像头预览框架（固定在顶部）- 使用更现代的样式
        preview_frame = ttk.LabelFrame(fixed_top_frame, text="📹 摄像头预览", padding="15")
        preview_frame.pack(fill="x", pady=(0, 10))
        
        # 预览标签 - 动态调整尺寸，根据摄像头比例和页面宽度自适应
        self.preview_label = tk.Label(preview_frame, text="🔄 正在启动摄像头预览...", 
                                     background="#2c3e50", foreground="white", 
                                     font=("SF Pro Display", 10), cursor="hand2")
        self.preview_label.pack(padx=8, pady=8)
        
        # 绑定预览标签点击事件
        self.preview_label.bind("<Button-1>", self._on_preview_click)
        
        # 视频进度条（初始隐藏）
        self.video_progress_bar = ttk.Progressbar(preview_frame, variable=self.video_progress_var, 
                                                 maximum=100, mode='determinate')
        # 绑定进度条点击和拖动事件
        self.video_progress_bar.bind('<Button-1>', self._on_progress_bar_click)
        self.video_progress_bar.bind('<B1-Motion>', self._on_progress_bar_drag)
        # 进度条初始不显示，只在播放视频时显示
        
        # 视频控制区域（时长信息和播放控制按钮）
        self.video_control_frame = tk.Frame(preview_frame, background="#ecf0f1")
        
        # 视频时长信息标签
        self.video_time_label = tk.Label(self.video_control_frame, text="00:00 / 00:00", 
                                         font=('SF Pro Display', 10), foreground="#2c3e50", 
                                         background="#ecf0f1", padx=8, pady=2)
        self.video_time_label.pack(side=tk.LEFT)
        
        # 播放/暂停控制按钮（圆形）
        self.play_pause_button = tk.Button(self.video_control_frame, text="⏸️", 
                                          font=('SF Pro Display', 12), width=3, height=1,
                                          relief="flat", background="#3498db", foreground="white",
                                          activebackground="#2980b9", cursor="hand2",
                                          command=self._toggle_video_playback)
        self.play_pause_button.pack(side=tk.LEFT, padx=(10, 0))
        
        # 控制区域初始不显示，只在播放视频时显示
        
        # 存储摄像头原始比例，用于动态调整预览框尺寸
        self.camera_aspect_ratio = 16/9  # 默认16:9，启动后会自动检测实际比例
        
        # 控制按钮已移至可滚动区域
        
        # 控制按钮已移至录制控制面板中
        
        # 创建可滚动的控制区域 - 改进样式（在主容器中）
        scrollable_container = ttk.Frame(main_container)
        scrollable_container.pack(side="bottom", fill="both", expand=True)
        
        canvas = tk.Canvas(scrollable_container, bg='#f8f9fa', highlightthickness=0)
        scrollbar = ttk.Scrollbar(scrollable_container, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # 绑定canvas大小变化事件，确保scrollable_frame宽度与canvas一致
        def _on_canvas_configure(event):
            canvas.itemconfig(canvas.find_all()[0], width=event.width)
        canvas.bind('<Configure>', _on_canvas_configure)
        
        # 绑定鼠标滚轮事件（支持 macOS 和 Windows）
        def _on_mousewheel(event):
            # macOS 使用 event.delta，Windows 使用 event.delta/120
            if event.delta:
                delta = event.delta
            else:
                delta = event.delta
            canvas.yview_scroll(int(-1 * delta), "units")
        
        def _bind_mousewheel(widget):
            """递归绑定鼠标滚轮事件到所有子控件"""
            widget.bind("<MouseWheel>", _on_mousewheel)  # Windows
            widget.bind("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))  # Linux
            widget.bind("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))   # Linux
            for child in widget.winfo_children():
                _bind_mousewheel(child)
        
        # 绑定滚轮事件到画布和主窗口
        canvas.bind("<MouseWheel>", _on_mousewheel)
        canvas.bind("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))
        canvas.bind("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))
        self.root.bind("<MouseWheel>", _on_mousewheel)
        self.root.bind("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))
        self.root.bind("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))
        
        # 绑定到可滚动框架
        _bind_mousewheel(scrollable_frame)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 创建主内容框架 - 改进间距
        main_frame = ttk.Frame(scrollable_frame, padding="15")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        scrollable_frame.columnconfigure(0, weight=1)
        scrollable_frame.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        row = 0
        
        # 录制控制面板 - 移到可滚动区域的第一个位置
        status_frame = ttk.LabelFrame(main_frame, text="📊 录制控制面板", padding="12")
        status_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 15))
        status_frame.columnconfigure(1, weight=1)
        row += 1
        
        # 第一行：录制状态和控制按钮
        control_row = ttk.Frame(status_frame)
        control_row.pack(fill="x", pady=(0, 8))
        
        # 录制状态标签 - 优化颜色主题
        self.countdown_label = tk.Label(control_row, text="⏸️ 未开始录制", 
                                       font=('SF Pro Display', 12, 'bold'), foreground="#2c3e50", 
                                       background="#ecf0f1", relief="solid", bd=1, padx=12, pady=6)
        self.countdown_label.pack(side=tk.LEFT, padx=(0, 15))
        
        # 控制按钮组 - 合并为单个切换按钮
        button_frame = ttk.Frame(control_row)
        button_frame.pack(side=tk.LEFT, padx=(0, 15))
        
        self.record_toggle_button = ttk.Button(button_frame, text="🎬 开始拍摄", command=self.toggle_recording, width=15)
        self.record_toggle_button.pack(side=tk.LEFT, padx=(0, 5))
        
        # 保留停止按钮的引用以兼容现有代码，但不显示
        self.record_button = self.record_toggle_button  # 兼容性引用
        self.stop_button = self.record_toggle_button    # 兼容性引用
        
        self.preview_video_button = ttk.Button(button_frame, text="📹 预览视频", command=self.preview_last_video, state=tk.DISABLED, width=12)
        self.preview_video_button.pack(side=tk.LEFT)
        
        # 录制时长设置
        time_setting_frame = ttk.Frame(control_row)
        time_setting_frame.pack(side=tk.RIGHT)
        
        ttk.Label(time_setting_frame, text="⏱️ 录制时长:", font=("SF Pro Display", 9)).pack(side=tk.LEFT)
        self.time_limit_combo = ttk.Combobox(time_setting_frame, textvariable=self.config["recording_time_limit"], 
                                           values=["无限制", "5分钟", "10分钟", "30分钟", "60分钟"], 
                                           state="readonly", width=8)
        self.time_limit_combo.pack(side=tk.LEFT, padx=(5, 0))
        self.time_limit_combo.bind("<<ComboboxSelected>>", self._on_time_limit_change)
        
        # 第二行：录制进度条和时间信息
        progress_row = ttk.Frame(status_frame)
        progress_row.pack(fill="x", pady=(0, 8))
        
        # 进度条 - 使用深绿色主题
        self.progress_var = tk.DoubleVar()
        style = ttk.Style()
        style.configure("DarkGreen.Horizontal.TProgressbar", background='#1e7e34', troughcolor='#ecf0f1')
        self.progress_bar = ttk.Progressbar(progress_row, variable=self.progress_var, mode='determinate', 
                                          length=300, style="DarkGreen.Horizontal.TProgressbar")
        self.progress_bar.pack(side=tk.LEFT, padx=(0, 15), fill=tk.X, expand=True)
        
        # 时间信息标签 - 优化颜色主题
        self.time_info_label = tk.Label(progress_row, text="等待开始录制", 
                                       font=('SF Pro Display', 10), foreground="#2c3e50", 
                                       background="#d5dbdb", relief="solid", bd=1, padx=8, pady=4)
        self.time_info_label.pack(side=tk.LEFT, padx=(0, 15))
        
        # 第三行：系统信息
        info_row = ttk.Frame(status_frame)
        info_row.pack(fill="x")
        
        self.system_info_label = tk.Label(info_row, text="💾 系统信息加载中...", 
                                         font=('SF Pro Display', 9), foreground="#7f8c8d", 
                                         background="#ecf0f1", relief="solid", bd=1, padx=8, pady=4)
        self.system_info_label.pack(side=tk.LEFT)
        
        # 第一行：基本设置和视频设置
        settings_row1 = ttk.Frame(main_frame)
        settings_row1.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 15))
        settings_row1.columnconfigure(0, weight=1)
        settings_row1.columnconfigure(1, weight=1)
        row += 1
        
        # 基本设置框架 - 左栏
        basic_frame = ttk.LabelFrame(settings_row1, text="⚙️ 基本设置", padding="15")
        basic_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 7))
        basic_frame.columnconfigure(1, weight=1)
        
        # 摄像头索引
        ttk.Label(basic_frame, text="摄像头索引:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.camera_spinbox = ttk.Spinbox(basic_frame, from_=0, to=10, textvariable=self.config["camera_index"], width=8)
        self.camera_spinbox.grid(row=0, column=1, padx=(0, 10), sticky=tk.W)
        
        # 拍摄间隔
        ttk.Label(basic_frame, text="拍摄间隔(秒):").grid(row=1, column=0, sticky=tk.W, padx=(0, 10))
        self.interval_spinbox = ttk.Spinbox(basic_frame, from_=0.1, to=3600, increment=0.1, textvariable=self.config["interval_seconds"], width=8)
        self.interval_spinbox.grid(row=1, column=1, padx=(0, 10), sticky=tk.W)
        
        # 输出目录
        ttk.Label(basic_frame, text="输出目录:").grid(row=2, column=0, sticky=tk.W, padx=(0, 10))
        dir_frame = ttk.Frame(basic_frame)
        dir_frame.grid(row=2, column=1, sticky=(tk.W, tk.E))
        dir_frame.columnconfigure(0, weight=1)
        self.output_dir_entry = ttk.Entry(dir_frame, textvariable=self.config["output_dir"])
        self.output_dir_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        self.browse_button = ttk.Button(dir_frame, text="浏览", command=self.browse_output_dir)
        self.browse_button.grid(row=0, column=1)
        
        # 文件名前缀
        ttk.Label(basic_frame, text="文件名前缀:").grid(row=3, column=0, sticky=tk.W, padx=(0, 10))
        self.filename_entry = ttk.Entry(basic_frame, textvariable=self.config["filename_prefix"], width=20)
        self.filename_entry.grid(row=3, column=1, sticky=tk.W)
        
        # 视频设置框架 - 右栏
        video_frame = ttk.LabelFrame(settings_row1, text="🎬 视频设置", padding="15")
        video_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(7, 0))
        video_frame.columnconfigure(1, weight=1)
        
        # 创建视频
        self.create_video_check = ttk.Checkbutton(video_frame, text="创建延时视频", variable=self.config["create_video"])
        self.create_video_check.grid(row=0, column=0, columnspan=2, sticky=tk.W)
        
        # 视频帧率
        ttk.Label(video_frame, text="视频帧率:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10))
        self.fps_spinbox = ttk.Spinbox(video_frame, from_=1, to=120, textvariable=self.config["video_fps"], width=8)
        self.fps_spinbox.grid(row=1, column=1, padx=(0, 10), sticky=tk.W)
        
        # 视频格式
        ttk.Label(video_frame, text="视频格式:").grid(row=2, column=0, sticky=tk.W, padx=(0, 10))
        self.video_format_combo = ttk.Combobox(video_frame, textvariable=self.config["video_format"], values=["mp4", "avi"], width=10)
        self.video_format_combo.grid(row=2, column=1, sticky=tk.W)
        self.video_format_combo.state(["readonly"])
        
        # 清理图片
        self.cleanup_check = ttk.Checkbutton(video_frame, text="创建视频后删除原始图片", variable=self.config["cleanup_images"])
        self.cleanup_check.grid(row=3, column=0, columnspan=2, sticky=tk.W)
        
        # 第二行：图像设置和摄像头调整
        settings_row2 = ttk.Frame(main_frame)
        settings_row2.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 15))
        settings_row2.columnconfigure(0, weight=1)
        settings_row2.columnconfigure(1, weight=1)
        row += 1
        
        # 图像设置框架 - 左栏
        image_frame = ttk.LabelFrame(settings_row2, text="🖼️ 图像设置", padding="15")
        image_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 7))
        image_frame.columnconfigure(1, weight=1)
        
        # 分辨率
        ttk.Label(image_frame, text="分辨率:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        res_frame = ttk.Frame(image_frame)
        res_frame.grid(row=0, column=1, sticky=(tk.W, tk.E))
        res_frame.columnconfigure(2, weight=1)
        
        # 分辨率预设
        self.preset_combo = ttk.Combobox(res_frame, values=["自定义", "4K (3840x2160)", "1080P (1920x1080)", "720P (1280x720)", "480P (640x480)"], width=15, state="readonly")
        self.preset_combo.grid(row=0, column=0, padx=(0, 10))
        self.preset_combo.set("1080P (1920x1080)")
        self.preset_combo.bind('<<ComboboxSelected>>', lambda e: self._on_resolution_preset_change(self.preset_combo.get()))
        
        # 自定义分辨率输入
        self.custom_res_frame = ttk.Frame(res_frame)
        self.custom_res_frame.grid(row=0, column=1, sticky=tk.W)
        self.width_spinbox = ttk.Spinbox(self.custom_res_frame, from_=320, to=4096, textvariable=self.config["width"], width=8)
        self.width_spinbox.grid(row=0, column=0)
        ttk.Label(self.custom_res_frame, text="x").grid(row=0, column=1, padx=5)
        self.height_spinbox = ttk.Spinbox(self.custom_res_frame, from_=240, to=2160, textvariable=self.config["height"], width=8)
        self.height_spinbox.grid(row=0, column=2)
        
        # 初始隐藏自定义分辨率输入框
        self.custom_res_frame.grid_remove()
        
        # 图片格式
        ttk.Label(image_frame, text="图片格式:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10))
        self.format_combo = ttk.Combobox(image_frame, textvariable=self.config["image_format"], values=["jpg", "png"], width=10)
        self.format_combo.grid(row=1, column=1, sticky=tk.W)
        self.format_combo.state(["readonly"])
        
        # 图片质量
        ttk.Label(image_frame, text="图片质量:").grid(row=2, column=0, sticky=tk.W, padx=(0, 10))
        quality_frame = ttk.Frame(image_frame)
        quality_frame.grid(row=2, column=1, sticky=(tk.W, tk.E))
        quality_frame.columnconfigure(0, weight=1)
        self.quality_scale = ttk.Scale(quality_frame, from_=1, to=100, orient=tk.HORIZONTAL, variable=self.config["image_quality"], command=lambda v: self.config["image_quality"].set(int(float(v))))
        self.quality_scale.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        ttk.Label(quality_frame, textvariable=self.config["image_quality"]).grid(row=0, column=1)
        
        # 摄像头调整框架 - 右栏
        camera_frame = ttk.LabelFrame(settings_row2, text="📷 摄像头调整", padding="15")
        camera_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(7, 0))
        camera_frame.columnconfigure(1, weight=1)
        
        # 自动曝光
        self.auto_exposure_check = ttk.Checkbutton(camera_frame, text="自动曝光", variable=self.config["auto_exposure"])
        self.auto_exposure_check.grid(row=0, column=0, columnspan=2, sticky=tk.W)
        
        # 亮度
        ttk.Label(camera_frame, text="亮度:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10))
        brightness_frame = ttk.Frame(camera_frame)
        brightness_frame.grid(row=1, column=1, sticky=(tk.W, tk.E))
        brightness_frame.columnconfigure(0, weight=1)
        self.brightness_scale = ttk.Scale(brightness_frame, from_=-100, to=100, orient=tk.HORIZONTAL, variable=self.config["brightness"], command=lambda v: self._update_camera_brightness(int(float(v))))
        self.brightness_scale.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        self.brightness_scale.bind('<Button-1>', lambda e: self._on_camera_scale_click(e, self.config["brightness"], -100, 100))
        ttk.Label(brightness_frame, textvariable=self.config["brightness"]).grid(row=0, column=1)
        
        # 对比度
        ttk.Label(camera_frame, text="对比度:").grid(row=2, column=0, sticky=tk.W, padx=(0, 10))
        contrast_frame = ttk.Frame(camera_frame)
        contrast_frame.grid(row=2, column=1, sticky=(tk.W, tk.E))
        contrast_frame.columnconfigure(0, weight=1)
        self.contrast_scale = ttk.Scale(contrast_frame, from_=-100, to=100, orient=tk.HORIZONTAL, variable=self.config["contrast"], command=lambda v: self._update_camera_contrast(int(float(v))))
        self.contrast_scale.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        self.contrast_scale.bind('<Button-1>', lambda e: self._on_camera_scale_click(e, self.config["contrast"], -100, 100))
        ttk.Label(contrast_frame, textvariable=self.config["contrast"]).grid(row=0, column=1)
        
        # 饱和度
        ttk.Label(camera_frame, text="饱和度:").grid(row=3, column=0, sticky=tk.W, padx=(0, 10))
        saturation_frame = ttk.Frame(camera_frame)
        saturation_frame.grid(row=3, column=1, sticky=(tk.W, tk.E))
        saturation_frame.columnconfigure(0, weight=1)
        self.saturation_scale = ttk.Scale(saturation_frame, from_=-100, to=100, orient=tk.HORIZONTAL, variable=self.config["saturation"], command=lambda v: self._update_camera_saturation(int(float(v))))
        self.saturation_scale.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        self.saturation_scale.bind('<Button-1>', lambda e: self._on_camera_scale_click(e, self.config["saturation"], -100, 100))
        ttk.Label(saturation_frame, textvariable=self.config["saturation"]).grid(row=0, column=1)
        
        # 移除配置按钮框架
        
        # 状态框架 - 添加图标
        status_frame = ttk.LabelFrame(main_frame, text="📋 状态信息", padding="15")
        status_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(15, 0))
        status_frame.columnconfigure(0, weight=1)
        row += 1
        
        # 状态文本
        self.status_text = tk.Text(status_frame, height=8, width=80)
        self.status_text.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        # 滚动条
        scrollbar = ttk.Scrollbar(status_frame, orient="vertical", command=self.status_text.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.status_text.configure(yscrollcommand=scrollbar.set)
        
        self.log_message("程序已启动，请配置参数后开始拍摄")
        
        # 绑定窗口大小变化事件，动态调整预览框尺寸
        self.root.bind('<Configure>', self._on_window_configure)
        
        # 初始化预览框尺寸
        self.root.after(100, self._update_preview_size)  # 延迟100ms确保窗口完全初始化
    
    def _on_window_configure(self, event):
        """窗口大小变化时动态调整预览框尺寸"""
        # 只处理主窗口的配置变化事件
        if event.widget == self.root:
            self._update_preview_size()
    
    def _update_preview_size(self):
        """根据窗口尺寸和摄像头比例动态调整预览框尺寸，严格保持比例"""
        try:
            # 获取窗口当前尺寸
            window_width = self.root.winfo_width()
            window_height = self.root.winfo_height()
            if window_width <= 1 or window_height <= 1:  # 窗口还未完全初始化
                return
            
            # 计算可用空间（留出边距和其他UI组件空间）
            available_width = window_width - 100  # 左右边距
            available_height = max(200, window_height - 400)  # 上下预留空间给其他组件
            
            # 根据摄像头比例和可用空间计算最佳尺寸
            # 方案1：基于宽度计算
            width_based_width = max(400, min(800, available_width))
            width_based_height = int(width_based_width / self.camera_aspect_ratio)
            
            # 方案2：基于高度计算
            height_based_height = min(available_height, 450)  # 最大高度450px
            height_based_width = int(height_based_height * self.camera_aspect_ratio)
            
            # 选择不超出边界的方案
            if width_based_height <= available_height:
                preview_width = width_based_width
                preview_height = width_based_height
            else:
                preview_width = height_based_width
                preview_height = height_based_height
            
            # 确保最小尺寸
            preview_width = max(400, preview_width)
            preview_height = max(225, preview_height)  # 400*9/16=225
            
            # 更新预览标签尺寸
            self.preview_label.configure(width=preview_width, height=preview_height)
            
        except Exception as e:
            pass  # 忽略调整过程中的错误
    
    def log_message(self, message):
        """记录日志消息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}\n"
        self.status_text.insert(tk.END, formatted_message)
        self.status_text.see(tk.END)
        self.root.update_idletasks()
    
    def _on_camera_scale_click(self, event, var, min_val, max_val):
        """处理摄像头调整滑块点击事件，直接跳转到点击位置"""
        # 获取Scale控件
        scale_widget = event.widget
        
        # 计算点击位置对应的数值
        # 获取Scale的几何信息
        scale_width = scale_widget.winfo_width()
        click_x = event.x
        
        # 计算相对位置（0-1之间）
        if scale_width > 0:
            relative_pos = max(0, min(1, click_x / scale_width))
            # 计算对应的数值并取整
            value = int(min_val + (max_val - min_val) * relative_pos)
            # 设置数值
            var.set(value)
            self.log_message(f"摄像头参数已设置为: {value}")

    def _disable_settings(self):
        """禁用所有设置控件"""
        # 基本设置
        self.camera_spinbox.config(state="disabled")
        self.interval_spinbox.config(state="disabled")
        self.output_dir_entry.config(state="disabled")
        self.browse_button.config(state="disabled")
        self.filename_entry.config(state="disabled")
        
        # 录制时长设置
        self.time_limit_combo.config(state="disabled")
        
        # 视频设置
        self.create_video_check.config(state="disabled")
        self.fps_spinbox.config(state="disabled")
        self.video_format_combo.config(state="disabled")
        self.cleanup_check.config(state="disabled")
        
        # 图像设置
        self.preset_combo.config(state="disabled")
        self.width_spinbox.config(state="disabled")
        self.height_spinbox.config(state="disabled")
        self.format_combo.config(state="disabled")
        self.quality_scale.config(state="disabled")
        
        # 摄像头调整
        self.auto_exposure_check.config(state="disabled")
        self.brightness_scale.config(state="disabled")
        self.contrast_scale.config(state="disabled")
        self.saturation_scale.config(state="disabled")
    
    def _enable_settings(self):
        """启用所有设置控件"""
        # 基本设置
        self.camera_spinbox.config(state="normal")
        self.interval_spinbox.config(state="normal")
        self.output_dir_entry.config(state="normal")
        self.browse_button.config(state="normal")
        self.filename_entry.config(state="normal")
        
        # 录制时长设置
        self.time_limit_combo.config(state="readonly")
        
        # 视频设置
        self.create_video_check.config(state="normal")
        self.fps_spinbox.config(state="normal")
        self.video_format_combo.config(state="readonly")
        self.cleanup_check.config(state="normal")
        
        # 图像设置
        self.preset_combo.config(state="readonly")
        self.width_spinbox.config(state="normal")
        self.height_spinbox.config(state="normal")
        self.format_combo.config(state="readonly")
        self.quality_scale.config(state="normal")
        
        # 摄像头调整
        self.auto_exposure_check.config(state="normal")
        self.brightness_scale.config(state="normal")
        self.contrast_scale.config(state="normal")
        self.saturation_scale.config(state="normal")
    
    def _on_preview_click(self, event):
        """处理预览框点击事件"""
        if self.is_playing_video:
            # 如果正在播放视频，切换暂停/播放状态
            self.video_paused = not self.video_paused
            if self.video_paused:
                self.log_message("视频已暂停")
            else:
                self.log_message("视频继续播放")
        elif hasattr(self, 'last_video_path') and self.last_video_path and os.path.exists(self.last_video_path):
            # 如果有可播放的视频，开始播放
            self._start_video_playback()
        else:
            # 没有视频可播放
            messagebox.showinfo("提示", "没有可播放的视频文件")
    
    def _on_resolution_preset_change(self, preset):
        """处理分辨率预设变化"""
        resolution_map = {
            "4K (3840x2160)": (3840, 2160),
            "1080P (1920x1080)": (1920, 1080),
            "720P (1280x720)": (1280, 720),
            "480P (640x480)": (640, 480)
        }
        
        if preset == "自定义":
            # 显示自定义分辨率输入框
            self.custom_res_frame.grid()
            self.log_message("已切换到自定义分辨率模式")
        elif preset in resolution_map:
            # 隐藏自定义分辨率输入框并设置预设值
            self.custom_res_frame.grid_remove()
            width, height = resolution_map[preset]
            self.config["width"].set(width)
            self.config["height"].set(height)
            self.log_message(f"分辨率已设置为 {preset}")
     
    def _on_time_limit_change(self, event=None):
        """录制时间限制选择变化时的回调"""
        selected = self.config["recording_time_limit"].get()
        if selected == "无限制":
            self.config["use_time_limit"].set(False)
        else:
            self.config["use_time_limit"].set(True)
        self.log_message(f"录制时长设置为: {selected}")
    
    def toggle_recording(self):
        """切换录制状态"""
        if not self.is_recording:
            self.start_recording()
        else:
            self.stop_recording()
    
    def browse_output_dir(self):
        """浏览输出目录"""
        directory = filedialog.askdirectory(initialdir=self.config["output_dir"].get())
        if directory:
            self.config["output_dir"].set(directory)
    
    def toggle_preview(self):
        """切换预览状态"""
        if self.is_previewing:
            self.stop_preview()
        else:
            self.start_preview()
    
    def start_preview(self):
        """开始预览"""
        if self.is_previewing or self.is_recording:
            return
        
        try:
            if self.camera:
                self.camera.release()
            
            self.camera = cv2.VideoCapture(self.config["camera_index"].get())
            
            if not self.camera.isOpened():
                messagebox.showerror("错误", f"无法打开摄像头 {self.config['camera_index'].get()}")
                return
            
            # 设置分辨率
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.config["width"].get())
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config["height"].get())
            
            # 应用摄像头设置
            if not self.config["auto_exposure"].get():
                self.camera.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
            
            # 设置摄像头参数（移除值为0时不设置的限制）
            self.camera.set(cv2.CAP_PROP_BRIGHTNESS, self.config["brightness"].get() / 100.0)
            self.camera.set(cv2.CAP_PROP_CONTRAST, self.config["contrast"].get() / 100.0)
            self.camera.set(cv2.CAP_PROP_SATURATION, self.config["saturation"].get() / 100.0)
            
            self.is_previewing = True
            
            # 启动预览线程
            self.preview_thread = threading.Thread(target=self._preview_worker)
            self.preview_thread.daemon = True
            self.preview_thread.start()
            
            actual_width = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.log_message(f"预览已启动，分辨率: {actual_width}x{actual_height}")
            
        except Exception as e:
            messagebox.showerror("错误", f"启动预览失败: {e}")
            self.log_message(f"启动预览失败: {e}")
            self.is_previewing = False
    
    def stop_preview(self):
        """停止预览"""
        self.is_previewing = False
        
        if self.camera:
            self.camera.release()
            self.camera = None
        
        # 清空预览
        self.preview_label.configure(image="", text="点击'开始预览'查看摄像头画面")
        self.preview_label.image = None
        
        self.log_message("预览已停止")
    
    def _preview_worker(self):
        """预览工作线程"""
        camera_ratio_detected = False
        
        while self.is_previewing and self.camera and self.camera.isOpened():
            try:
                ret, frame = self.camera.read()
                if ret:
                    # 转换为PIL图像
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    pil_image = Image.fromarray(frame_rgb)
                    
                    # 应用软件层面的图像调整（亮度、对比度、饱和度）
                    pil_image = self._apply_image_adjustments(pil_image)
                    
                    img_width, img_height = pil_image.size
                    
                    # 检测并更新摄像头实际比例（只在第一次检测）
                    if not camera_ratio_detected:
                        self.camera_aspect_ratio = img_width / img_height
                        camera_ratio_detected = True
                        # 触发预览框尺寸更新
                        self.root.after(0, self._update_preview_size)
                    
                    # 获取预览标签的当前尺寸
                    display_width = self.preview_label.winfo_width()
                    display_height = self.preview_label.winfo_height()
                    
                    # 如果标签尺寸还未初始化，使用默认尺寸
                    if display_width <= 1 or display_height <= 1:
                        display_width = 800
                        display_height = int(display_width / self.camera_aspect_ratio)
                    
                    # 计算缩放比例，保持宽高比并完整显示画面（可能有黑边）
                    scale_w = display_width / img_width
                    scale_h = display_height / img_height
                    scale = min(scale_w, scale_h)  # 使用min保持完整画面
                    
                    new_width = int(img_width * scale)
                    new_height = int(img_height * scale)
                    
                    # 缩放图像
                    pil_image = pil_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    
                    # 创建一个黑色背景的图像，将缩放后的图像居中放置
                    final_image = Image.new('RGB', (display_width, display_height), (0, 0, 0))
                    paste_x = (display_width - new_width) // 2
                    paste_y = (display_height - new_height) // 2
                    final_image.paste(pil_image, (paste_x, paste_y))
                    pil_image = final_image
                    
                    # 转换为Tkinter图像
                    tk_image = ImageTk.PhotoImage(pil_image)
                    
                    # 更新预览（在主线程中执行）
                    self.root.after(0, self._update_preview, tk_image)
                    
                    # 控制帧率
                    time.sleep(0.033)  # 约30fps
                else:
                    break
            except Exception as e:
                self.log_message(f"预览出错: {e}")
                break
        
        # 预览结束时的清理
        if self.is_previewing:
            self.root.after(0, self.stop_preview)
    
    def _update_preview(self, tk_image):
        """更新预览图像（主线程中执行）"""
        if self.is_previewing:
            self.preview_label.configure(image=tk_image, text="")
            self.preview_label.image = tk_image  # 保持引用
    
    def start_recording(self):
        """开始录制"""
        if self.is_recording:
            return
        
        # 验证配置
        if self.config["interval_seconds"].get() <= 0:
            messagebox.showerror("错误", "拍摄间隔必须大于0")
            return
        
        if self.config["duration_minutes"].get() <= 0:
            messagebox.showerror("错误", "拍摄时长必须大于0")
            return
        
        # 停止任何正在进行的视频播放
        if self.is_playing_video:
            self._stop_video_playback()
        
        # 保持预览继续运行，不中断预览画面
        
        # 更新按钮状态和文本
        self.record_toggle_button.configure(text="⏹️ 停止拍摄")
        
        # 禁用所有设置控件
        self._disable_settings()
        
        # 更新录制状态显示 - 优化颜色主题
        self.countdown_label.config(text="🔴 正在录制中...", foreground="#e74c3c", background="#fdf2f2")
        self.time_info_label.config(text="录制已开始，请等待...", foreground="#27ae60", background="#d5f4e6")
        
        # 初始化进度条
        self.progress_var.set(0)
        if self.config["recording_time_limit"].get() != "无限制":
            self.progress_bar.config(mode='determinate')
        else:
            self.progress_bar.config(mode='indeterminate')
            self.progress_bar.start(10)  # 无限制模式下显示动画
        
        # 设置录制状态
        self.is_recording = True
        
        # 启动录制线程
        self.recording_thread = threading.Thread(target=self._recording_worker)
        self.recording_thread.daemon = True
        self.recording_thread.start()
        
        # 启动倒计时线程
        self.timer_thread = threading.Thread(target=self._timer_worker)
        self.timer_thread.daemon = True
        self.timer_thread.start()
        
        # 不启动独立的录制预览线程，使用主预览持续显示
    
    def stop_recording(self):
        """停止录制"""
        self.is_recording = False
        self.log_message("正在停止拍摄...")
        
        # 清空当前录制目录
        self.current_recording_dir = None
        
        # 重置按钮状态和文本
        self.record_toggle_button.configure(text="🎬 开始拍摄")
        
        # 启用所有设置控件
        self._enable_settings()
        
        # 停止进度条动画
        self.progress_bar.stop()
        
        # 更新录制状态显示 - 优化颜色主题
        self.countdown_label.config(text="⏸️ 录制已停止", foreground="#e67e22", background="#fef5e7")
        self.time_info_label.config(text="录制已停止，正在处理...", foreground="#8e44ad", background="#f4ecf7")
        
        # 3秒后恢复初始状态
        def reset_status():
            self.countdown_label.config(text="⏸️ 未开始录制", foreground="#2c3e50", background="#ecf0f1")
            self.time_info_label.config(text="等待开始录制", foreground="#2c3e50", background="#d5dbdb")
            self.progress_var.set(0)
        
        self.root.after(3000, reset_status)
    
    def _recording_worker(self):
        """录制工作线程"""
        recording_camera = None
        try:
            # 为录制创建独立的摄像头实例
            recording_camera = cv2.VideoCapture(self.config["camera_index"].get())
            
            if not recording_camera.isOpened():
                self.log_message(f"无法打开摄像头 {self.config['camera_index'].get()}")
                return
            
            # 设置摄像头参数
            recording_camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.config["width"].get())
            recording_camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config["height"].get())
            
            if not self.config["auto_exposure"].get():
                recording_camera.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
            
            recording_camera.set(cv2.CAP_PROP_BRIGHTNESS, self.config["brightness"].get() / 100.0)
            recording_camera.set(cv2.CAP_PROP_CONTRAST, self.config["contrast"].get() / 100.0)
            recording_camera.set(cv2.CAP_PROP_SATURATION, self.config["saturation"].get() / 100.0)
            
            # 创建输出目录
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = os.path.join(self.config["output_dir"].get(), f"{self.config['filename_prefix'].get()}_{timestamp}")
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            
            # 设置当前录制目录
            self.current_recording_dir = output_dir
            
            self.log_message(f"输出目录: {output_dir}")
            
            # 保存配置
            config_dict = {key: var.get() for key, var in self.config.items()}
            config_path = os.path.join(output_dir, "config.json")
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=4, ensure_ascii=False)
            
            # 开始拍摄
            self.is_recording = True
            self.frame_count = 0
            self.start_time = datetime.now()
            
            # 根据时间限制设置计算结束时间
            if self.config["use_time_limit"].get():
                time_limit_text = self.config["recording_time_limit"].get()
                if "分钟" in time_limit_text:
                    minutes = int(time_limit_text.replace("分钟", ""))
                    end_time = self.start_time + timedelta(minutes=minutes)
                    total_seconds = minutes * 60
                    estimated_frames = int(total_seconds // self.config["interval_seconds"].get())
                    
                    self.log_message(f"开始延时拍摄...")
                    self.log_message(f"拍摄间隔: {self.config['interval_seconds'].get()}秒")
                    self.log_message(f"拍摄时长: {minutes}分钟")
                    self.log_message(f"预计帧数: {estimated_frames}")
                else:
                    end_time = None
                    self.log_message(f"开始延时拍摄...")
                    self.log_message(f"拍摄间隔: {self.config['interval_seconds'].get()}秒")
                    self.log_message(f"拍摄模式: 无限制录制")
            else:
                end_time = None
                self.log_message(f"开始延时拍摄...")
                self.log_message(f"拍摄间隔: {self.config['interval_seconds'].get()}秒")
                self.log_message(f"拍摄模式: 无限制录制")
            
            while self.is_recording and (end_time is None or datetime.now() < end_time):
                # 捕获帧
                ret, frame = recording_camera.read()
                if ret:
                    # 生成文件名
                    filename = f"{self.config['filename_prefix'].get()}_{self.frame_count:06d}.{self.config['image_format'].get()}"
                    filepath = os.path.join(output_dir, filename)
                    
                    # 设置图片质量参数
                    if self.config["image_format"].get().lower() == "jpg":
                        encode_params = [cv2.IMWRITE_JPEG_QUALITY, self.config["image_quality"].get()]
                    elif self.config["image_format"].get().lower() == "png":
                        encode_params = [cv2.IMWRITE_PNG_COMPRESSION, 9 - (self.config["image_quality"].get() // 10)]
                    else:
                        encode_params = []
                    
                    # 保存图片
                    success = cv2.imwrite(filepath, frame, encode_params)
                    
                    if success:
                        self.frame_count += 1
                        current_time = datetime.now().strftime("%H:%M:%S")
                        elapsed = datetime.now() - self.start_time
                        self.log_message(f"帧 {self.frame_count:06d} 已保存 | 已运行: {str(elapsed).split('.')[0]}")
                    else:
                        self.log_message(f"保存图片失败: {filepath}")
                else:
                    self.log_message("无法读取摄像头画面")
                
                # 等待下一次拍摄
                time.sleep(self.config["interval_seconds"].get())
            
            self.log_message(f"拍摄完成！总共捕获 {self.frame_count} 帧")
            
            # 创建视频
            if self.config["create_video"].get() and self.frame_count > 0:
                self._create_video(output_dir)
            
        except Exception as e:
            self.log_message(f"录制出错: {e}")
        
        finally:
            # 清理资源
            self.is_recording = False
            if recording_camera:
                recording_camera.release()
                recording_camera = None
            
            # 更新按钮状态
            self.root.after(0, self._reset_buttons)
            
            # 录制完成后显示视频预览并启用预览按钮
            if self.config["create_video"].get() and self.frame_count > 0:
                self.root.after(1000, lambda: self._show_video_preview(output_dir))
                self.root.after(0, lambda: self.preview_video_button.configure(state="normal"))
    
    def _timer_worker(self):
        """计时器工作线程 - 更新进度条和时间信息"""
        while self.is_recording:
            try:
                if self.start_time:
                    elapsed = datetime.now() - self.start_time
                    elapsed_str = str(elapsed).split('.')[0]
                    
                    # 检查是否有时间限制
                    time_limit_str = self.config["recording_time_limit"].get()
                    
                    if time_limit_str == "无限制":
                        # 无限制模式 - 只显示已录制时间
                        time_info = f"已录制: {elapsed_str} | 已拍摄: {self.frame_count} 帧"
                        self.root.after(0, lambda info=time_info: self.time_info_label.configure(text=info))
                    else:
                        # 有时间限制模式 - 显示进度条和剩余时间
                        time_minutes = int(time_limit_str.replace('分钟', ''))
                        total_duration = timedelta(minutes=time_minutes)
                        remaining = total_duration - elapsed
                        
                        if remaining.total_seconds() <= 0:
                            # 时间到了，停止录制
                            self.root.after(0, self.stop_recording)
                            break
                        
                        remaining_str = str(remaining).split('.')[0]
                        progress_percent = (elapsed.total_seconds() / total_duration.total_seconds()) * 100
                        
                        time_info = f"已录制: {elapsed_str} | 剩余: {remaining_str} | 已拍摄: {self.frame_count} 帧"
                        
                        # 更新进度条和时间信息
                        self.root.after(0, lambda: self.progress_var.set(progress_percent))
                        self.root.after(0, lambda info=time_info: self.time_info_label.configure(text=info))
                    
                time.sleep(1)
            except Exception as e:
                print(f"Timer worker error: {e}")
                break
    
    def _recording_preview_worker(self):
        """录制预览工作线程"""
        preview_camera = None
        try:
            # 创建独立的摄像头连接用于预览
            preview_camera = cv2.VideoCapture(self.config["camera_index"].get())
            
            if not preview_camera.isOpened():
                return
            
            # 设置预览分辨率（较小以提高性能）
            preview_camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            preview_camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            
            while self.is_recording:
                ret, frame = preview_camera.read()
                if ret:
                    try:
                        # 转换为RGB并创建缩略图
                        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        pil_image = Image.fromarray(frame_rgb)
                        
                        # 应用软件层面的图像调整（亮度、对比度、饱和度）
                        pil_image = self._apply_image_adjustments(pil_image)
                        
                        # 获取预览标签的当前尺寸
                        display_width = self.preview_label.winfo_width()
                        display_height = self.preview_label.winfo_height()
                        
                        # 如果标签尺寸还未初始化，使用默认尺寸
                        if display_width <= 1 or display_height <= 1:
                            display_width = 800
                            display_height = int(display_width / self.camera_aspect_ratio)
                        
                        img_width, img_height = pil_image.size
                        
                        # 计算缩放比例，保持宽高比
                        scale_w = display_width / img_width
                        scale_h = display_height / img_height
                        scale = min(scale_w, scale_h)  # 使用min保持完整画面
                        
                        new_width = int(img_width * scale)
                        new_height = int(img_height * scale)
                        
                        # 缩放图像
                        pil_image = pil_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                        
                        # 如果缩放后的图像尺寸与显示尺寸不完全匹配，创建黑色背景居中显示
                        if new_width != display_width or new_height != display_height:
                            final_image = Image.new('RGB', (display_width, display_height), (0, 0, 0))
                            paste_x = (display_width - new_width) // 2
                            paste_y = (display_height - new_height) // 2
                            final_image.paste(pil_image, (paste_x, paste_y))
                            pil_image = final_image
                        
                        tk_image = ImageTk.PhotoImage(pil_image)
                        
                        # 更新预览
                        self.root.after(0, lambda img=tk_image: self._update_recording_preview(img))
                        
                    except:
                        pass  # 忽略预览更新错误
                
                time.sleep(0.1)  # 10fps预览
                
        except Exception as e:
            self.log_message(f"预览出错: {e}")
        finally:
            if preview_camera:
                preview_camera.release()
    
    def _update_recording_preview(self, tk_image):
        """更新录制预览图像（主线程中执行）"""
        if self.is_recording:
            self.preview_label.configure(image=tk_image, text="")
            self.preview_label.image = tk_image  # 保持引用
    
    def _show_video_preview(self, output_dir):
        """在摄像头预览框内显示视频预览"""
        try:
            # 查找生成的视频文件
            video_files = [f for f in os.listdir(output_dir) 
                          if f.endswith(('.mp4', '.avi'))]
            
            if not video_files:
                messagebox.showinfo("提示", "未找到生成的视频文件")
                return
            
            video_path = os.path.join(output_dir, video_files[0])
            self.last_video_path = video_path  # 保存视频路径
            
            # 在摄像头预览框内显示视频缩略图
            try:
                cap = cv2.VideoCapture(video_path)
                ret, frame = cap.read()
                if ret:
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    pil_image = Image.fromarray(frame_rgb)
                    
                    # 获取预览标签的当前尺寸
                    display_width = self.preview_label.winfo_width()
                    display_height = self.preview_label.winfo_height()
                    
                    # 如果标签尺寸还未初始化，使用默认尺寸
                    if display_width <= 1 or display_height <= 1:
                        display_width, display_height = 640, 480
                    
                    # 保持宽高比缩放
                    pil_image.thumbnail((display_width, display_height), Image.Resampling.LANCZOS)
                    
                    # 在缩略图上添加播放按钮图标
                    from PIL import ImageDraw, ImageFont
                    draw = ImageDraw.Draw(pil_image)
                    
                    # 计算播放按钮位置（居中）
                    img_width, img_height = pil_image.size
                    button_size = min(img_width, img_height) // 8
                    button_x = (img_width - button_size) // 2
                    button_y = (img_height - button_size) // 2
                    
                    # 绘制半透明圆形背景
                    overlay = Image.new('RGBA', pil_image.size, (0, 0, 0, 0))
                    overlay_draw = ImageDraw.Draw(overlay)
                    overlay_draw.ellipse([button_x - button_size//2, button_y - button_size//2, 
                                        button_x + button_size//2, button_y + button_size//2], 
                                       fill=(0, 0, 0, 128))
                    
                    # 绘制播放三角形
                    triangle_size = button_size // 3
                    triangle_points = [
                        (button_x - triangle_size//2, button_y - triangle_size//2),
                        (button_x - triangle_size//2, button_y + triangle_size//2),
                        (button_x + triangle_size//2, button_y)
                    ]
                    overlay_draw.polygon(triangle_points, fill=(255, 255, 255, 200))
                    
                    # 合并图像
                    pil_image = Image.alpha_composite(pil_image.convert('RGBA'), overlay).convert('RGB')
                    
                    tk_image = ImageTk.PhotoImage(pil_image)
                    
                    # 在预览框中显示视频缩略图，并添加提示文字
                    self.preview_label.configure(image=tk_image, text="")
                    self.preview_label.image = tk_image
                    
                    # 显示视频信息和播放提示
                    self.log_message(f"视频预览已显示: {video_files[0]}")
                    self.log_message(f"视频路径: {output_dir}")
                    self.log_message("💡 点击预览框播放视频，播放时再次点击可暂停/继续")
                    
                cap.release()
            except Exception as e:
                self.preview_label.configure(image="", text=f"无法预览视频: {str(e)}")
                self.preview_label.image = None
                
        except Exception as e:
            messagebox.showerror("错误", f"预览视频时出错: {e}")
    
    def _create_video(self, output_dir):
        """创建视频"""
        try:
            # 设置视频制作状态
            self.is_creating_video = True
            self.video_creation_progress = 0
            self.root.after(0, lambda: self.preview_video_button.configure(
                text="🎬 制作中...", state="disabled"))
            
            self.log_message("正在创建延时视频...")
            
            # 获取所有图片文件
            image_files = sorted([f for f in os.listdir(output_dir) 
                                if f.endswith(f".{self.config['image_format'].get()}")])
            
            if not image_files:
                self.log_message("没有找到图片文件")
                self.is_creating_video = False
                return
            
            # 读取第一张图片获取尺寸
            first_image = cv2.imread(os.path.join(output_dir, image_files[0]))
            height, width, _ = first_image.shape
            
            # 设置视频编码器
            if self.config["video_format"].get().lower() == "mp4":
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                video_filename = f"{self.config['filename_prefix'].get()}_timelapse.mp4"
            else:
                fourcc = cv2.VideoWriter_fourcc(*'XVID')
                video_filename = f"{self.config['filename_prefix'].get()}_timelapse.avi"
            
            video_path = os.path.join(output_dir, video_filename)
            video_writer = cv2.VideoWriter(video_path, fourcc, self.config["video_fps"].get(), (width, height))
            
            # 写入视频帧
            for i, image_file in enumerate(image_files):
                image_path = os.path.join(output_dir, image_file)
                frame = cv2.imread(image_path)
                video_writer.write(frame)
                
                # 更新进度
                progress = (i + 1) / len(image_files) * 100
                self.video_creation_progress = progress
                
                # 更新按钮文本显示进度
                if i % 5 == 0:  # 每5帧更新一次UI
                    self.root.after(0, lambda p=progress: self.preview_video_button.configure(
                        text=f"🎬 制作中 {p:.0f}%"))
                    self.log_message(f"视频创建进度: {progress:.1f}%")
            
            video_writer.release()
            self.log_message(f"延时视频已创建: {video_path}")
            
            # 记录最后创建的视频路径
            self.last_video_path = video_path
            
            # 视频制作完成，更新状态
            self.is_creating_video = False
            self.root.after(0, lambda: self.preview_video_button.configure(
                text="📹 预览视频", state="normal"))
            
            # 清理原始图片（如果配置要求）
            if self.config["cleanup_images"].get():
                self.log_message("正在清理原始图片...")
                for image_file in image_files:
                    os.remove(os.path.join(output_dir, image_file))
                self.log_message("原始图片已清理")
                
        except Exception as e:
            self.log_message(f"创建视频失败: {e}")
            # 出错时重置状态
            self.is_creating_video = False
            self.root.after(0, lambda: self.preview_video_button.configure(
                text="📹 预览视频", state="normal"))
    
    def _reset_buttons(self):
        """重置按钮状态和UI显示"""
        self.record_toggle_button.configure(text="🎬 开始拍摄")
        
        # 停止进度条动画
        self.progress_bar.stop()
        
        # 重置所有显示状态 - 优化颜色主题
        self.countdown_label.configure(text="⏸️ 未开始录制", foreground="#2c3e50", background="#ecf0f1")
        self.time_info_label.configure(text="等待开始录制", foreground="#2c3e50", background="#d5dbdb")
        self.progress_var.set(0)
    
    def load_config(self):
        """加载配置"""
        filename = filedialog.askopenfilename(
            title="选择配置文件",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                # 更新配置变量
                for key, value in config_data.items():
                    if key in self.config:
                        if key == "resolution":
                            self.config["width"].set(value["width"])
                            self.config["height"].set(value["height"])
                        else:
                            self.config[key].set(value)
                
                self.log_message(f"配置已从 {filename} 加载")
                messagebox.showinfo("成功", "配置加载成功")
                
            except Exception as e:
                messagebox.showerror("错误", f"加载配置失败: {e}")
                self.log_message(f"加载配置失败: {e}")
    
    def save_config(self):
        """保存配置"""
        filename = filedialog.asksaveasfilename(
            title="保存配置文件",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                config_dict = {}
                for key, var in self.config.items():
                    if key in ["width", "height"]:
                        continue  # 这些会在resolution中处理
                    config_dict[key] = var.get()
                
                # 添加分辨率
                config_dict["resolution"] = {
                    "width": self.config["width"].get(),
                    "height": self.config["height"].get()
                }
                
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(config_dict, f, indent=4, ensure_ascii=False)
                
                self.log_message(f"配置已保存到 {filename}")
                messagebox.showinfo("成功", "配置保存成功")
                
            except Exception as e:
                messagebox.showerror("错误", f"保存配置失败: {e}")
                self.log_message(f"保存配置失败: {e}")
    
    def update_system_info(self):
        """更新系统信息显示"""
        try:
            import shutil
            try:
                import psutil
            except ImportError:
                # 如果psutil未安装，只显示磁盘空间信息
                output_dir = self.config["output_dir"].get()
                if output_dir and os.path.exists(output_dir):
                    total, used, free = shutil.disk_usage(output_dir)
                    free_gb = free / (1024**3)
                    
                    # 计算当前拍摄内容大小（只计算当前录制项目）
                    content_size = 0
                    if self.current_recording_dir and os.path.exists(self.current_recording_dir):
                        # 只计算当前录制目录的文件
                        for root, dirs, files in os.walk(self.current_recording_dir):
                            for file in files:
                                if file.lower().endswith(('.jpg', '.jpeg', '.png', '.mp4', '.avi')):
                                    file_path = os.path.join(root, file)
                                    try:
                                        content_size += os.path.getsize(file_path)
                                    except OSError:
                                        continue
                    
                    content_mb = content_size / (1024**2)
                    info_text = f"💾 可用空间: {free_gb:.1f}GB | 📁 内容: {content_mb:.1f}MB | 🧠 内存: 未安装psutil"
                    self.system_info_label.config(text=info_text)
                else:
                    self.system_info_label.config(text="💾 请选择有效的输出目录")
                return
            
            # 获取输出目录的磁盘空间信息
            output_dir = self.config["output_dir"].get()
            if output_dir and os.path.exists(output_dir):
                total, used, free = shutil.disk_usage(output_dir)
                free_gb = free / (1024**3)
                
                # 计算当前拍摄内容大小（只计算当前录制项目）
                content_size = 0
                if self.current_recording_dir and os.path.exists(self.current_recording_dir):
                    # 只计算当前录制目录的文件
                    for root, dirs, files in os.walk(self.current_recording_dir):
                        for file in files:
                            if file.lower().endswith(('.jpg', '.jpeg', '.png', '.mp4', '.avi')):
                                file_path = os.path.join(root, file)
                                try:
                                    content_size += os.path.getsize(file_path)
                                except OSError:
                                    continue
                
                content_mb = content_size / (1024**2)
                
                # 获取内存使用情况
                memory = psutil.virtual_memory()
                memory_percent = memory.percent
                memory_used_gb = (memory.total - memory.available) / (1024**3)
                memory_total_gb = memory.total / (1024**3)
                
                # 获取当前程序占用的内存
                current_process = psutil.Process()
                program_memory_mb = current_process.memory_info().rss / (1024**2)
                
                # 估算当前拍摄内容在内存中的占用（基于文件大小的近似值）
                content_memory_mb = min(content_mb, memory_used_gb * 1024 * 0.1)  # 假设最多占用10%的已用内存
                
                info_text = f"💾 可用空间: {free_gb:.1f}GB | 📁 内容: {content_mb:.1f}MB | 🧠 系统内存: {memory_percent:.1f}% | 💻 程序占用: {program_memory_mb:.1f}MB | 📸 拍摄占用: ~{content_memory_mb:.1f}MB"
                self.system_info_label.config(text=info_text)
            else:
                self.system_info_label.config(text="💾 请选择有效的输出目录")
                
        except Exception as e:
            self.system_info_label.config(text=f"💾 系统信息获取失败: {str(e)[:30]}...")
        
        # 每5秒更新一次
        self.root.after(5000, self.update_system_info)
    
    def _start_video_playback(self):
        """开始视频播放"""
        if self.is_playing_video:
            return
        
        try:
            # 停止摄像头预览
            if self.is_previewing:
                self.stop_preview()
            
            # 初始化视频播放
            self.video_cap = cv2.VideoCapture(self.last_video_path)
            if not self.video_cap.isOpened():
                messagebox.showerror("错误", "无法打开视频文件")
                return
            
            # 获取视频信息
            self.video_frame_count = int(self.video_cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.video_fps = self.video_cap.get(cv2.CAP_PROP_FPS) or 30
            self.current_frame = 0
            self.video_paused = False
            self.is_playing_video = True
            
            # 计算视频总时长
            self.video_total_seconds = self.video_frame_count / self.video_fps
            
            # 显示进度条和控制区域
            self.video_progress_bar.pack(fill="x", padx=8, pady=(0, 4))
            self.video_control_frame.pack(padx=8, pady=(0, 8))
            self.video_progress_var.set(0)
            
            # 初始化时长显示和播放按钮状态
            total_time_str = self._format_time(self.video_total_seconds)
            self.video_time_label.config(text=f"00:00 / {total_time_str}")
            self.play_pause_button.configure(text="⏸️")
            
            # 启动播放线程
            self.video_thread = threading.Thread(target=self._video_playback_worker)
            self.video_thread.daemon = True
            self.video_thread.start()
            
            self.log_message(f"开始播放视频: {os.path.basename(self.last_video_path)}")
            
        except Exception as e:
            messagebox.showerror("错误", f"播放视频失败: {e}")
            self._stop_video_playback()
    
    def _stop_video_playback(self):
        """停止视频播放"""
        self.is_playing_video = False
        self.video_paused = False
        
        if self.video_cap:
            self.video_cap.release()
            self.video_cap = None
        
        # 隐藏进度条和控制区域（检查是否存在）
        if self.video_progress_bar:
            self.video_progress_bar.pack_forget()
        if hasattr(self, 'video_control_frame') and self.video_control_frame:
            self.video_control_frame.pack_forget()
        
        # 清空预览框并重新启动摄像头预览
        self.preview_label.configure(image="", text="摄像头预览")
        self.preview_label.image = None
        
        # 重新启动摄像头预览
        if not self.is_recording and not self.is_previewing:
            self.start_preview()
        
        self.log_message("视频播放已停止")
    
    def _video_playback_worker(self):
        """视频播放工作线程"""
        try:
            frame_delay = 1.0 / self.video_fps
            
            while self.is_playing_video and self.video_cap and self.video_cap.isOpened():
                if not self.video_paused:
                    ret, frame = self.video_cap.read()
                    if ret:
                        # 转换为RGB并显示
                        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        pil_image = Image.fromarray(frame_rgb)
                        
                        # 获取预览标签的当前尺寸
                        display_width = self.preview_label.winfo_width()
                        display_height = self.preview_label.winfo_height()
                        
                        if display_width <= 1 or display_height <= 1:
                            display_width, display_height = 640, 480
                        
                        # 保持宽高比缩放
                        pil_image.thumbnail((display_width, display_height), Image.Resampling.LANCZOS)
                        tk_image = ImageTk.PhotoImage(pil_image)
                        
                        # 更新预览图像
                        self.root.after(0, self._update_video_frame, tk_image)
                        
                        # 更新进度和时长显示
                        self.current_frame += 1
                        progress = (self.current_frame / self.video_frame_count) * 100
                        current_seconds = self.current_frame / self.video_fps
                        
                        # 更新进度条和时长标签
                        self.root.after(0, lambda: self.video_progress_var.set(progress))
                        current_time_str = self._format_time(current_seconds)
                        total_time_str = self._format_time(self.video_total_seconds)
                        self.root.after(0, lambda: self.video_time_label.config(text=f"{current_time_str} / {total_time_str}"))
                        
                        time.sleep(frame_delay)
                    else:
                        # 视频播放完毕，停止播放（不再循环）
                        break
                else:
                    # 暂停状态，短暂休眠
                    time.sleep(0.1)
        except Exception as e:
            self.root.after(0, lambda: self.log_message(f"视频播放出错: {e}"))
        finally:
            # 播放结束，清理资源
            self.root.after(0, self._stop_video_playback)
    
    def _update_video_frame(self, tk_image):
        """更新视频帧（主线程中执行）"""
        if self.is_playing_video:
            self.preview_label.configure(image=tk_image, text="")
            self.preview_label.image = tk_image
    
    def _format_time(self, seconds):
        """格式化时间为 mm:ss 格式"""
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes:02d}:{seconds:02d}"
    
    def _on_progress_bar_click(self, event):
        """处理进度条点击事件"""
        if not self.is_playing_video or not self.video_cap:
            return
        
        # 计算点击位置对应的进度百分比
        progress_bar_width = self.video_progress_bar.winfo_width()
        click_x = event.x
        progress_percent = max(0, min(100, (click_x / progress_bar_width) * 100))
        
        # 跳转到对应帧
        self._seek_to_progress(progress_percent)
    
    def _on_progress_bar_drag(self, event):
        """处理进度条拖动事件"""
        if not self.is_playing_video or not self.video_cap:
            return
        
        # 计算拖动位置对应的进度百分比
        progress_bar_width = self.video_progress_bar.winfo_width()
        drag_x = event.x
        progress_percent = max(0, min(100, (drag_x / progress_bar_width) * 100))
        
        # 跳转到对应帧
        self._seek_to_progress(progress_percent)
    
    def _seek_to_progress(self, progress_percent):
        """跳转到指定进度位置"""
        if not self.video_cap or self.video_frame_count == 0:
            return
        
        # 计算目标帧数
        target_frame = int((progress_percent / 100) * self.video_frame_count)
        target_frame = max(0, min(self.video_frame_count - 1, target_frame))
        
        # 设置视频位置
        self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
        self.current_frame = target_frame
        
        # 更新进度条和时间显示
        self.video_progress_var.set(progress_percent)
        current_seconds = target_frame / self.video_fps
        time_text = f"{self._format_time(current_seconds)} / {self._format_time(self.video_total_seconds)}"
        self.video_time_label.configure(text=time_text)
    
    def _toggle_video_playback(self):
        """切换视频播放/暂停状态"""
        if not self.is_playing_video:
            return
        
        self.video_paused = not self.video_paused
        if self.video_paused:
            self.play_pause_button.configure(text="▶️")
        else:
            self.play_pause_button.configure(text="⏸️")
    
    def preview_last_video(self):
        """在摄像头预览框内预览最后录制的视频"""
        if not self.last_video_path or not os.path.exists(self.last_video_path):
            messagebox.showinfo("提示", "没有可预览的视频文件")
            return
        
        # 直接开始视频播放
        self._start_video_playback()
    
    def _update_camera_brightness(self, value):
        """实时更新摄像头亮度"""
        self.config["brightness"].set(value)
        if self.camera and self.camera.isOpened():
            try:
                # 将-100到100的值转换为0-1范围
                brightness_val = max(0.0, min(1.0, (float(value) + 100.0) / 200.0))
                self.camera.set(cv2.CAP_PROP_BRIGHTNESS, brightness_val)
                # 不在日志中显示每次调整，避免日志过多
            except Exception as e:
                self.log_message(f"设置亮度失败: {e}")
    
    def _update_camera_contrast(self, value):
        """实时更新摄像头对比度"""
        self.config["contrast"].set(value)
        if self.camera and self.camera.isOpened():
            try:
                # 将-100到100的值转换为0-1范围
                contrast_val = max(0.0, min(1.0, (float(value) + 100.0) / 200.0))
                self.camera.set(cv2.CAP_PROP_CONTRAST, contrast_val)
                # 不在日志中显示每次调整，避免日志过多
            except Exception as e:
                self.log_message(f"设置对比度失败: {e}")
    
    def _update_camera_saturation(self, value):
        """实时更新摄像头饱和度"""
        self.config["saturation"].set(value)
        if self.camera and self.camera.isOpened():
            try:
                # 将-100到100的值转换为0-1范围
                saturation_val = max(0.0, min(1.0, (float(value) + 100.0) / 200.0))
                self.camera.set(cv2.CAP_PROP_SATURATION, saturation_val)
                # 不在日志中显示每次调整，避免日志过多
            except Exception as e:
                self.log_message(f"设置饱和度失败: {e}")
    
    def _apply_image_adjustments(self, pil_image):
        """应用软件层面的图像调整（亮度、对比度、饱和度）"""
        try:
            # 获取当前参数值
            brightness_val = self.config["brightness"].get()
            contrast_val = self.config["contrast"].get()
            saturation_val = self.config["saturation"].get()
            
            # 应用亮度调整 (-100到100转换为0.0到2.0)
            if brightness_val != 0:
                brightness_factor = max(0.0, min(2.0, (brightness_val + 100.0) / 100.0))
                enhancer = ImageEnhance.Brightness(pil_image)
                pil_image = enhancer.enhance(brightness_factor)
            
            # 应用对比度调整 (-100到100转换为0.0到2.0)
            if contrast_val != 0:
                contrast_factor = max(0.0, min(2.0, (contrast_val + 100.0) / 100.0))
                enhancer = ImageEnhance.Contrast(pil_image)
                pil_image = enhancer.enhance(contrast_factor)
            
            # 应用饱和度调整 (-100到100转换为0.0到2.0)
            if saturation_val != 0:
                saturation_factor = max(0.0, min(2.0, (saturation_val + 100.0) / 100.0))
                enhancer = ImageEnhance.Color(pil_image)
                pil_image = enhancer.enhance(saturation_factor)
            
            return pil_image
        except Exception as e:
            self.log_message(f"图像调整失败: {e}")
            return pil_image
    
    def on_closing(self):
        """窗口关闭事件"""
        if self.is_recording or self.is_previewing or self.is_playing_video:
            if messagebox.askokcancel("确认", "正在录制、预览或播放视频中，确定要退出吗？"):
                self.is_recording = False
                self.is_previewing = False
                
                # 停止视频播放
                if self.is_playing_video:
                    self._stop_video_playback()
                
                if self.camera:
                    self.camera.release()
                self.root.destroy()
        else:
            self.root.destroy()


def main():
    """主函数"""
    root = tk.Tk()
    app = TimelapseGUI(root)
    
    # 设置窗口关闭事件
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    
    # 启动GUI
    root.mainloop()


if __name__ == "__main__":
    main()