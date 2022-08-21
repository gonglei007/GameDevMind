<h2 align="center">C++找bug训练</h2>

# 指针

## Bug1

### 代码

```
char *CUT_CramMd5::GetClientResponse(LPCSTR ServerChallenge) 
{ 
	... 
	if (m_szPassword != NULL) 
	{ 	
		... 	
		if (m_szPassword != '\0') 
		{ 	
			... 	
		}   
	}  
}

```

### 说明

```
此代码段的意图是：确保指针m_szPassword不是空指针，并且其内容也不是空字符串。
“if (m_szPassword != ‘\0’) ”是要检查字符串的第一个字符不是结束符。
应该写成“if (*m_szPassword != ‘\0’) ”
```

## Bug2

### 代码

```
void CG_RegisterItemVisuals( int itemNum ) { 
	...   
	itemInfo_t*	itemInfo;   
	... 
	memset( itemInfo, 0, sizeof( &itemInfo ) ); 
	...
 } 

```

### 说明

```
sizeof操作符返回的是指针的大小（32bit），而不是itemInfo_t这个结构体的大小。
应该写成"sizeof(*itemInfo)" 

```

# 数组

## Bug1

### 代码

```
ID_INLINE mat3_t::mat3_t( float (&src)[3][3] ) 
{ 
memcpy( mat, src, sizeof( src ) ); 
}
```

### 说明

```
正确的写法如下：
ID_INLINE mat3_t::mat3_t( float (&src)[3][3] ) 
{ 
memcpy( mat, src, sizeof( src ) ); 
}
```

# 字符串

## Bug1

### 代码

```
这段代码有什么问题？
typedef struct bot_state_s
{
  ...
  char  teamleader[32];
  ...
}bot_state_t;

void BotTeamAI( bot_state_t* bs ){
  ...
  bs->teamleader[sizeof( bs->teamleader )] = '\0';
  ...
} 
```

### 说明

```
正确的写法如下：
首先，至少要用 sizeof(bs->teamleader) – 1
最好这样写，这样写在数组类型改为其它类型时也不会出错：
bs->teamleader[sizeof(bs->teamleader) / sizeof(bs->teamleader[0])-1] = ‘\0’; 
```

# 运算符
## Bug1
### 代码
```
如果 'pceltFetched' 不是一个空指针，该函数必须增加该指针指向的ULONG类型变量的值。
这段代码有什么问题？
STDMETHODIMP CCustomAutoComplete::Next(..., ULONG *pceltFetched)
{
  ...
  if (pceltFetched != NULL)
    *pceltFetched++;
  ...
} 
```

### 说明
```
'++' 运算符的优先级高于 '*' 运算符的优先级（指针解引用）。该 "*pceltFetched++;" 行等同于下面的代码：
TMP = pceltFetched + 1;
*pceltFetched;
pceltFetched = TMP;
实际上它仅仅增加了指针的值。
为使代码正确，我们必须添加括号："(*pceltFetched)++;".

```


# if流程控制
## Bug1
### 代码
```
这段代码有什么问题？
void BCMenu::InsertSpaces(void)
{
  if(IsLunaMenuStyle())
    if(!xp_space_accelerators) return;
  else
    if(!original_space_accelerators) return;
  ...
}
```

### 说明
```
// 我们希望的逻辑是
if(IsLunaMenuStyle()) {
  if(!xp_space_accelerators) return;
} else {
  if(!original_space_accelerators) return;
}

// 但实际逻辑是
if(IsLunaMenuStyle())
{
   if(!xp_space_accelerators) {
     return;
   } else {
     if(!original_space_accelerators) return;
   }
}


```

# loop流程控制
## Bug1
### 代码
```
这段代码有什么问题？
bool equals( class1* val1, class2* val2 ) const{
{
  ...
  size_t size = val1->size();
  ...
  while ( --size >= 0 ){
    if ( !comp(*itr1,*itr2) )
      return false;
    itr1++;
    itr2++;
  }
  ...
}
```

### 说明
```
// size变量是无符号类型的，所以(--size >= 0) 条件总为 true.
建议这样写
for (size_t i = 0; i != size; i++){
  if ( !comp(*itr1,*itr2) )
    return false;
  itr1++;
  itr2++;
}

```

# 内存
## Bug1
### 代码
```
class Complex
{
	public:
	double real, imag;
	Complex();
};

Complex& operator+( Complex& a, Complex& b)
{
	Complex *p = new Complex;
	p->real = a.real + b.real;
	p->imag = a.imag + b.imag;
	return *p;
}
```

### 说明
```
binary operator 'Symbol' returning a reference  -- An
       operator-like function was found to be returning a reference.
       For example:

                 X &operator+ ( X &, X & );

       This is almost always a bad idea.  [12, Item 23].  You normally
       can't return a reference unless you allocate the object, but then
       who is going to delete it.  The usual way this is declared is:

                 X operator+ ( X &, X & );
```

# 注释
## Bug1
### 代码
```
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
```

### 说明
```
结果是20，为什么？
这种注释在使用时要注意
```

