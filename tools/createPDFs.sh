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

sh ./books/images2pdf1.sh
sh ./books/images2pdf2.sh
sh ./books/images2pdf3.sh
sh ./books/images2pdf4.sh
sh ./books/images2pdf5.sh
sh ./books/images2pdf6.sh

#ls -1 ../output/pdf/*.pdf | xargs tar -czvf ../output/游戏开发技术图谱.tar.gz
# zip -r ../output/游戏开发技术图谱.zip ../output/pdf/ -x "*.DS_Store"