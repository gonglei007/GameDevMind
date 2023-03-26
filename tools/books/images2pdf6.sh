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
    ../exports/6.运营能力.png \
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
\
	  -compress jpeg \
	  -quality 100 \
	  -background black	\
      -density ${i}x${i} \
      -units PixelsPerInch \
	  -resize ${width}x *	\
      -gravity center	\
	  -extent ${width}x *	\
      ../output/pdf/游戏开发-运营能力.pdf