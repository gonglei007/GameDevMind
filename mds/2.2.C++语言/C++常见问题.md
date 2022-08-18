<h1 align="center">C++常见问题</h1>

# 野指针怎么产生的

## 示例1

```
int main(){
	int *myNum = new int(12);
	int *myOtherNum = myNum;

	delete myNum;
	
	cout << *myOtherNum << endl;

	return 0;
}
```

## 示例2

```
int* badFunction(){
	int num = 10;
	return &num;
}
int* stillBad(int n){
	n += 12;
	return &n;
}
int main(){
	int num = 12;
	int *myNum = badFunction();
	int *myOtherNum = 	stillBad(num);

	cout << *myNum << “, “;
	cout << *myOtherNum << endl;

	return 0;
}
```

# 内存对齐

## 示例1

### 代码

```
#include <iostream>
using namespace std;

struct X1
{
  int i;//4个字节
  char c1;//1个字节
  char c2;//1个字节
};

struct X2
{
  char c1;//1个字节
  int i;//4个字节
  char c2;//1个字节
};

struct X3
{
  char c1;//1个字节
  char c2;//1个字节
  int i;//4个字节
};

int main()
{   
    cout<<"long "<<sizeof(long)<<"\n";
    cout<<"float "<<sizeof(float)<<"\n";
    cout<<"int "<<sizeof(int)<<"\n";
    cout<<"char "<<sizeof(char)<<"\n";

    X1 x1;
    X2 x2;
    X3 x3;
    cout<<"x1 的大小 "<<sizeof(x1)<<"\n";
    cout<<"x2 的大小 "<<sizeof(x2)<<"\n";
    cout<<"x3 的大小 "<<sizeof(x3)<<"\n";
    return 0;
}
```

### 输出
```
long 4
float 4
int 4
char 1
x1 的大小 8
x2 的大小 12
x3 的大小 8
```
