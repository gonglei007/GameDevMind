#!/usr/bin/env bash

ItemSize=480x
ItemTitle=5x

# 1
echo "合成图1"
montage \
    ../exports/1.1.编程语言.png \
    ../exports/1.1.1.编程语言基础概念.png \
    ../exports/1.1.2.C++语言.png \
    ../exports/1.1.3.C#语言.png \
    ../exports/1.1.4.JS语言.png \
    ../exports/1.1.5.编程语言综合.png \
    ../exports/1.1.6.内存管理.png \
    ../exports/1.1.7.编程语言高阶概念.png \
    ../exports/1.2.程序设计.png \
    ../exports/1.2.1.设计模式.png \
    ../exports/1.2.2.数据结构.png \
    ../exports/1.2.3.算法.png \
    ../exports/1.3.通用基础.png \
    ../exports/1.3.1.数学.png \
    ../exports/1.3.2.人工智能.png \
    ../exports/1.3.3.操作系统.png \
    ../exports/1.3.4.计算机组成原理.png \
    ../exports/1.3.5.计算机网络.png \
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

