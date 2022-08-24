//
//  main.cpp
//  bug603
//
//  Created by Gong Lei on 12-3-14.
//  Copyright (c) 2012年 __MyCompanyName__. All rights reserved.
//

#include <iostream>
#include <stdio.h>

//TODO: GL - not finished
void string_copy( const char *, char * );

int main (int argc, const char * argv[])
{
    char buf[12];
    string_copy( buf, "hello world" );
    printf( "%s\n", buf );
    return 0;
}

