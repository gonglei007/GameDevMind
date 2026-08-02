cmake_minimum_required(VERSION 3.14)
project(object_pool_pattern LANGUAGES CXX)

# C++17 标准（需要 if constexpr 等特性）
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# 开启优化（性能对比需要 -O2）
set(CMAKE_CXX_FLAGS_RELEASE "-O2 -DNDEBUG")
set(CMAKE_BUILD_TYPE Release)

# 可执行文件
add_executable(object_pool_demo main.cpp)

# 输出信息
message(STATUS "Object Pool Pattern Demo - Build Ready")
message(STATUS "  Build: cmake .. -DCMAKE_BUILD_TYPE=Release && make")
message(STATUS "  Run:   ./object_pool_demo")
