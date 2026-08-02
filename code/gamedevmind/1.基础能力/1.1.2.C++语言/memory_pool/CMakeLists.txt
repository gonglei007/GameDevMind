cmake_minimum_required(VERSION 3.14)
project(GameServerMemoryPool LANGUAGES CXX)

# -------------------------------------------------------------------
# 游戏服务器内存池示例
# 对应图谱：1.基础能力 / 1.1.2.C++语言 / 内存
# -------------------------------------------------------------------

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# 默认构建类型
if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release CACHE STRING
        "Build type: Debug or Release" FORCE)
endif()

# ---------- Release 配置 ----------
# 关闭 DEBUG 宏，移除哨兵/元数据开销，最快性能
add_executable(memory_pool_demo main.cpp)
target_compile_definitions(memory_pool_demo PRIVATE
    $<$<CONFIG:Debug>:DEBUG>          # Debug 时定义 DEBUG 宏
)
target_compile_options(memory_pool_demo PRIVATE
    $<$<CONFIG:Release>:-O3>
    $<$<CONFIG:Debug>:-g -O0>
)

# ---------- 安装 / 打包（可选） ----------
# install(TARGETS memory_pool_demo DESTINATION bin)
