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
    ../exports/5.管理能力.png \
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
	  -compress jpeg \
	  -quality 100 \
	  -background black	\
      -density ${i}x${i} \
      -units PixelsPerInch \
	  -resize ${width}x *	\
      -gravity center	\
	  -extent ${width}x *	\
      ../output/pdf/5.游戏开发-管理能力.pdf