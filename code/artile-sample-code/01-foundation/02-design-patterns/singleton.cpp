/**
 * 游戏开发中的单例模式 — MonoSingleton
 * 
 * Unity/Cocos 中最常见的模式：全局唯一的管理器
 * 文章对应：一-02-设计模式实战
 */

#include <iostream>
#include <cassert>

// ============================================================
// 1. 基础线程安全单例 (C++11)
// ============================================================
class GameConfig {
public:
    static GameConfig& getInstance() {
        static GameConfig instance;  // C++11 保证线程安全
        return instance;
    }

    void setVolume(int v) { volume_ = v; }
    int getVolume() const { return volume_; }

private:
    GameConfig() : volume_(80) {}                        // 构造函数私有
    ~GameConfig() = default;
    GameConfig(const GameConfig&) = delete;             // 禁止拷贝
    GameConfig& operator=(const GameConfig&) = delete;  // 禁止赋值

    int volume_;
};

// ============================================================
// 2. 游戏中的 MonoSingleton（模拟 Unity 风格）
// ============================================================
template<typename T>
class MonoSingleton {
public:
    static T& getInstance() {
        static T instance;
        return instance;
    }

protected:
    MonoSingleton() = default;
    virtual ~MonoSingleton() = default;

private:
    MonoSingleton(const MonoSingleton&) = delete;
    MonoSingleton& operator=(const MonoSingleton&) = delete;
};

// 音频管理器
class AudioManager : public MonoSingleton<AudioManager> {
    friend class MonoSingleton<AudioManager>;
public:
    void playBGM(const std::string& name) {
        currentBGM_ = name;
        std::cout << "[Audio] 播放背景音乐: " << name << std::endl;
    }
    const std::string& currentBGM() const { return currentBGM_; }
private:
    AudioManager() = default;
    std::string currentBGM_;
};

// ============================================================
// 3. 服务定位器（Service Locator — 单例的进阶替代）
// ============================================================
class IAudioService {
public:
    virtual ~IAudioService() = default;
    virtual void playSound(const std::string&) = 0;
};

class RealAudioService : public IAudioService {
public:
    void playSound(const std::string& name) override {
        std::cout << "[RealAudio] 🔊 " << name << std::endl;
    }
};

class NullAudioService : public IAudioService {
public:
    void playSound(const std::string&) override {
        // 静默 — Null Object 模式
    }
};

class ServiceLocator {
public:
    static IAudioService& getAudio() { return *audioService_; }

    static void provide(IAudioService* service) {
        audioService_ = service;
    }

private:
    static inline IAudioService* audioService_ = nullptr;
    static inline NullAudioService nullService_;
};

// ============================================================
int main() {
    // 测试基础单例
    auto& config = GameConfig::getInstance();
    std::cout << "音量: " << config.getVolume() << std::endl;
    config.setVolume(50);
    std::cout << "调整后音量: " << GameConfig::getInstance().getVolume() << std::endl;

    // 测试 MonoSingleton
    auto& am = AudioManager::getInstance();
    am.playBGM("星海主题曲");
    // 同一实例
    assert(&am == &AudioManager::getInstance());
    std::cout << "✅ MonoSingleton 验证通过：全局唯一" << std::endl;

    // 测试 Service Locator
    RealAudioService realAudio;
    ServiceLocator::provide(&realAudio);
    ServiceLocator::getAudio().playSound("按钮点击");

    std::cout << "\n✅ 所有测试通过！" << std::endl;
    return 0;
}
