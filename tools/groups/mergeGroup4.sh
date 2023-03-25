#!/usr/bin/env bash

ItemSize=480x
ItemTitle=5x

# 4
echo "合成图4"
montage \
    ../exports/4.1.游戏生产.png \
    ../exports/4.1.1.数字内容生产线.png \
    ../exports/4.1.2.AI助力游戏生产.png \
    ../exports/4.1.3.引擎的基本功能系统.png \
    ../exports/4.1.4.引擎的其它系统.png \
    ../exports/4.2.工具开发.png \
    ../exports/4.2.1.编辑器开发.png \
    ../exports/4.2.2.工具开发与应用.png \
    ../exports/4.2.3.游戏数据文件.png \
    ../exports/4.3.技术中台.png \
    ../exports/4.3.1.快速开发框架.png \
    ../exports/4.3.2.技术支持.png \
    ../exports/4.3.3.DevOps.png \
\
	-auto-orient 	\
	-resize $ItemSize *  \
	-mode Concatenate	\
	-tile $ItemTitle	\
	-border 1 	\
	-shadow 	\
	-geometry +20+40 	\
	-background "#15831C" 	\
	-title "(4)"   \
	../overview/4.生产能力.png
