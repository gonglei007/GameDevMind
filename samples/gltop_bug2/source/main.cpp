//
//  main.cpp
//  gltop_bug2
//
//  Created by Gong Lei on 12-3-30.
//  Copyright (c) 2012年 __MyCompanyName__. All rights reserved.
//

#include <iostream>

class BaseObject
{
public:
    unsigned int    mType;
};

class ObjectA : public BaseObject
{
public:
    ObjectA():
    mState(2)
    {
        mType = 1;
    }

    int     mState;
};

class ObjectB : public BaseObject
{
public:
    ObjectB():
    mFlag(4)
    {
        mType = 3;
    }

    char    mFlag;
};

int main (int argc, const char * argv[])
{
    ObjectA     a1;
    ObjectA     a2;
    ObjectB     b1;
    ObjectB     b2;
    
    BaseObject*  objectList[] = { &a1, &a2, &b1, &b2 };
    
    ObjectA*    objA = &a2;
    int*       state = &objA->mState + 1;
    *state = 10;

    // insert code here...
    std::cout << "a1:type-" << a1.mType << "state-" << a1.mState << "\n";
    std::cout << "a2:type-" << a2.mType << "state-" << a2.mState << "\n";
    std::cout << "b1:type-" << b1.mType << "flag-" << (int)b1.mFlag << "\n";
    std::cout << "b2:type-" << b2.mType << "flag-" << (int)b2.mFlag << "\n";
    return 0;
}

// 内存越界
// 栈的地址空间

