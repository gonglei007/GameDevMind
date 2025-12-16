#!/usr/bin/env bash
montage ../exports/0.总览.png ../exports-en/0.Overview.png 	\
	-auto-orient 	\
	-geometry 4096x4096 \
	-mode Concatenate	\
	-border 1 	\
	-bordercolor LightSalmon4    \
	-background "#E9E298"   \
	../output/overview.png
