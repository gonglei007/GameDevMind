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
    ../exports/3.研发能力.png \
    ../exports/3.1.客户端产品研发.png \
    ../exports/3.1.1.客户端底层通用系统.png \
    ../exports/3.1.2.客户端3D场景开发.png \
    ../exports/3.1.3.客户端优化.png \
    ../exports/3.1.4.客户端网络系统.png \
    ../exports/3.1.5.渲染与特效.png \
    ../exports/3.1.6.UI系统.png \
    ../exports/3.1.7.客户端中间件.png \
    ../exports/3.2.服务端产品研发.png \
    ../exports/3.2.1.服务端底层架构.png \
    ../exports/3.2.2.网游网络同步.png \
    ../exports/3.2.3.服务端优化.png \
    ../exports/3.2.4.服务端基础功能.png \
    ../exports/3.2.5.服务端业务架构.png \
    ../exports/3.3.业务层功能.png \
    ../exports/3.3.1.摄像机控制.png \
    ../exports/3.3.2.角色.png \
    ../exports/3.3.3.综合业务层功能.png \
\
	  -compress jpeg \
	  -quality 100 \
	  -background black	\
      -density ${i}x${i} \
      -units PixelsPerInch \
	  -resize ${width}x *	\
      -gravity center	\
	  -extent ${width}x *	\
      ../output/pdf/3.游戏开发-研发能力.pdf