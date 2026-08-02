cmake_minimum_required(VERSION 3.14)
project(quadtree_demo LANGUAGES CXX)

# C++17 标准
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# 优化选项
if(CMAKE_BUILD_TYPE STREQUAL "Release")
    add_compile_options(-O3 -DNDEBUG)
else()
    # Debug 模式也开基本优化，保证性能测试有意义
    add_compile_options(-O2 -g)
endif()

# 可执行文件（header-only，无需编译 quadtree.hpp）
add_executable(quadtree_demo main.cpp)

# 输出信息
message(STATUS "Quadtree Demo - Build Ready")
message(STATUS "  Run:   ./quadtree_demo")
message(STATUS "  Release: cmake -B build -DCMAKE_BUILD_TYPE=Release && cmake --build build")
