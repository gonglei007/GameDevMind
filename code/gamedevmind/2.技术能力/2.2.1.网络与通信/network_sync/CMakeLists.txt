cmake_minimum_required(VERSION 3.14)
project(NetworkSyncDemo VERSION 1.0.0 LANGUAGES CXX)

# C++17 标准
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# 编译选项
add_compile_options(-Wall -Wextra -O2)

# ============================================================
# 帧同步演示 (Lockstep)
# ============================================================
add_executable(lockstep lockstep.cpp)
target_compile_features(lockstep PRIVATE cxx_std_17)

# ============================================================
# 状态同步演示 (State Sync)
# ============================================================
add_executable(state_sync state_sync.cpp)
target_compile_features(state_sync PRIVATE cxx_std_17)

# ============================================================
# 安装 (可选)
# ============================================================
install(TARGETS lockstep state_sync DESTINATION bin)
