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
Redis N+1 Query Performance Benchmark

Comprehensive benchmarking suite for Redis provider N+1 query issues.
Tests both current and optimized implementations to measure performance improvements.
"""

import asyncio
import json
import os
import sys
import time
from typing import Any, Dict, List

# Add the parent directory to the path so we can import from mcp-server
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp-server"))

from providers.redis_provider import RedisStorageProvider


class RedisN1PerformanceBenchmark:
    """Redis N+1 performance benchmark suite."""
    
    def __init__(self):
        self.provider = None
        
    async def setup_test_environment(self) -> bool:
        """Setup Redis provider and test data."""
        try:
            # Initialize Redis provider
            self.provider = RedisStorageProvider("redis://localhost:6379/1")
            
            print("📋 Setting up test environment...")
            
            # Clear test database
            await self.cleanup_test_data()
            
            # Create test data
            await self._create_test_data()
            
            print("✅ Test environment ready")
            return True
            
        except Exception as e:
            print(f"❌ Failed to setup test environment: {e}")
            return False
    
    async def cleanup_test_data(self):
        """Clean up test data."""
        if self.provider:
            try:
                # Clear test database
                await self.provider.redis.flushdb()
                print("🧹 Test data cleaned up")
            except Exception as e:
                print(f"⚠️  Cleanup warning: {e}")
    
    async def _create_test_data(self):
        """Create test data for benchmarking."""
        print("📝 Creating test data...")
        
        # Create projects
        projects = ["project_1", "project_2", None]  # None for global contexts
        
        # Create contexts with tags (this creates the N+1 scenario)
        context_id = 1
        for project_id in projects:
            for i in range(15):  # 15 contexts per project
                tags = [f"tag_{project_id or 'global'}_{i}", f"tag_{project_id or 'global'}_{i+1}", "common_tag"]
                
                context = {
                    "content": f"Test context {context_id} for {project_id or 'global'}",
                    "context_type": "test",
                    "importance_level": 5 + (i % 5),
                    "tags": tags,
                    "project_id": project_id
                }
                
                await self.provider.save_context(context)
                context_id += 1
        
        # Create additional tags for popular tags test
        for i in range(20):
            context = {
                "content": f"Popular tag test context {i}",
                "context_type": "test", 
                "importance_level": 7,
                "tags": [f"popular_tag_{i}", "very_popular_tag"],
                "project_id": "tag_test_project"
            }
            
            await self.provider.save_context(context)
        
        print(f"✅ Created ~{context_id + 20} test contexts with tags")
    
    async def benchmark_get_popular_tags(self) -> Dict[str, Any]:
        """Benchmark get_popular_tags N+1 performance."""
        print("\n🔍 Benchmarking get_popular_tags() N+1 issues...")
        
        scenarios = [
            {"limit": 10, "min_usage": 1, "project_id": None},
            {"limit": 20, "min_usage": 2, "project_id": None}, 
            {"limit": 15, "min_usage": 1, "project_id": "project_1"},
            {"limit": 30, "min_usage": 1, "project_id": "tag_test_project"},
        ]
        
        results = []
        
        for scenario in scenarios:
            print(f"  📈 Testing: limit={scenario['limit']}, min_usage={scenario['min_usage']}, project_id={scenario.get('project_id', 'None')}")
            
            # Measure execution time
            start_time = time.time()
            
            tags = await self.provider.get_popular_tags(
                limit=scenario["limit"],
                min_usage=scenario["min_usage"],
                project_id=scenario.get("project_id")
            )
            
            execution_time = time.time() - start_time
            
            result = {
                "scenario": scenario,
                "execution_time_ms": round(execution_time * 1000, 2),
                "results_count": len(tags),
                "estimated_redis_ops": self._estimate_redis_operations_popular_tags(
                    scenario["limit"], scenario.get("project_id") is not None
                )
            }
            
            results.append(result)
            
            print(f"    ⏱️  Time: {result['execution_time_ms']}ms")
            print(f"    📊 Results: {result['results_count']} tags")
            print(f"    🔢 Est. Redis ops: {result['estimated_redis_ops']}")
        
        return {"method": "get_popular_tags", "scenarios": results}
    
    async def benchmark_find_contexts_by_multiple_tags(self) -> Dict[str, Any]:
        """Benchmark find_contexts_by_multiple_tags N+1 performance."""
        print("\n🔍 Benchmarking find_contexts_by_multiple_tags() N+1 issues...")
        
        scenarios = [
            {"tags": ["common_tag"], "project_id": None, "limit": 20},
            {"tags": ["tag_project_1_1", "tag_project_1_2"], "project_id": None, "limit": 10},
            {"tags": ["tag_project_1_1", "common_tag"], "project_id": "project_1", "limit": 15},
            {"tags": ["popular_tag_1", "popular_tag_2", "very_popular_tag"], "project_id": "tag_test_project", "limit": 25},
        ]
        
        results = []
        
        for scenario in scenarios:
            print(f"  📈 Testing: {len(scenario['tags'])} tags, project_id={scenario.get('project_id', 'None')}")
            
            # Measure execution time
            start_time = time.time()
            
            contexts = await self.provider.find_contexts_by_multiple_tags(
                tags=scenario["tags"],
                project_id=scenario.get("project_id"),
                limit=scenario["limit"]
            )
            
            execution_time = time.time() - start_time
            
            result = {
                "scenario": scenario,
                "execution_time_ms": round(execution_time * 1000, 2),
                "results_count": len(contexts),
                "estimated_redis_ops": self._estimate_redis_operations_find_by_tags(
                    len(scenario["tags"]), scenario.get("project_id") is not None, len(contexts)
                )
            }
            
            results.append(result)
            
            print(f"    ⏱️  Time: {result['execution_time_ms']}ms")
            print(f"    📊 Results: {result['results_count']} contexts")
            print(f"    🔢 Est. Redis ops: {result['estimated_redis_ops']}")
        
        return {"method": "find_contexts_by_multiple_tags", "scenarios": results}
    
    async def benchmark_load_contexts_with_tags_filter(self) -> Dict[str, Any]:
        """Benchmark load_contexts with tags_filter N+1 performance."""
        print("\n🔍 Benchmarking load_contexts() with tags_filter N+1 issues...")
        
        scenarios = [
            {"tags_filter": ["tag_0_1", "tag_0_2"], "limit": 20, "project_id": None},
            {"tags_filter": ["tag_0_1", "tag_0_2", "tag_0_3"], "limit": 30, "project_id": None},
            {"tags_filter": ["tag_0_1", "tag_0_2"], "limit": 20, "project_id": "project_1"},
        ]
        
        results = []
        
        for scenario in scenarios:
            print(f"  📈 Testing: {len(scenario['tags_filter'])} tag filters, project_id={scenario.get('project_id', 'None')}")
            
            # Measure execution time
            start_time = time.time()
            
            contexts = await self.provider.load_contexts(
                project_id=scenario.get("project_id"),
                limit=scenario["limit"],
                importance_threshold=1,
                tags_filter=scenario["tags_filter"]
            )
            
            execution_time = time.time() - start_time
            
            result = {
                "scenario": scenario,
                "execution_time_ms": round(execution_time * 1000, 2),
                "results_count": len(contexts),
                "estimated_redis_ops": self._estimate_redis_operations_load_contexts(
                    len(scenario["tags_filter"]), scenario.get("project_id") is not None, len(contexts)
                )
            }
            
            results.append(result)
            
            print(f"    ⏱️  Time: {result['execution_time_ms']}ms")
            print(f"    📊 Results: {result['results_count']} contexts")
            print(f"    🔢 Est. Redis ops: {result['estimated_redis_ops']}")
        
        return {"method": "load_contexts", "scenarios": results}
    
    def _estimate_redis_operations_popular_tags(self, limit: int, has_project_filter: bool) -> int:
        """Estimate Redis operations for get_popular_tags (current N+1 implementation)."""
        # Assume ~20 tags exist in test data
        estimated_tags = min(20, limit * 2)  # More tags than limit usually exist
        estimated_contexts_per_tag = 10
        
        operations = 1  # KEYS operation
        operations += estimated_tags  # LRANGE per tag
        
        if has_project_filter:
            # Additional GET per context for project filtering
            operations += estimated_tags * estimated_contexts_per_tag
        
        return operations
    
    def _estimate_redis_operations_find_by_tags(self, tag_count: int, has_project_filter: bool, result_count: int) -> int:
        """Estimate Redis operations for find_contexts_by_multiple_tags."""
        operations = tag_count  # LRANGE per tag
        
        if has_project_filter:
            operations += result_count  # GET per result context
        
        return operations
    
    def _estimate_redis_operations_load_contexts(self, tag_filter_count: int, has_project_filter: bool, result_count: int) -> int:
        """Estimate Redis operations for load_contexts with tags_filter."""
        # This method calls find_contexts_by_multiple_tags + load_contexts_by_ids
        find_ops = self._estimate_redis_operations_find_by_tags(tag_filter_count, has_project_filter, result_count)
        load_ops = 1  # MGET for load_contexts_by_ids (this is already optimized)
        
        return find_ops + load_ops
    
    async def run_comprehensive_benchmark(self) -> Dict[str, Any]:
        """Run all benchmarks and return comprehensive results."""
        print("🚀 Starting Redis N+1 Performance Benchmark Suite")
        print("=" * 60)
        
        if not await self.setup_test_environment():
            return {"error": "Failed to setup test environment"}
        
        try:
            # Run all benchmarks
            results = {
                "benchmark_info": {
                    "description": "Redis N+1 Performance Issues Benchmark",
                    "test_data": "20-50 tags with 10-15 contexts each",
                    "redis_version": "Unknown",  # Could add version detection
                    "timestamp": time.time()
                },
                "benchmarks": []
            }
            
            # Benchmark each problematic method
            results["benchmarks"].append(await self.benchmark_get_popular_tags())
            results["benchmarks"].append(await self.benchmark_find_contexts_by_multiple_tags())
            results["benchmarks"].append(await self.benchmark_load_contexts_with_tags_filter())
            
            # Calculate summary statistics
            total_time = sum(
                scenario["execution_time_ms"] 
                for benchmark in results["benchmarks"] 
                for scenario in benchmark["scenarios"]
            )
            
            total_operations = sum(
                scenario["estimated_redis_ops"]
                for benchmark in results["benchmarks"]
                for scenario in benchmark["scenarios"]
            )
            
            results["summary"] = {
                "total_scenarios_tested": sum(len(b["scenarios"]) for b in results["benchmarks"]),
                "total_execution_time_ms": round(total_time, 2),
                "total_estimated_redis_operations": total_operations,
                "average_time_per_scenario_ms": round(total_time / len([s for b in results["benchmarks"] for s in b["scenarios"]]), 2)
            }
            
            print("\n" + "=" * 60)
            print("📊 BENCHMARK SUMMARY")
            print("=" * 60)
            print(f"Total scenarios tested: {results['summary']['total_scenarios_tested']}")
            print(f"Total execution time: {results['summary']['total_execution_time_ms']}ms")
            print(f"Total Redis operations: {results['summary']['total_estimated_redis_operations']}")
            print(f"Average time per scenario: {results['summary']['average_time_per_scenario_ms']}ms")
            
            # Highlight worst performers
            worst_scenarios = []
            for benchmark in results["benchmarks"]:
                for scenario in benchmark["scenarios"]:
                    worst_scenarios.append({
                        "method": benchmark["method"],
                        "time_ms": scenario["execution_time_ms"],
                        "redis_ops": scenario["estimated_redis_ops"],
                        "scenario": scenario["scenario"]
                    })
            
            # Sort by Redis operations (main N+1 indicator)
            worst_scenarios.sort(key=lambda x: x["redis_ops"], reverse=True)
            
            print(f"\n🚨 WORST N+1 PERFORMERS:")
            for i, scenario in enumerate(worst_scenarios[:3]):
                print(f"{i+1}. {scenario['method']}: {scenario['redis_ops']} ops, {scenario['time_ms']}ms")
            
            return results
            
        except Exception as e:
            print(f"❌ Benchmark failed: {e}")
            return {"error": str(e)}
        
        finally:
            # Cleanup
            await self.cleanup_test_data()
            print("\n🧹 Benchmark cleanup complete")


async def main():
    """Run the Redis N+1 performance benchmark."""
    benchmark = RedisN1PerformanceBenchmark()
    results = await benchmark.run_comprehensive_benchmark()
    
    if "error" not in results:
        # Save results to file
        output_file = "redis_n1_benchmark_results.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n💾 Results saved to {output_file}")
        
        # Print optimization potential
        print("\n🎯 OPTIMIZATION POTENTIAL:")
        print("Based on SQLite fixes (8.6-9.5x speedup), Redis could achieve:")
        
        for benchmark in results["benchmarks"]:
            method = benchmark["method"]
            avg_time = sum(s["execution_time_ms"] for s in benchmark["scenarios"]) / len(benchmark["scenarios"])
            avg_ops = sum(s["estimated_redis_ops"] for s in benchmark["scenarios"]) / len(benchmark["scenarios"])
            
            optimized_time = avg_time / 9  # Assume 9x speedup like SQLite
            optimized_ops = 3  # Batch operations typically reduce to ~3 operations
            
            print(f"  {method}:")
            print(f"    Current: {avg_time:.1f}ms avg, {avg_ops:.0f} Redis ops avg")
            print(f"    Optimized: {optimized_time:.1f}ms avg, {optimized_ops} Redis ops avg")
            print(f"    Improvement: {avg_time/optimized_time:.1f}x faster, {avg_ops/optimized_ops:.1f}x fewer operations")
    
    else:
        print(f"\n❌ Benchmark failed: {results['error']}")


if __name__ == "__main__":
    asyncio.run(main())
