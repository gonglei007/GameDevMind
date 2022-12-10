#!/usr/bin/env bash

ItemSize=480x
ItemTitle=5x

# 1
echo "合成图1"
montage \
    ../exports/1.1.编程语言.png \
    ../exports/1.1.1.编程语言共通概念.png \
    ../exports/1.1.2.C++语言.png \
    ../exports/1.1.3.C#语言.png \
    ../exports/1.1.4.JS语言.png \
    ../exports/1.1.5.编程语言综合.png \
    ../exports/1.2.程序设计.png \
    ../exports/1.2.1.设计模式.png \
    ../exports/1.2.2.数据结构.png \
    ../exports/1.2.3.算法.png \
    ../exports/1.2.4.代码重构.png \
    ../exports/1.3.通用基础.png \
    ../exports/1.3.1.数学.png \
    ../exports/1.3.2.人工智能.png \
    ../exports/1.3.3.内存管理.png \
    ../exports/1.3.4.计算机组成原理.png \
\
	-auto-orient 	\
	-resize $ItemSize *  \
	-mode Concatenate	\
	-tile $ItemTitle	\
	-border 1 	\
	-shadow 	\
	-geometry +20+40 	\
	-background "#E32C2D" 	\
	-title "(1)"   \
	../overview/1.基础能力.png

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
    ../exports/2.3.开发者工具箱.png \
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

# 3
echo "合成图3"
montage \
    ../exports/3.1.客户端产品研发.png \
    ../exports/3.1.1.客户端底层通用系统.png \
    ../exports/3.1.2.客户端3D场景开发.png \
    ../exports/3.1.3.客户端优化.png \
    ../exports/3.1.4.客户端网络系统.png \
    ../exports/3.1.5.渲染与特效.png \
    ../exports/3.2.服务端产品研发.png \
    ../exports/3.2.1.服务端架构.png \
    ../exports/3.2.2.网游网络同步.png \
    ../exports/3.2.3.服务端优化.png \
    ../exports/3.3.业务层功能系统.png \
    ../exports/3.4.生产工具研发.png \
    ../exports/3.4.1.游戏引擎原理与开发.png \
    ../exports/3.4.2.编辑器开发.png \
    ../exports/3.4.3.工具开发与应用.png \
\
	-auto-orient 	\
	-resize $ItemSize *  \
	-mode Concatenate	\
	-tile $ItemTitle	\
	-border 1 	\
	-shadow 	\
	-geometry +20+40 	\
	-background "#FFFB00" 	\
	-title "(3)"   \
	../overview/3.研发能力.png

# 4
echo "合成图4"
montage \
    ../exports/4.1.工程管理.png \
    ../exports/4.1.1.数字内容生产线.png \
    ../exports/4.1.2.系统开发生产线.png \
    ../exports/4.1.3.DevOps.png \
    ../exports/4.1.4.开发工作流.png \
    ../exports/4.2.项目管理.png \
    ../exports/4.2.1.项目管理综合.png \
    ../exports/4.2.2.版本管理.png \
    ../exports/4.2.3.质量保证.png \
    ../exports/4.2.4.团队与组织.png \
    ../exports/4.2.5.SCRUM.png \
    ../exports/4.3.技术中台.png \
    ../exports/4.3.1.快速开发框架.png \
    ../exports/4.3.2.技术支持.png \
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
	../overview/4.管理能力.png

# 5
echo "合成图5"
montage \
    ../exports/5.1.运维技术.png \
    ../exports/5.1.1.网络维护.png \
    ../exports/5.1.2.数据存储.png \
    ../exports/5.1.3.资产管理.png \
    ../exports/5.1.4.Linux系统.png \
    ../exports/5.2.产品运营支持.png \
    ../exports/5.2.1.GM后台.png \
    ../exports/5.2.2.数据统计分析.png \
    ../exports/5.2.3.产品热更新.png \
    ../exports/5.2.4.产品本地化.png \
    ../exports/5.3.产品商业化.png \
    ../exports/5.3.1.游戏安全.png \
    ../exports/5.3.2.帐号与支付.png \
\
	-auto-orient 	\
	-resize $ItemSize *  \
	-mode Concatenate	\
	-tile $ItemTitle	\
	-border 1 	\
	-shadow 	\
	-geometry +20+40 	\
	-background "#00526B" 	\
	-title "(5)"   \
	../overview/5.商品化能力.png
