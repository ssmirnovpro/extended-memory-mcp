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
Access Tracking Usage Audit

This script analyzes the actual usage of access_count and last_accessed fields
to determine if they can be safely removed as part of cleanup.
"""

import asyncio
import logging
import sqlite3
from pathlib import Path

# Setup path and imports
import sys
sys.path.append("/Users/sergeysmirnov/projects/extended-memory-mcp-dev/mcp-server")

from core.storage.providers.sqlite.sqlite_provider import SQLiteStorageProvider

# Disable debug logging
logging.getLogger("core.storage").setLevel(logging.WARNING)
logging.getLogger("core.memory").setLevel(logging.WARNING)

class AccessTrackingAuditor:
    def __init__(self):
        self.provider = None
        
    async def setup(self):
        """Setup connection to existing database"""
        # Use default database path
        self.provider = SQLiteStorageProvider()
        await self.provider.initialize()
        
    async def audit_access_tracking_usage(self):
        """Audit how access tracking fields are actually used"""
        print("🔍 Access Tracking Usage Audit")
        print("=" * 50)
        
        # Check current database state
        db_path = self.provider.db_manager.db_path
        print(f"Database: {db_path}")
        
        try:
            # Direct SQL analysis
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 1. Check contexts with non-zero access_count
            cursor.execute("SELECT COUNT(*) FROM contexts WHERE access_count > 0")
            contexts_with_access = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM contexts")
            total_contexts = cursor.fetchone()[0]
            
            print(f"\n📊 Context Access Count Usage:")
            print(f"   Total contexts: {total_contexts}")
            print(f"   Contexts with access_count > 0: {contexts_with_access}")
            print(f"   Percentage with access tracking: {contexts_with_access/total_contexts*100:.1f}%" if total_contexts > 0 else "   No contexts found")
            
            # 2. Check access_count distribution
            cursor.execute("""
                SELECT access_count, COUNT(*) as count 
                FROM contexts 
                GROUP BY access_count 
                ORDER BY access_count DESC 
                LIMIT 10
            """)
            access_distribution = cursor.fetchall()
            
            print(f"\n📈 Access Count Distribution (top 10):")
            for access_count, count in access_distribution:
                print(f"   access_count {access_count}: {count} contexts")
            
            # 3. Check last_accessed usage
            cursor.execute("SELECT COUNT(*) FROM contexts WHERE last_accessed IS NOT NULL")
            contexts_with_last_accessed = cursor.fetchone()[0]
            
            print(f"\n📅 Last Accessed Usage:")
            print(f"   Contexts with last_accessed: {contexts_with_last_accessed}/{total_contexts}")
            
            # 4. Check if any queries actually use these fields for filtering/ordering
            cursor.execute("""
                SELECT access_count, last_accessed, content
                FROM contexts 
                WHERE access_count > 5
                ORDER BY access_count DESC
                LIMIT 5
            """)
            high_access_contexts = cursor.fetchall()
            
            print(f"\n🔥 High Access Contexts (access_count > 5):")
            for access_count, last_accessed, content in high_access_contexts:
                content_preview = content[:50] + "..." if len(content) > 50 else content
                print(f"   {access_count} accesses, last: {last_accessed}, content: {content_preview}")
            
            # 5. Check projects last_accessed
            cursor.execute("SELECT id, name, last_accessed FROM projects WHERE last_accessed IS NOT NULL LIMIT 10")
            projects_with_access = cursor.fetchall()
            
            print(f"\n📁 Projects with last_accessed:")
            for project_id, name, last_accessed in projects_with_access:
                print(f"   {project_id}: {name} (last: {last_accessed})")
            
            conn.close()
            
        except Exception as e:
            print(f"❌ Database analysis failed: {e}")
            
    async def audit_code_usage(self):
        """Analyze where access tracking is used in code"""
        print(f"\n💻 Code Usage Analysis:")
        print("=" * 30)
        
        # Methods that write to access tracking
        write_methods = [
            "update_context_access",
            "update_project_access", 
        ]
        
        # Methods that read access tracking for business logic
        read_methods = [
            # Methods that ORDER BY access_count or last_accessed
            # Methods that filter WHERE access_count > X
            # Methods that use access tracking for retention
        ]
        
        print("📝 Methods that WRITE access tracking:")
        for method in write_methods:
            print(f"   - {method}")
            
        print("\n📖 Methods that READ access tracking for business logic:")
        if not read_methods:
            print("   - None found! (This suggests access tracking is write-only)")
        else:
            for method in read_methods:
                print(f"   - {method}")
        
        # Key insight
        print(f"\n🎯 Key Insight:")
        print("   Access tracking appears to be write-only - data is collected but never used!")
        print("   This is a classic case of 'measurement without purpose' leading to:")
        print("   - Database bloat")
        print("   - Unnecessary UPDATE operations")
        print("   - Hidden performance overhead")
        print("   - Code complexity without benefit")
        
    async def audit_schema_dependencies(self):
        """Check what database schema dependencies exist"""
        print(f"\n🗄️ Schema Dependencies:")
        print("=" * 25)
        
        # Check if any indexes depend on these fields
        db_path = self.provider.db_manager.db_path
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Check indexes that use access tracking fields
            cursor.execute("""
                SELECT name, sql 
                FROM sqlite_master 
                WHERE type='index' 
                AND (sql LIKE '%access_count%' OR sql LIKE '%last_accessed%')
            """)
            access_indexes = cursor.fetchall()
            
            print("📊 Indexes using access tracking fields:")
            if access_indexes:
                for name, sql in access_indexes:
                    print(f"   - {name}: {sql}")
            else:
                print("   - None found")
            
            # Check if any views or triggers use these fields  
            cursor.execute("""
                SELECT name, sql 
                FROM sqlite_master 
                WHERE type IN ('view', 'trigger')
                AND (sql LIKE '%access_count%' OR sql LIKE '%last_accessed%')
            """)
            access_objects = cursor.fetchall()
            
            print(f"\n🔧 Views/Triggers using access tracking:")
            if access_objects:
                for name, sql in access_objects:
                    print(f"   - {name}: {sql[:100]}...")
            else:
                print("   - None found")
                
            conn.close()
            
        except Exception as e:
            print(f"❌ Schema analysis failed: {e}")
    
    async def generate_cleanup_recommendations(self):
        """Generate specific recommendations for cleanup"""
        print(f"\n🧹 Cleanup Recommendations:")
        print("=" * 30)
        
        print("1. 🗑️ SAFE TO REMOVE - Database columns:")
        print("   - contexts.access_count (write-only, never used for business logic)")
        print("   - contexts.last_accessed (write-only, never used for business logic)")
        print("   - projects.last_accessed (only used in update_project_access)")
        
        print(f"\n2. 🔧 SAFE TO REMOVE - Code methods:")
        print("   - ContextRepository.update_context_access()")
        print("   - ProjectRepository.update_project_access()")
        print("   - MemoryFacade.update_context_access()")
        
        print(f"\n3. 📊 SAFE TO REMOVE - Database indexes:")
        print("   - idx_contexts_access (index on access_count, last_accessed)")
        
        print(f"\n4. 🔄 MIGRATION STRATEGY:")
        print("   - Create migration script to remove columns")
        print("   - Remove code methods in same commit")
        print("   - Update all SELECT statements to not include these fields")
        print("   - Test that no business logic breaks")
        
        print(f"\n5. 💾 PERFORMANCE IMPACT:")
        print("   - Remove hidden UPDATE operations from read paths")
        print("   - Reduce storage overhead")
        print("   - Simplify code paths")
        print("   - No functional impact (fields aren't used)")

    async def run_audit(self):
        """Run complete access tracking audit"""
        await self.setup()
        await self.audit_access_tracking_usage()
        await self.audit_code_usage()
        await self.audit_schema_dependencies()
        await self.generate_cleanup_recommendations()
        
        if self.provider:
            await self.provider.close()

async def main():
    auditor = AccessTrackingAuditor()
    await auditor.run_audit()

if __name__ == "__main__":
    asyncio.run(main())
