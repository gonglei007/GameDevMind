cmake_minimum_required(VERSION 3.16)
project(hex_astar_demo LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# 优化 & 警告
if(CMAKE_BUILD_TYPE STREQUAL "Debug")
    add_compile_options(-g -O0 -Wall -Wextra -pedantic)
else()
    add_compile_options(-O2 -Wall -Wextra)
endif()

add_executable(hex_demo main.cpp)

# 头文件依赖 (header-only, 但告诉 CMake 以便 IDE 识别)
target_include_directories(hex_demo PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})

# 如需目标属性
set_target_properties(hex_demo PROPERTIES
    CXX_STANDARD 17
    CXX_STANDARD_REQUIRED ON
)
