montage $(ls ../exports/*.png | grep -v "0.") -resize 400x *  -mode Concatenate -tile 7x -geometry +5+10 ../overview/overview.png
