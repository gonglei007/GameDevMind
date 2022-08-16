montage $(ls ../exports/*.png | grep -v "0.") 	\
	-auto-orient 	\
	-resize 400x *  \
	-mode Concatenate	\
	-tile 6x	\
	-border 1 	\
	-shadow 	\
	-background DarkSlateGray4 	\
	-geometry +20+40 	\
	../overview/overview.png
