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
    ../exports/1.基础能力.png \
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
	  -compress jpeg \
	  -quality 100 \
	  -background black	\
      -density ${i}x${i} \
      -units PixelsPerInch \
	  -resize ${width}x *	\
      -gravity center	\
	  -extent ${width}x *	\
      ../output/pdf/游戏开发-基础能力.pdf