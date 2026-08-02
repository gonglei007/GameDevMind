#pragma once

#include <algorithm>
#include <functional>
#include <queue>
#include <unordered_map>
#include <vector>

// ============================================================================
// 通用 A* 寻路 (模板化)
//
// 使用方式:
//   auto result = astar::find_path<Node>(
//       start,
//       is_goal,          // bool(const Node&)
//       get_neighbors,    // vector<pair<Node, Cost>>(const Node&)
//       heuristic,        // Cost(const Node&, const Node&)  估计到终点的代价
//       [hash_node]       // size_t(const Node&)  默认用 std::hash
//   );
//
//   result.path   — vector<Node>  起点到终点的节点序列
//   result.cost   — Cost           总代价
//   result.found  — bool           是否找到路径
// ============================================================================

namespace astar {

template <typename Node, typename Cost = double>
struct PathResult {
    std::vector<Node> path;
    Cost cost = Cost{};
    bool found = false;
};

template <typename Node, typename Cost = double>
PathResult<Node, Cost> find_path(
    Node start,
    std::function<bool(const Node&)>           is_goal,
    std::function<std::vector<std::pair<Node, Cost>>(const Node&)> get_neighbors,
    std::function<Cost(const Node&, const Node&)> heuristic,
    std::function<size_t(const Node&)> hash_node = std::hash<Node>{})
{
    using QueueEntry = std::pair<Cost, Node>;  // (f_score, node)

    // 最小堆: 按 f = g + h 排序
    auto cmp = [](const QueueEntry& a, const QueueEntry& b) {
        return a.first > b.first;  // priority_queue 默认最大堆, 反转
    };
    std::priority_queue<QueueEntry, std::vector<QueueEntry>, decltype(cmp)> open(cmp);

    std::unordered_map<size_t, Cost> g_score;   // node_hash → g
    std::unordered_map<size_t, Node> came_from; // node_hash → 前驱节点
    std::unordered_map<size_t, Node> node_by_hash; // node_hash → node (用于重建路径)

    auto hash = [&](const Node& n) { return hash_node(n); };

    size_t sh = hash(start);
    g_score[sh] = Cost{};
    node_by_hash[sh] = start;
    open.emplace(heuristic(start, start/*dummy*/), start);  // 初始 f = h(start)

    PathResult<Node, Cost> result;

    while (!open.empty()) {
        auto [f, current] = open.top();
        open.pop();

        size_t ch = hash(current);

        // 注意: 可能同一节点以不同 f 值多次入队; 跳过已处理的更优 g
        if (g_score.count(ch) && g_score[ch] < f - heuristic(current, current))
            continue;

        if (is_goal(current)) {
            result.found = true;
            result.cost = g_score[ch];
            // 重建路径
            result.path.push_back(current);
            while (true) {
                auto it = came_from.find(hash(current));
                if (it == came_from.end()) break;
                current = it->second;
                result.path.push_back(current);
            }
            std::reverse(result.path.begin(), result.path.end());
            return result;
        }

        Cost g_cur = g_score[ch];

        for (auto& [neighbor, step_cost] : get_neighbors(current)) {
            size_t nh = hash(neighbor);
            Cost tentative_g = g_cur + step_cost;

            auto git = g_score.find(nh);
            if (git == g_score.end() || tentative_g < git->second) {
                g_score[nh] = tentative_g;
                node_by_hash[nh] = neighbor;
                came_from[nh] = current;
                Cost f_score = tentative_g + heuristic(neighbor, neighbor/*dummy - h只依赖节点本身*/);
                open.emplace(f_score, neighbor);
            }
        }
    }

    return result;  // not found
}

} // namespace astar
