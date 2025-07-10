#!/usr/bin/env python3

# Extended Memory MCP Server
# Copyright (c) 2024 Sergey Smirnov
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


# Extended Memory MCP Server
# Copyright (C) 2025 Sergey Smirnov
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

"""
Redis vs SQLite Performance Benchmark Suite

Comprehensive performance comparison between Redis and SQLite providers
with focus on the operations affected by N+1 issues.
"""

import asyncio
import time
import json
import statistics
from typing import List, Dict, Any, Tuple
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'mcp-server'))

from core.storage.providers.redis.redis_provider import RedisStorageProvider
from core.storage.providers.sqlite.sqlite_provider import SQLiteStorageProvider


class RedisVsSQLiteBenchmark:
    """Comprehensive benchmark suite comparing Redis vs SQLite providers."""
    
    def __init__(self):
        self.redis_provider = None
        self.sqlite_provider = None
        self.test_scenarios = [
            # Small dataset
            {"contexts": 100, "tags": 20, "tags_per_context": 3, "name": "small"},
            # Medium dataset  
            {"contexts": 1000, "tags": 100, "tags_per_context": 4, "name": "medium"},
            # Large dataset
            {"contexts": 5000, "tags": 500, "tags_per_context": 5, "name": "large"},
        ]
        
    async def setup_providers(self):
        """Initialize both Redis and SQLite providers."""
        try:
            # Redis provider
            self.redis_provider = RedisStorageProvider(
                host="localhost",
                port=6379,
                db=2,  # Use separate test database
                key_prefix="benchmark_redis"
            )
            
            # SQLite provider (in-memory for consistent testing)
            self.sqlite_provider = SQLiteStorageProvider(
                db_path=":memory:",  # In-memory database
                timeout=30.0
            )
            
            await self.sqlite_provider.initialize()
            
            print("✅ Both providers initialized successfully")
            return True
            
        except Exception as e:
            print(f"❌ Failed to initialize providers: {e}")
            return False    
    async def cleanup_providers(self):
        """Clean up both providers."""
        try:
            # Clean Redis
            if self.redis_provider:
                redis = await self.redis_provider.connection_service.get_connection()
                pattern = self.redis_provider.connection_service.make_key("*")
                keys = await redis.keys(pattern)
                if keys:
                    await redis.delete(*keys)
            
            # SQLite cleanup happens automatically (in-memory)
            print("🧹 Providers cleaned up")
            
        except Exception as e:
            print(f"⚠️  Cleanup warning: {e}")
    
    async def populate_test_data(self, provider_name: str, scenario: Dict[str, Any]) -> bool:
        """Populate test data for a specific provider and scenario."""
        provider = self.redis_provider if provider_name == "redis" else self.sqlite_provider
        
        try:
            print(f"📊 Populating {provider_name} with {scenario['name']} dataset...")
            
            contexts_count = scenario["contexts"]
            tags_count = scenario["tags"] 
            tags_per_context = scenario["tags_per_context"]
            
            # Create tags pool
            all_tags = [f"tag_{i}" for i in range(tags_count)]
            
            # Create contexts with distributed tags
            for i in range(contexts_count):
                # Select random tags for this context
                context_tags = []
                for j in range(tags_per_context):
                    tag_idx = (i * tags_per_context + j) % tags_count
                    context_tags.append(all_tags[tag_idx])
                
                # Add some common tags for realistic overlaps
                if i % 10 == 0:
                    context_tags.append("common_tag")
                if i % 25 == 0:
                    context_tags.append("frequent_tag")
                
                project_id = f"project_{i % 5}"  # 5 different projects
                
                await provider.save_context(
                    project_id=project_id,
                    content=f"Test content for context {i} in {scenario['name']} dataset",
                    importance_level=5 + (i % 6),  # Vary importance 5-10
                    tags=context_tags
                )
            
            print(f"✅ {provider_name} populated: {contexts_count} contexts, {tags_count} tags")
            return True
            
        except Exception as e:
            print(f"❌ Failed to populate {provider_name}: {e}")
            return False    
    async def benchmark_get_popular_tags(self, provider_name: str, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Benchmark get_popular_tags performance."""
        provider = self.redis_provider if provider_name == "redis" else self.sqlite_provider
        
        test_cases = [
            {"limit": 10, "min_usage": 2, "project_id": None},
            {"limit": 20, "min_usage": 3, "project_id": None},
            {"limit": 10, "min_usage": 2, "project_id": "project_1"},  # With project filter
        ]
        
        results = []
        
        for test_case in test_cases:
            times = []
            
            # Run multiple iterations for statistical accuracy
            for _ in range(3):
                start_time = time.time()
                
                if provider_name == "redis":
                    popular_tags = await provider.tag_service.get_popular_tags(
                        limit=test_case["limit"],
                        min_usage=test_case["min_usage"],
                        project_id=test_case.get("project_id")
                    )
                else:
                    popular_tags = await provider.tags_repo.get_popular_tags(
                        limit=test_case["limit"],
                        min_usage=test_case["min_usage"],
                        project_id=test_case.get("project_id")
                    )
                
                execution_time = time.time() - start_time
                times.append(execution_time * 1000)  # Convert to ms
            
            results.append({
                "test_case": test_case,
                "avg_time_ms": round(statistics.mean(times), 2),
                "min_time_ms": round(min(times), 2),
                "max_time_ms": round(max(times), 2),
                "results_count": len(popular_tags)
            })
        
        return {"method": "get_popular_tags", "results": results}    
    async def benchmark_find_contexts_by_tags(self, provider_name: str, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Benchmark find_contexts_by_multiple_tags performance.""" 
        provider = self.redis_provider if provider_name == "redis" else self.sqlite_provider
        
        test_cases = [
            {"tags": ["tag_0", "tag_1"], "limit": 50, "project_id": None},
            {"tags": ["tag_0", "tag_1", "tag_2", "tag_3", "tag_4"], "limit": 100, "project_id": None},
            {"tags": ["tag_0", "tag_1", "tag_2"], "limit": 50, "project_id": "project_1"},
        ]
        
        results = []
        
        for test_case in test_cases:
            times = []
            
            for _ in range(3):
                start_time = time.time()
                
                if provider_name == "redis":
                    context_ids = await provider.tag_service.find_contexts_by_multiple_tags(
                        tags=test_case["tags"],
                        limit=test_case["limit"],
                        project_id=test_case.get("project_id")
                    )
                else:
                    # SQLite provider method
                    context_ids = await provider.tags_repo.find_contexts_by_multiple_tags(
                        tags=test_case["tags"],
                        limit=test_case["limit"],
                        project_id=test_case.get("project_id")
                    )
                
                execution_time = time.time() - start_time
                times.append(execution_time * 1000)
            
            results.append({
                "test_case": test_case,
                "avg_time_ms": round(statistics.mean(times), 2),
                "min_time_ms": round(min(times), 2),
                "max_time_ms": round(max(times), 2),
                "results_count": len(context_ids)
            })
        
        return {"method": "find_contexts_by_multiple_tags", "results": results}    
    async def benchmark_load_contexts(self, provider_name: str, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Benchmark load_contexts with tags_filter performance."""
        provider = self.redis_provider if provider_name == "redis" else self.sqlite_provider
        
        test_cases = [
            {"tags_filter": ["tag_0", "tag_1"], "limit": 20, "project_id": None},
            {"tags_filter": ["tag_0", "tag_1", "tag_2"], "limit": 30, "project_id": None},
            {"tags_filter": ["common_tag"], "limit": 25, "project_id": "project_1"},
        ]
        
        results = []
        
        for test_case in test_cases:
            times = []
            
            for _ in range(3):
                start_time = time.time()
                
                contexts = await provider.load_contexts(
                    project_id=test_case.get("project_id"),
                    limit=test_case["limit"],
                    importance_threshold=1,
                    tags_filter=test_case["tags_filter"]
                )
                
                execution_time = time.time() - start_time
                times.append(execution_time * 1000)
            
            results.append({
                "test_case": test_case,
                "avg_time_ms": round(statistics.mean(times), 2),
                "min_time_ms": round(min(times), 2),
                "max_time_ms": round(max(times), 2),
                "results_count": len(contexts)
            })
        
        return {"method": "load_contexts", "results": results}
    
    async def run_comprehensive_benchmark(self) -> Dict[str, Any]:
        """Run comprehensive benchmark comparing Redis vs SQLite."""
        print("🚀 Redis vs SQLite Performance Benchmark")
        print("=" * 60)
        
        if not await self.setup_providers():
            return {"error": "Failed to setup providers"}
        
        all_results = {
            "benchmark_info": {
                "description": "Redis vs SQLite Performance Comparison",
                "focus": "Operations affected by N+1 issues",
                "redis_status": "With N+1 issues (unoptimized)",
                "sqlite_status": "Optimized (post N+1 fixes)",
                "timestamp": time.time()
            },
            "scenarios": []
        }
        
        try:
            for scenario in self.test_scenarios:
                print(f"\n📊 TESTING SCENARIO: {scenario['name'].upper()}")
                print(f"Contexts: {scenario['contexts']}, Tags: {scenario['tags']}")
                print("-" * 40)
                
                scenario_results = {
                    "scenario": scenario,
                    "providers": {}
                }
                
                # Test both providers with same data
                for provider_name in ["redis", "sqlite"]:
                    print(f"\n🔧 Testing {provider_name.upper()} provider...")
                    
                    # Clean and populate
                    await self.cleanup_providers()
                    if not await self.populate_test_data(provider_name, scenario):
                        continue
                    
                    # Run benchmarks
                    provider_results = {
                        "benchmarks": [],
                        "summary": {}
                    }
                    
                    # Test each method
                    benchmarks = [
                        await self.benchmark_get_popular_tags(provider_name, scenario),
                        await self.benchmark_find_contexts_by_tags(provider_name, scenario),
                        await self.benchmark_load_contexts(provider_name, scenario)
                    ]
                    
                    provider_results["benchmarks"] = benchmarks
                    
                    # Calculate summary stats
                    all_times = []
                    for benchmark in benchmarks:
                        for result in benchmark["results"]:
                            all_times.append(result["avg_time_ms"])
                    
                    provider_results["summary"] = {
                        "total_time_ms": round(sum(all_times), 2),
                        "avg_time_ms": round(statistics.mean(all_times), 2),
                        "total_operations": len(all_times)
                    }
                    
                    scenario_results["providers"][provider_name] = provider_results
                    
                    print(f"✅ {provider_name} completed: {provider_results['summary']['avg_time_ms']}ms average")
                
                # Calculate comparison
                if "redis" in scenario_results["providers"] and "sqlite" in scenario_results["providers"]:
                    redis_avg = scenario_results["providers"]["redis"]["summary"]["avg_time_ms"]
                    sqlite_avg = scenario_results["providers"]["sqlite"]["summary"]["avg_time_ms"]
                    
                    if sqlite_avg > 0:
                        performance_ratio = redis_avg / sqlite_avg
                        scenario_results["comparison"] = {
                            "redis_slower_by": round(performance_ratio, 2),
                            "redis_avg_ms": redis_avg,
                            "sqlite_avg_ms": sqlite_avg,
                            "verdict": "Redis slower" if performance_ratio > 1 else "Redis faster"
                        }
                
                all_results["scenarios"].append(scenario_results)
        
        except Exception as e:
            print(f"❌ Benchmark failed: {e}")
            all_results["error"] = str(e)
        
        finally:
            await self.cleanup_providers()
        
        return all_results


async def main():
    """Run the comprehensive Redis vs SQLite benchmark."""
    benchmark = RedisVsSQLiteBenchmark()
    results = await benchmark.run_comprehensive_benchmark()
    
    if "error" not in results:
        # Save results
        output_file = "redis_vs_sqlite_benchmark_results.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 BENCHMARK RESULTS SUMMARY")
        print("=" * 60)
        
        for scenario_result in results["scenarios"]:
            scenario = scenario_result["scenario"]
            print(f"\n🎯 {scenario['name'].upper()} Dataset ({scenario['contexts']} contexts, {scenario['tags']} tags):")
            
            if "comparison" in scenario_result:
                comparison = scenario_result["comparison"]
                print(f"   Redis: {comparison['redis_avg_ms']}ms average")
                print(f"   SQLite: {comparison['sqlite_avg_ms']}ms average")
                print(f"   📈 Performance: Redis is {comparison['redis_slower_by']:.1f}x {'slower' if comparison['redis_slower_by'] > 1 else 'faster'}")
            
        print(f"\n💾 Detailed results saved to {output_file}")
        
        # Analysis
        print(f"\n🔍 KEY INSIGHTS:")
        print(f"• Redis performance with N+1 issues vs optimized SQLite")
        print(f"• Shows the cost of N+1 antipatterns in production")
        print(f"• Demonstrates potential for Redis optimization")
        
    else:
        print(f"❌ Benchmark failed: {results['error']}")


if __name__ == "__main__":
    asyncio.run(main())
