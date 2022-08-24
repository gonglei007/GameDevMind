//
//  main.cpp
//  bug542
//
//  Created by Gong Lei on 12-3-14.
//  Copyright (c) 2012年 __MyCompanyName__. All rights reserved.
//

#include <stdio.h>

struct { int bit:1; } s;

bool f()
{
    if( s.bit > 0 ) return true;
    else return false;
}

int main()
{
    s.bit = 1;
    if( f() ) printf( "the bit is ON\n" );
    else printf( "the bit is OFF\n" );
    return 0;
}