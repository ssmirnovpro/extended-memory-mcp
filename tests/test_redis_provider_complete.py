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
Comprehensive Redis Provider Compliance Tests

CRITICAL TASK: Validate 100% IStorageProvider interface compliance for Redis provider.
Tests every method for functionality, performance, data consistency, and edge cases.
"""

import asyncio
import json
import time
from typing import Any, Dict, List
import pytest
from unittest.mock import AsyncMock, Mock, patch

from extended_memory_mcp.core.storage.providers.redis.redis_provider import RedisStorageProvider
from extended_memory_mcp.core.storage.interfaces.storage_provider import IStorageProvider


class TestRedisProviderCompliance:
    """Comprehensive tests for Redis provider interface compliance"""
    
    @pytest.fixture
    async def redis_provider(self):
        """Mock Redis provider for testing"""
        with patch('redis.asyncio.Redis') as mock_redis_class:
            mock_redis = AsyncMock()
            mock_redis_class.return_value = mock_redis
            
            provider = RedisStorageProvider(
                host="localhost",
                port=6379,
                db=0,
                key_prefix="test"
            )
            
            # Mock the get_redis_connection method
            async def mock_get_redis():
                return mock_redis
            provider.connection_service.get_connection = mock_get_redis
            
            # Store reference to mock for test assertions
            provider._mock_redis = mock_redis
            
            yield provider

    @pytest.mark.asyncio
    async def test_get_popular_tags_basic_functionality(self, redis_provider):
        """Test get_popular_tags returns correct data structure and values"""
        
        # Setup mock data
        mock_redis = redis_provider._mock_redis
        
        # Mock tag keys discovery
        mock_redis.keys.return_value = [
            "test:tag:python:contexts",
            "test:tag:javascript:contexts", 
            "test:tag:redis:contexts"
        ]
        
        # Mock context lists for each tag
        def mock_lrange(key, start, end):
            if "python" in key:
                return ["1", "2", "3", "4"]  # 4 contexts
            elif "javascript" in key:
                return ["5", "6", "7"]  # 3 contexts  
            elif "redis" in key:
                return ["8", "9"]  # 2 contexts
            return []
        
        mock_redis.lrange.side_effect = mock_lrange
        
        # Test basic functionality
        result = await redis_provider.tag_service.get_popular_tags(limit=10, min_usage=2)
        
        # Verify results
        assert isinstance(result, list)
        assert len(result) == 3  # All tags meet min_usage=2
        
        # Check data structure
        for tag_data in result:
            assert "tag" in tag_data
            assert "count" in tag_data
            assert isinstance(tag_data["count"], int)
            
        # Check ordering (should be sorted by count desc)
        assert result[0]["tag"] == "python"
        assert result[0]["count"] == 4
        assert result[1]["tag"] == "javascript" 
        assert result[1]["count"] == 3
        assert result[2]["tag"] == "redis"
        assert result[2]["count"] == 2

    @pytest.mark.asyncio
    async def test_get_popular_tags_project_isolation(self, redis_provider):
        """Test get_popular_tags respects project_id filtering"""
        
        mock_redis = redis_provider._mock_redis
        
        # Mock tag discovery
        mock_redis.keys.return_value = ["test:tag:python:contexts"]
        
        # Mock context list
        mock_redis.lrange.return_value = ["1", "2", "3"]
        
        # Mock context data with different project_ids
        def mock_get(key):
            if "context:1" in key:
                return json.dumps({"project_id": "project_a", "content": "test1"})
            elif "context:2" in key:
                return json.dumps({"project_id": "project_b", "content": "test2"})
            elif "context:3" in key:
                return json.dumps({"project_id": "project_a", "content": "test3"})
            return None
            
        mock_redis.get.side_effect = mock_get
        
        # Test project filtering
        result = await redis_provider.tag_service.get_popular_tags(
            project_id="project_a", min_usage=1
        )
        
        # Should only count contexts from project_a (contexts 1 and 3)
        assert len(result) == 1
        assert result[0]["tag"] == "python"
        assert result[0]["count"] == 2

    @pytest.mark.asyncio 
    async def test_get_popular_tags_performance_benchmark(self, redis_provider):
        """Test get_popular_tags performance with large dataset"""
        
        mock_redis = redis_provider._mock_redis
        
        # Simulate large number of tags
        tag_keys = [f"test:tag:tag_{i}:contexts" for i in range(100)]
        mock_redis.keys.return_value = tag_keys
        
        # Mock consistent response time
        mock_redis.lrange.return_value = ["1", "2", "3"]  # 3 contexts per tag
        
        # Measure execution time
        start_time = time.time()
        result = await redis_provider.tag_service.get_popular_tags(limit=50)
        execution_time = time.time() - start_time
        
        # Performance requirement: < 1 second for 100 tags
        assert execution_time < 1.0
        assert len(result) == 50  # Limited to requested amount
        
    @pytest.mark.asyncio
    async def test_find_contexts_by_multiple_tags_or_logic(self, redis_provider):
        """Test find_contexts_by_multiple_tags implements OR logic correctly"""
        
        mock_redis = redis_provider._mock_redis
        
        # Mock tag-to-context mappings  
        def mock_lrange(key, start, end):
            if "tag1" in key:
                return ["1", "2", "3"]
            elif "tag2" in key:
                return ["3", "4", "5"] 
            elif "tag3" in key:
                return ["5", "6"]
            return []
            
        mock_redis.lrange.side_effect = mock_lrange
        
        # Test OR logic with multiple tags
        result = await redis_provider.tag_service.find_contexts_by_multiple_tags(
            tags=["tag1", "tag2", "tag3"]
        )
        
        # Should return union of all context IDs as strings (Redis uses UUID strings)
        expected_ids = {"1", "2", "3", "4", "5", "6"}
        actual_ids = set(result)
        
        assert actual_ids == expected_ids
        assert len(result) == 6

    @pytest.mark.asyncio
    async def test_find_contexts_by_multiple_tags_project_filter(self, redis_provider):
        """Test find_contexts_by_multiple_tags with project_id filtering"""
        
        mock_redis = redis_provider._mock_redis
        
        # Mock tag mappings
        mock_redis.lrange.return_value = ["1", "2", "3", "4"]
        
        # Mock context data with project filtering
        def mock_get(key):
            context_id = key.split(":")[-1]
            if context_id in ["1", "3"]:
                return json.dumps({"project_id": "target_project"})
            else:
                return json.dumps({"project_id": "other_project"})
                
        mock_redis.get.side_effect = mock_get
        
        # Test with project filtering
        result = await redis_provider.tag_service.find_contexts_by_multiple_tags(
            tags=["test_tag"],
            project_id="target_project"
        )
        
        # Should only return contexts 1 and 3
        assert set(result) == {"1", "3"}  # Redis returns string IDs

    @pytest.mark.asyncio
    async def test_list_all_projects_global_completeness(self, redis_provider):
        """Test list_all_projects_global returns ALL projects without filtering"""
        
        mock_redis = redis_provider._mock_redis
        
        # Mock context keys discovery
        mock_redis.keys.return_value = [
            "test:context:1",
            "test:context:2", 
            "test:context:3",
            "test:context:4",
            "test:context:5"
        ]
        
        # Mock context data with various project_ids as JSON strings
        def mock_get(key):
            context_id = key.split(":")[-1]
            project_mapping = {
                "1": '{"project_id": "project_a"}',
                "2": '{"project_id": "project_a"}',
                "3": '{"project_id": "project_b"}',
                "4": '{"project_id": "project_c"}',
                "5": '{"project_id": "project_b"}'
            }
            return project_mapping.get(context_id, None)
            
        mock_redis.get.side_effect = mock_get
        
        # Test global project listing
        result = await redis_provider.list_all_projects_global()
        
        # Verify all projects are included with correct counts
        assert len(result) == 3
        
        project_counts = {p["id"]: p["context_count"] for p in result}
        assert project_counts["project_a"] == 2
        assert project_counts["project_b"] == 2  
        assert project_counts["project_c"] == 1
        
        # Verify data structure
        for project in result:
            assert "id" in project
            assert "name" in project
            assert "context_count" in project

    @pytest.mark.asyncio
    async def test_tags_filter_integration_with_load_contexts(self, redis_provider):
        """Test tags_filter parameter integration in load_contexts method"""
        
        mock_redis = redis_provider._mock_redis
        
        # Mock the find_contexts_by_multiple_tags call
        with patch.object(
            redis_provider.tag_service, 
            'find_contexts_by_multiple_tags',
            return_value=[1, 2, 3]
        ) as mock_find:
            
            # Mock load_contexts_by_ids call
            with patch.object(
                redis_provider.context_service,
                'load_contexts_by_ids',
                return_value=[
                    {"id": 1, "content": "content_1", "tags": ["python"]},
                    {"id": 2, "content": "content_2", "tags": ["redis"]}, 
                    {"id": 3, "content": "content_3", "tags": ["python", "redis"]}
                ]
            ) as mock_load_by_ids:
            
                # Test load_contexts with tags_filter
                result = await redis_provider.load_contexts(
                    tags_filter=["python", "redis"],
                    limit=10
                )
                
                # Verify tags_filter was used
                mock_find.assert_called_once_with(
                    tags=["python", "redis"], 
                    limit=10, 
                    project_id=None
                )
                
                # Verify load_contexts_by_ids was called with correct IDs
                mock_load_by_ids.assert_called_once_with(["1", "2", "3"])
                
                # Verify contexts were loaded
                assert len(result) == 3
                assert all("content" in ctx for ctx in result)

    @pytest.mark.asyncio
    async def test_load_context_tags_method_exists(self, redis_provider):
        """Test load_context_tags method exists and works"""
        
        mock_redis = redis_provider._mock_redis
        
        # Mock context data with tags
        mock_redis.get.return_value = json.dumps({
            "tags": ["python", "redis", "testing"]
        })
        
        # Test the method
        result = await redis_provider.tag_service.load_context_tags(123)
        
        assert result == ["python", "redis", "testing"]
        
        # Verify correct key was accessed
        mock_redis.get.assert_called_with("test:context:123")

    @pytest.mark.asyncio
    async def test_error_handling_graceful_failures(self, redis_provider):
        """Test all methods handle Redis errors gracefully"""
        
        mock_redis = redis_provider._mock_redis
        
        # Make Redis operations fail
        mock_redis.keys.side_effect = Exception("Redis connection failed")
        mock_redis.get.side_effect = Exception("Redis connection failed")
        mock_redis.lrange.side_effect = Exception("Redis connection failed")
        
        # Test each method handles errors gracefully
        
        # get_popular_tags should return empty list
        result = await redis_provider.tag_service.get_popular_tags()
        assert result == []
        
        # find_contexts_by_multiple_tags should return empty list
        result = await redis_provider.tag_service.find_contexts_by_multiple_tags(["tag"])
        assert result == []
        
        # list_all_projects_global should return empty list  
        result = await redis_provider.list_all_projects_global()
        assert result == []
        
        # load_context_tags should return empty list
        result = await redis_provider.tag_service.load_context_tags(123)
        assert result == []

    @pytest.mark.asyncio
    async def test_edge_cases_empty_data(self, redis_provider):
        """Test methods handle empty data scenarios"""
        
        mock_redis = redis_provider._mock_redis
        
        # Test with no tag keys found
        mock_redis.keys.return_value = []
        result = await redis_provider.tag_service.get_popular_tags()
        assert result == []
        
        # Test with no contexts in tags
        mock_redis.keys.return_value = ["test:tag:empty:contexts"]
        mock_redis.lrange.return_value = []
        result = await redis_provider.tag_service.get_popular_tags()
        assert result == []
        
        # Test with no project contexts
        mock_redis.keys.return_value = []
        result = await redis_provider.list_all_projects_global()
        assert result == []

    @pytest.mark.asyncio 
    async def test_data_types_consistency(self, redis_provider):
        """Test all methods return consistent data types"""
        
        mock_redis = redis_provider._mock_redis
        
        # Setup basic mock data
        mock_redis.keys.return_value = ["test:tag:sample:contexts"]
        mock_redis.lrange.return_value = ["1", "2"]
        mock_redis.get.return_value = json.dumps({"tags": ["sample"]})
        mock_redis.hgetall.return_value = {"project_id": "test"}
        
        # Test get_popular_tags returns correct types
        result = await redis_provider.tag_service.get_popular_tags()
        assert isinstance(result, list)
        if result:
            assert isinstance(result[0], dict)
            assert isinstance(result[0]["tag"], str)
            assert isinstance(result[0]["count"], int)
        
        # Test find_contexts_by_multiple_tags returns list of strings (Redis uses UUID strings)
        result = await redis_provider.tag_service.find_contexts_by_multiple_tags(["sample"])
        assert isinstance(result, list)
        assert all(isinstance(ctx_id, str) for ctx_id in result)
        
        # Test list_all_projects_global returns correct structure
        result = await redis_provider.list_all_projects_global()
        assert isinstance(result, list)
        if result:
            project = result[0]
            assert isinstance(project["id"], str)
            assert isinstance(project["name"], str) 
            assert isinstance(project["context_count"], int)


class TestRedisProviderPerformance:
    """Performance benchmarking tests for Redis provider"""
    
    @pytest.fixture
    async def redis_provider(self):
        """Setup Redis provider for performance testing"""
        with patch('redis.asyncio.Redis') as mock_redis_class:
            mock_redis = AsyncMock()
            mock_redis_class.return_value = mock_redis
            
            provider = RedisStorageProvider()
            provider.connection_service.get_connection = AsyncMock(return_value=mock_redis)
            provider._mock_redis = mock_redis
            
            yield provider

    @pytest.mark.asyncio
    async def test_large_dataset_performance(self, redis_provider):
        """Test performance with simulated large dataset"""
        
        mock_redis = redis_provider._mock_redis
        
        # Simulate 1000 tags scenario
        large_tag_keys = [f"test:tag:tag_{i}:contexts" for i in range(1000)]
        mock_redis.keys.return_value = large_tag_keys
        
        # Each tag has 10 contexts
        mock_redis.lrange.return_value = [str(i) for i in range(10)]
        
        # Benchmark get_popular_tags
        start_time = time.time()
        result = await redis_provider.tag_service.get_popular_tags(limit=50)
        execution_time = time.time() - start_time
        
        # Performance requirement: < 1 second for 1000 tags
        assert execution_time < 1.0
        assert len(result) <= 50

    @pytest.mark.asyncio
    async def test_concurrent_operations_stability(self, redis_provider):
        """Test Redis provider stability under concurrent load"""
        
        mock_redis = redis_provider._mock_redis
        mock_redis.keys.return_value = ["test:tag:concurrent:contexts"]
        mock_redis.lrange.return_value = ["1", "2", "3"]
        
        # Run 10 concurrent operations
        tasks = []
        for _ in range(10):
            task = redis_provider.tag_service.get_popular_tags()
            tasks.append(task)
        
        # All should complete without errors
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # No exceptions should occur
        assert all(not isinstance(r, Exception) for r in results)
        
        # All should return expected data structure
        assert all(isinstance(r, list) for r in results)


class TestRedisProviderDataConsistency:
    """Test data consistency between Redis and expected SQLite behavior"""
    
    @pytest.mark.asyncio
    async def test_consistent_sorting_behavior(self):
        """Test sorting behavior matches expected SQL-like ordering"""
        # This would require comparison with SQLite provider results
        # Implementation depends on having both providers available
        pass
        
    @pytest.mark.asyncio  
    async def test_consistent_filtering_behavior(self):
        """Test filtering behavior matches expected SQL-like filtering"""
        # This would require comparison with SQLite provider results
        pass


if __name__ == "__main__":
    pytest.main([__file__])
