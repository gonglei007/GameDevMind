#!/bin/bash
set -e
cd "/Users/mac/Works/hermes_workspace/GameDevMind/code/gamedevmind/2.技术能力/2.2.1.网络与通信/network_sync"

echo "=== 编译 lockstep.cpp ==="
g++ -std=c++17 -Wall -Wextra -O2 lockstep.cpp -o lockstep
echo "✅ lockstep 编译成功"

echo ""
echo "=== 编译 state_sync.cpp ==="
g++ -std=c++17 -Wall -Wextra -O2 state_sync.cpp -o state_sync
echo "✅ state_sync 编译成功"

echo ""
echo "=== 运行 lockstep ==="
./lockstep

echo ""
echo "============================================================"
echo "=== 运行 state_sync ==="
./state_sync
