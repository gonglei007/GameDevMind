# magick ../exports/*.png 	\
# 	-auto-orient 	\
# 	-resize 1280x *  \
# 	-mode Concatenate	\
# 	-tile 1x	\
# 	-border 1 	\
# 	-shadow 	\
# 	-background black 	\
# 	-geometry +10+10 	\
# 	../output/gamedevmind.pdf

#       -resize $((i*827/100))x$((i*1169/100)) \
#       -repage $((i*827/100))x$((i*1169/100)) \

i=150;width=2560;height=2048; \
	convert \
	  ../exports/0.前言.png \
\
    ../exports/4.1.游戏生产.png \
    ../exports/4.1.1.数字内容生产.png \
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
	  -compress jpeg \
	  -quality 100 \
	  -background black	\
      -density ${i}x${i} \
      -units PixelsPerInch \
	  -resize ${width}x *	\
      -gravity center	\
	  -extent ${width}x *	\
      ../output/pdf/4.游戏开发-生产能力.pdf