cmake_minimum_required(VERSION 3.14)
project(smart_pointer_demo VERSION 1.0.0 LANGUAGES CXX)

# C++17 标准
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# 可执行目标
add_executable(smart_pointer_demo smart_pointer_demo.cpp)

# 可选：开启更多警告
if(MSVC)
    target_compile_options(smart_pointer_demo PRIVATE /W4)
else()
    target_compile_options(smart_pointer_demo PRIVATE -Wall -Wextra -Wpedantic)
endif()
