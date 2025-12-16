#!/usr/bin/env bash

ItemSize=480x
ItemTitle=5x

# 2
echo "合成图2"
montage \
    ../exports/2.1.客户端技术.png \
    ../exports/2.1.1.图形与渲染.png \
    ../exports/2.1.2.物理.png \
    ../exports/2.1.3.UI.png \
    ../exports/2.1.4.声音.png \
    ../exports/2.1.5.动画与特效.png \
    ../exports/2.1.6.游戏引擎概念与应用.png \
    ../exports/2.1.7.平台开发.png \
    ../exports/2.2.服务端技术.png \
    ../exports/2.2.1.网络与通信.png \
    ../exports/2.2.2.数据库.png \
    ../exports/2.2.3.服务端中间件.png \
    ../exports/2.3.开发者工具箱.png \
    ../exports/2.3.1.通用工具.png \
    ../exports/2.3.2.客户端开发工具.png \
    ../exports/2.3.3.服务端开发工具.png \
    ../exports/2.3.4.设计工具.png \
    ../exports/2.3.5.日常工具.png \
\
	-auto-orient 	\
	-resize $ItemSize *  \
	-mode Concatenate	\
	-tile $ItemTitle	\
	-border 1 	\
	-shadow 	\
	-geometry +20+40 	\
	-background "#FF6F00" 	\
	-title "(2)"   \
	../overview/2.技术能力.png
