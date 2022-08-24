//
//  main.cpp
//  bug602
//
//  Created by Gong Lei on 12-3-14.
//  Copyright (c) 2012年 __MyCompanyName__. All rights reserved.
//

#include <stdio.h>

int quotient(int *q, int *p)
{
	if(*p) return *q/*p  /* compute ratio */ ;
	else return *q;
}

int main()
{
    int n = 20, m = 4;
    int q = quotient( &n, &m );
    printf( "%d/%d == %d\n", n, m, q );
    return 0;
}
