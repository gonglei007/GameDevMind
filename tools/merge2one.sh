montage $(ls ../exports/*.png | grep -v "0.") -resize 400x *  -mode Concatenate -tile 7x -geometry +20+40 ../overview/overview.png
