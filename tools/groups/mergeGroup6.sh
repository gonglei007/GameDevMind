#!/usr/bin/env bash

ItemSize=480x
ItemTitle=5x

# 6
echo "合成图6"
montage \
    ../exports/6.1.运维技术.png \
    ../exports/6.1.1.网络维护.png \
    ../exports/6.1.2.数据存储.png \
    ../exports/6.1.3.资产管理.png \
    ../exports/6.1.4.Linux系统.png \
    ../exports/6.1.5.中间件运维.png \
    ../exports/6.1.6.网络安全.png \
    ../exports/6.2.产品运营支持.png \
    ../exports/6.2.1.GM后台.png \
    ../exports/6.2.2.数据统计分析.png \
    ../exports/6.2.3.产品热更新.png \
    ../exports/6.2.4.产品本地化.png \
    ../exports/6.2.5.开发配合.png \
    ../exports/6.2.6.AI助力游戏运营.png \
    ../exports/6.3.产品商业化.png \
    ../exports/6.3.1.游戏安全.png \
    ../exports/6.3.2.帐号与支付.png \
    ../exports/6.3.3.第三方服务.png \
    ../exports/6.3.4.产品合规.png \
\
	-auto-orient 	\
	-resize $ItemSize *  \
	-mode Concatenate	\
	-tile $ItemTitle	\
	-border 1 	\
	-shadow 	\
	-geometry +20+40 	\
	-background "#4A148C" 	\
	-title "(6)"   \
	../overview/6.运营能力.png
