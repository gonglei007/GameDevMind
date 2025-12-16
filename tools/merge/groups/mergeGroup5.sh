#!/usr/bin/env bash

ItemSize=480x
ItemTitle=5x

# 5
echo "合成图5"
montage \
    ../exports/5.1.工作流.png \
    ../exports/5.1.1.系统开发工作流.png \
    ../exports/5.1.2.UI制作工作流.png \
    ../exports/5.1.3.更多开发工作流.png \
    ../exports/5.2.质量保障.png \
    ../exports/5.2.1.代码质量管理.png \
    ../exports/5.2.2.产品质量管理.png \
    ../exports/5.3.项目管理.png \
    ../exports/5.3.1.项目里程.png \
    ../exports/5.3.2.版本管理.png \
    ../exports/5.3.3.SCRUM.png \
    ../exports/5.3.4.团队与组织.png \
    ../exports/5.3.5.团队管理.png \
    ../exports/5.3.6.项目管理综合.png \
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
	../overview/5.管理能力.png
