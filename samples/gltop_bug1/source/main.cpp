//
//  main.cpp
//  gltop_bug1
//
//  Created by Gong Lei on 12-3-17.
//  Copyright (c) 2012年 __MyCompanyName__. All rights reserved.
//

#include <iostream>

using namespace std;

int main()
{
    //声明变量，并初始化
    int a=010, b=10, c=0X10; 
    
    //以十进制形式显示数据
    cout << "DEC:";
    cout << " a=" << a;
    cout << " b=" << b;
    cout << " c=" << c << endl; 
    
    return 0;
}