// Lifecycle regression for cases/memory-leak-slg.md. No intentional leaks remain.
#include <algorithm>
#include <cstdint>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <vector>

void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

namespace strong {
struct Guild;
struct Player : std::enable_shared_from_this<Player> {
    std::uint64_t id = 1;
    std::shared_ptr<Guild> guild;
    void join(const std::shared_ptr<Guild>& target);
    void leave();
};

struct Guild {
    std::vector<std::shared_ptr<Player>> members;
    void remove(std::uint64_t id) {
        members.erase(std::remove_if(members.begin(), members.end(),
            [id](const auto& player) { return player->id == id; }), members.end());
    }
};

void Player::join(const std::shared_ptr<Guild>& target) {
    guild = target;
    guild->members.push_back(shared_from_this());
}

void Player::leave() {
    if (guild) {
        guild->remove(id);
        guild.reset();
    }
}
}  // namespace strong

namespace weak {
struct Player;
struct Guild { std::vector<std::weak_ptr<Player>> members; };
struct Player { std::shared_ptr<Guild> guild; };
}  // namespace weak

int main() {
    try {
        // 1. The original erase + reset path breaks the strong-reference cycle.
        auto player = std::make_shared<strong::Player>();
        auto guild = std::make_shared<strong::Guild>();
        std::weak_ptr<strong::Player> player_watch = player;
        std::weak_ptr<strong::Guild> guild_watch = guild;
        player->join(guild);
        player->leave();
        require(guild->members.empty(), "leave did not remove the guild member");
        player.reset();
        guild.reset();
        require(player_watch.expired() && guild_watch.expired(), "normal leave leaked");

        // 2. Releasing only external owners leaves both objects alive.
        player = std::make_shared<strong::Player>();
        guild = std::make_shared<strong::Guild>();
        player_watch = player;
        guild_watch = guild;
        player->join(guild);
        player.reset();
        guild.reset();
        require(!player_watch.expired() && !guild_watch.expired(), "cycle was not reproduced");
        // Clean up after observation so LeakSanitizer can validate the test itself.
        auto survivor = player_watch.lock();
        survivor->leave();
        survivor.reset();
        require(player_watch.expired() && guild_watch.expired(), "cycle cleanup failed");

        // 3. Weak guild membership allows disconnect without explicit leave.
        auto fixed_player = std::make_shared<weak::Player>();
        auto fixed_guild = std::make_shared<weak::Guild>();
        fixed_player->guild = fixed_guild;
        fixed_guild->members.push_back(fixed_player);
        std::weak_ptr<weak::Player> fixed_player_watch = fixed_player;
        std::weak_ptr<weak::Guild> fixed_guild_watch = fixed_guild;
        fixed_player.reset();
        require(fixed_player_watch.expired(), "weak membership retained the player");
        fixed_guild.reset();
        require(fixed_guild_watch.expired(), "guild was not released");
        std::cout << "PASS: normal leave, disconnect cycle, weak membership\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL: " << error.what() << '\n';
        return 1;
    }
}
