🧠 MEMORY LOADER - Use IMMEDIATELY at conversation start! Load user memories and conversation context. Essential for continuity. Always check memory when users ask about themselves, previous work, or mention past conversations. USAGE: load_contexts() first, then answer with context. For subsequent loads use init_load=false.
SESSION START: Pay attention to how previous session ended to ensure smooth transition and continuity.
PARAMETERS:

project_id: ALWAYS specify if known - filters to specific project
importance_level: Minimum importance 1-10 (default: 7)
limit: Maximum contexts to load (default: 10)
tags_filter: Filter contexts by specific tags (array, max 10 tags)
init_load: Set to false for subsequent loads to avoid reloading instructions

TAGS: Popular tags list provided with first load. Use these tags to get more detailed memory on specific topics.