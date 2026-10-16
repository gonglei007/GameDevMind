#include <condition_variable>
#include <cstdint>
#include <iostream>
#include <mutex>
#include <stdexcept>
#include <thread>
#include <vector>

// A reusable C++17 barrier, separate from the two business mutexes.
class Gate {
    std::mutex mutex_;
    std::condition_variable changed_;
    int arrivals_ = 0;
    int generation_ = 0;
public:
    void wait() {
        std::unique_lock<std::mutex> lock(mutex_);
        const auto generation = generation_;
        if (++arrivals_ == 2) {
            arrivals_ = 0;
            ++generation_;
            changed_.notify_all();
        } else {
            changed_.wait(lock, [&] { return generation_ != generation; });
        }
    }
};

static void require(bool value, const char* message) {
    if (!value) throw std::runtime_error(message);
}

// Reproduce the WAIT CYCLE CONDITIONS, not an indefinitely hung process.
static void verify_abba_conditions() {
    std::mutex player, guild;
    Gate both_holding, both_attempted;
    bool player_waits = false, guild_waits = false;
    std::thread logic([&] {
        std::lock_guard<std::mutex> first(player);
        both_holding.wait();
        player_waits = !guild.try_lock();
        if (!player_waits) guild.unlock();
        both_attempted.wait(); // Keep the first lock until BOTH second-lock attempts complete.
    });
    std::thread network([&] {
        std::lock_guard<std::mutex> first(guild);
        both_holding.wait();
        guild_waits = !player.try_lock();
        if (!guild_waits) player.unlock();
        both_attempted.wait();
    });
    logic.join();
    network.join();
    require(player_waits && guild_waits, "ABBA wait cycle conditions not reproduced");
}

struct Player {
    std::mutex mutex;
    int guild_id = 7;
    std::uint64_t events = 0;
};

struct Guild {
    std::mutex mutex;
    int id = 7;
    std::uint64_t events = 0;
};

// Precondition: callers hold neither lock. All nested paths use Guild -> Player.
static bool apply_ordered(Guild& guild, Player& player) {
    std::lock_guard<std::mutex> guild_lock(guild.mutex);
    std::lock_guard<std::mutex> player_lock(player.mutex);
    if (player.guild_id != guild.id) return false; // Snapshot lifetime != current membership.
    ++player.events;
    ++guild.events;
    // No network/DB call or callback while business locks are held.
    return true;
}

static bool apply_scoped(Guild& guild, Player& player, bool reversed_arguments) {
    // scoped_lock uses a deadlock-avoiding sequence, not an atomic all-or-nothing instruction.
    if (reversed_arguments) {
        std::scoped_lock locks(player.mutex, guild.mutex);
        if (player.guild_id != guild.id) return false;
        ++player.events;
        ++guild.events;
    } else {
        std::scoped_lock locks(guild.mutex, player.mutex);
        if (player.guild_id != guild.id) return false;
        ++player.events;
        ++guild.events;
    }
    return true;
}

static void verify_fixed_paths(bool use_scoped) {
    Guild guild;
    Player player;
    constexpr int workers = 4;
    constexpr int iterations = 2000;
    std::vector<std::thread> threads;
    for (int worker = 0; worker < workers; ++worker) {
        threads.emplace_back([&, worker] {
            for (int i = 0; i < iterations; ++i) {
                if (use_scoped) apply_scoped(guild, player, worker % 2 == 0);
                else apply_ordered(guild, player);
            }
        });
    }
    for (auto& thread : threads) thread.join();
    require(guild.events == workers * iterations && player.events == guild.events,
        "Progress or cross-object invariant failed");
    { // Simulate membership invalidation after a previously obtained member snapshot.
        std::lock_guard<std::mutex> guild_lock(guild.mutex);
        std::lock_guard<std::mutex> player_lock(player.mutex);
        player.guild_id = 0;
    }
    require(!apply_ordered(guild, player) && !apply_scoped(guild, player, true),
        "Stale membership accepted");
    require(player.events == workers * iterations && guild.events == player.events,
        "Rejected membership changed counters");
}

int main() {
    try {
        verify_abba_conditions();
        verify_fixed_paths(false);
        verify_fixed_paths(true);
        std::cout << "PASS: ABBA conditions, ordered/scoped progress and membership invariants\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
