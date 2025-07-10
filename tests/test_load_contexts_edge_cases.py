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

"""
Tests for load_contexts edge cases and performance under load
Based on docsru/test_improvements.md recommendations
"""

import sys
import asyncio
import random
import time
from pathlib import Path
from datetime import datetime, timezone

import pytest

# Add mcp-server to path for imports
project_root = Path(__file__).parent.parent / "mcp-server"
sys.path.append(str(project_root))

from extended_memory_mcp.core.memory.context_repository import ContextRepository


class TestLoadContextsEdgeCases:
    """Test load_contexts with focus on edge cases and large datasets"""

    @pytest.mark.asyncio
    async def test_load_contexts_pagination_edge_cases(self, context_repo):
        """Test load_contexts with large dataset to catch pagination issues"""
        # Create 30 contexts with different importance levels
        contexts = []
        for i in range(30):
            context_id = await context_repo.save_context(
                content=f"Context {i} with importance {i % 10 + 1}",
                importance_level=i % 10 + 1,  # 1-10
                project_id="large_test_project",
                tags=[f"tag_{i % 3}"]  # 3 different tags
            )
            contexts.append((context_id, i % 10 + 1))
        
        # Test edge cases
        test_cases = [
            {"importance_min": 6, "limit": 5, "expected_min": 5},
            {"importance_min": 6, "limit": 15, "expected_min": 15},
            {"importance_min": 8, "limit": 10, "expected_max": 10},
        ]
        
        for case in test_cases:
            result = await context_repo.load_contexts(
                project_id="large_test_project",
                importance_min=case["importance_min"],
                limit=case["limit"]
            )
            
            # Verify filtering worked correctly
            assert all(ctx["importance_level"] >= case["importance_min"] for ctx in result)
            
            # Verify sorting (newest first by ID)
            if len(result) > 1:
                ids = [int(ctx["id"]) for ctx in result]
                assert ids == sorted(ids, reverse=True)
            
            # Verify limit respected
            assert len(result) <= case["limit"]
            
            if "expected_min" in case:
                assert len(result) >= case["expected_min"]
            if "expected_max" in case:
                assert len(result) <= case["expected_max"]

    @pytest.mark.asyncio
    async def test_load_contexts_sorting_consistency(self, context_repo):
        """Test that sorting is deterministic and correct"""
        
        # Create contexts with deliberate ordering
        contexts = []
        base_time = datetime.now(timezone.utc)
        
        for i in range(10):
            context_id = await context_repo.save_context(
                content=f"Context {i}",
                importance_level=7,
                project_id="sort_test",
                tags=["sorting"]
            )
            contexts.append(int(context_id))
            # Small delay to ensure different timestamps
            await asyncio.sleep(0.001)
        
        # Load with different limits
        for limit in [3, 5, 8, 10]:
            result = await context_repo.load_contexts(
                project_id="sort_test",
                limit=limit,
                importance_min=1
            )
            
            # Verify deterministic order
            assert len(result) == min(limit, len(contexts))
            
            # Should be newest first (higher IDs first)
            ids = [int(ctx["id"]) for ctx in result]
            expected_ids = sorted(contexts, reverse=True)[:limit]
            assert ids == expected_ids

    @pytest.mark.asyncio
    async def test_importance_threshold_boundary(self, context_repo):
        """Test importance threshold boundary conditions"""
        # Create contexts with specific importance levels
        test_data = [
            {"content": "Level 5", "importance": 5},
            {"content": "Level 6 - First", "importance": 6}, 
            {"content": "Level 6 - Second", "importance": 6},
            {"content": "Level 7", "importance": 7},
        ]
        
        for data in test_data:
            await context_repo.save_context(
                content=data["content"],
                importance_level=data["importance"],
                project_id="boundary_test",
                tags=["boundary"]
            )
        
        # Test threshold=6 should include levels 6,7 (3 contexts)
        result = await context_repo.load_contexts(
            project_id="boundary_test",
            importance_min=6,
            limit=10
        )
        
        assert len(result) == 3
        assert all(ctx["importance_level"] >= 6 for ctx in result)
        
        # Test threshold=7 should include only level 7 (1 context)  
        result = await context_repo.load_contexts(
            project_id="boundary_test", 
            importance_min=7,
            limit=10
        )
        
        assert len(result) == 1
        assert result[0]["importance_level"] == 7

    @pytest.mark.asyncio
    async def test_production_scale_load_contexts(self, context_repo):
        """Test load_contexts with production-like data volumes"""
        # Create 100 contexts simulating real usage
        project_id = "production_scale_test"
        
        for i in range(100):
            await context_repo.save_context(
                content=f"Production context {i}: " + "x" * (i * 10),  # Variable content length
                importance_level=random.randint(1, 10),
                project_id=project_id,
                tags=[f"tag_{i % 5}", "production"]
            )
        
        # Test various real-world scenarios
        scenarios = [
            {"min_importance": 1, "limit": 10, "description": "Default load"},
            {"min_importance": 6, "limit": 20, "description": "Important contexts"},
            {"min_importance": 8, "limit": 5, "description": "Critical contexts only"},
            {"min_importance": 1, "limit": 50, "description": "Large page load"},
        ]
        
        for scenario in scenarios:
            start_time = time.time()
            
            result = await context_repo.load_contexts(
                project_id=project_id,
                importance_min=scenario["min_importance"],
                limit=scenario["limit"]
            )
            
            end_time = time.time()
            
            # Verify basic constraints
            assert len(result) <= scenario["limit"]
            assert all(ctx["importance_level"] >= scenario["min_importance"] for ctx in result)
            
            # Verify performance (should complete in reasonable time < 1s)
            assert end_time - start_time < 1.0, f"Query took {end_time - start_time:.2f}s for {scenario['description']}"

    @pytest.mark.asyncio
    async def test_absolute_correctness_vs_consistency(self, context_repo):
        """Test actual correctness, not just provider consistency"""
        # Create known dataset with controlled order
        known_contexts = [
            {"content": "Important A", "importance": 8},
            {"content": "Important B", "importance": 8}, 
            {"content": "Normal C", "importance": 5},
            {"content": "Critical D", "importance": 9},
        ]
        
        saved_ids = []
        for ctx in known_contexts:
            context_id = await context_repo.save_context(
                content=ctx["content"],
                importance_level=ctx["importance"],
                project_id="correctness_test",
                tags=["correctness"]
            )
            saved_ids.append(int(context_id))
            # Ensure different save times
            await asyncio.sleep(0.001)
        
        # Test specific expected results
        result = await context_repo.load_contexts(
            project_id="correctness_test",
            importance_min=8,
            limit=10
        )
        
        # Should return contexts with importance >= 8, sorted by newest first
        assert len(result) == 3  # Important A, Important B, Critical D
        
        # Should be in reverse order of creation (newest first)
        assert result[0]["content"] == "Critical D"  # Last created, highest importance
        assert result[1]["content"] == "Important B"  # Second to last
        assert result[2]["content"] == "Important A"  # Second created

    @pytest.mark.asyncio
    async def test_edge_case_limits_and_thresholds(self, context_repo):
        """Test edge cases for limits and thresholds"""
        # Create test data
        for i in range(5):
            await context_repo.save_context(
                content=f"Edge case context {i}",
                importance_level=i + 1,  # 1-5
                project_id="edge_test",
                tags=["edge"]
            )
        
        # Test edge cases
        test_cases = [
            {"min_importance": 0, "limit": 0, "expected": 0},      # Zero limit
            {"min_importance": 0, "limit": 1, "expected": 1},      # Minimum limit
            {"min_importance": 1, "limit": 1000, "expected": 5},   # Limit larger than data
            {"min_importance": 10, "limit": 10, "expected": 0},    # Threshold higher than any data
            {"min_importance": 1, "limit": 3, "expected": 3},      # Normal case
        ]
        
        for case in test_cases:
            result = await context_repo.load_contexts(
                project_id="edge_test",
                importance_min=case["min_importance"],
                limit=case["limit"]
            )
            
            assert len(result) == case["expected"], f"Failed for case {case}"

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, context_repo):
        """Test concurrent save and load operations"""
        project_id = "concurrent_test"
        
        # Simulate concurrent saves
        async def save_context(i):
            return await context_repo.save_context(
                content=f"Concurrent context {i}",
                importance_level=random.randint(1, 10),
                project_id=project_id,
                tags=[f"concurrent_{i % 3}"]
            )
        
        # Save 20 contexts concurrently
        save_tasks = [save_context(i) for i in range(20)]
        saved_ids = await asyncio.gather(*save_tasks)
        
        # Verify all contexts were saved
        assert len(saved_ids) == 20
        assert all(context_id for context_id in saved_ids)
        
        # Load contexts and verify consistency
        result = await context_repo.load_contexts(
            project_id=project_id,
            importance_min=1,
            limit=25
        )
        
        assert len(result) == 20
        # All contexts should have valid structure
        for ctx in result:
            assert "id" in ctx
            assert "content" in ctx
            assert "importance_level" in ctx
            assert ctx["project_id"] == project_id
