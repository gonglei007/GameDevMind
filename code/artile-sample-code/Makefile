# 《游戏开发者应知》配套代码 Makefile
# 一键编译所有 C++ 示例

CXX = g++
CXXFLAGS = -std=c++17 -Wall -O2

DESIGN_PATTERNS = $(wildcard 01-foundation/02-design-patterns/*.cpp)

.PHONY: all clean test

all: design-patterns

# 设计模式
design-patterns:
	@echo "=== 编译设计模式示例 ==="
	@for f in $(DESIGN_PATTERNS); do \
		name=$$(basename $$f .cpp); \
		dir=$$(dirname $$f); \
		echo "  🛠️  $$name"; \
		$(CXX) $(CXXFLAGS) $$f -o $$dir/$$name; \
	done
	@echo "✅ 全部编译完成"

test:
	@echo "=== 运行所有示例 ==="
	@echo ""
	@for f in $(DESIGN_PATTERNS); do \
		name=$$(basename $$f .cpp); \
		dir=$$(dirname $$f); \
		echo "▶️  $$name"; \
		$$dir/$$name; \
		echo "---"; \
	done
	@echo ""
	@echo "=== Python 示例 ==="
	@python3 01-foundation/02-design-patterns/observer.py
	@echo "---"
	@python3 01-foundation/03-data-structures/quadtree.py
	@echo "---"
	@python3 01-foundation/05-memory/memory_demo.py
	@echo "---"
	@python3 01-foundation/07-ai-coding/ai_prompts.py

clean:
	@echo "🧹 清理编译产物..."
	@find . -type f \( -name '*.o' -o -name '*.out' -o -name 'a.out' \) -delete
	@for f in $(DESIGN_PATTERNS); do \
		name=$$(basename $$f .cpp); \
		dir=$$(dirname $$f); \
		rm -f $$dir/$$name; \
	done
	@echo "✅ 清理完成"
