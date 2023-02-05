#!/usr/bin/env bash

i=150;width=2560;height=2048; \
	convert \
	  ../exports/0.前言.png \
\
    ../exports/1.基础能力.png \
    ../exports/1.1.编程语言.png \
    ../exports/1.1.1.编程语言共通概念.png \
    ../exports/1.1.2.C++语言.png \
\
	  -compress jpeg \
	  -quality 100 \
	  -background black	\
      -density ${i}x${i} \
      -units PixelsPerInch \
	  -resize ${width}x *	\
      -gravity center	\
	  -extent ${width}x *	\
      ../output/test.pdf