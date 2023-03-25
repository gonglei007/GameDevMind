#!/usr/bin/env bash
#montage $(ls ../exports/*.png | grep -v "0.") 	\
#	-auto-orient 	\
#	-resize 200x *  \
#	-mode Concatenate	\
#	-tile 6x	\
#	-border 1 	\
#	-shadow 	\
#	-background DarkSlateGray4 	\
#	-geometry +20+40 	\
#	../overview/overview.png

# all-in-one
echo "合成overview-竖向"
montage \
    ../overview/1.基础能力.png \
    ../overview/2.技术能力.png \
    ../overview/3.研发能力.png \
    ../overview/4.生产能力.png \
    ../overview/5.管理能力.png \
    ../overview/6.运营能力.png \
\
	-auto-orient 	\
	-resize 1280x *  \
	-mode Concatenate	\
	-tile 1x	\
	-border 1 	\
	-shadow 	\
	-background black 	\
	-geometry +10+10 	\
	../overview/overview-v.png

echo "合成overview-横向"
montage \
    ../overview/1.基础能力.png \
    ../overview/2.技术能力.png \
    ../overview/3.研发能力.png \
    ../overview/4.生产能力.png \
    ../overview/5.管理能力.png \
    ../overview/6.运营能力.png \
\
	-auto-orient 	\
	-resize 480x *  \
	-mode Concatenate	\
	-tile 6x	\
	-border 10 	\
	-shadow 	\
	-background black 	\
	-geometry +20+20 	\
	../overview/overview-h.png
