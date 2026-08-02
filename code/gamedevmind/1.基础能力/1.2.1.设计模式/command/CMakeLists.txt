cmake_minimum_required(VERSION 3.14)
project(command_pattern LANGUAGES CXX)

# C++17 标准
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# 可执行文件
add_executable(command_demo main.cpp)

# 输出信息
message(STATUS "Command Pattern Demo - Build Ready")
message(STATUS "  Run: ./command_demo")
