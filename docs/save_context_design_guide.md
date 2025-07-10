# AI Memory Continuity: Save Context Design Guide

## The Core Challenge

AI assistants naturally default to **episodic documentation** - recording what happened during a conversation - rather than **continuation-ready documentation** - extracting actionable artifacts for future sessions. This tendency stems from their training on conversational data where dialogue summarization is the primary pattern.

**The fundamental principle**: We need maximally passive extraction of what was already said, not active cognitive processes for determining what should happen next. Even seemingly neutral words like "identify" or "determine" can trigger analytical thinking rather than pure documentation.

### Why AI Defaults to Meeting Minutes

**Conversational Training Bias**: LLMs are extensively trained on dialogue patterns where the natural response to "summarize this interaction" is to create a chronological recap of who said what. This creates a strong bias toward process documentation.

**Cognitive Load Asymmetry**: Recording conversation flow requires minimal interpretation - it's essentially transcription. Extracting continuation-ready information requires the AI to:
- Identify which decisions affect future work
- Distinguish between settled and unsettled issues  
- Recognize implicit vs explicit commitments
- Filter signal from noise

**Salience Misalignment**: AI models perceive the conversation itself as the primary artifact, while users need the conversation's *outcomes* preserved. The model treats dialogue as the work product rather than a means to modify an external project state.

## The Hallucination Risk

When instructing AI to focus on "future steps" or "what to do next," there's significant risk of **fabricated planning**. AI may interpret continuation-focused prompts as requests to:
- Predict logical next steps that weren't discussed
- Invent tasks based on general domain knowledge
- Assume user preferences without explicit confirmation
- Generate TODO items from template patterns

### Safe vs Unsafe Framing

**❌ Unsafe (Subtly Prediction-oriented):**
- "Save what needs to be done next" (AI may invent logical tasks)
- "Record the project roadmap" (encourages planning beyond discussed items)
- "Document next steps for continuation" (implies AI should determine steps)
- "Preserve actionable items for future work" (may generate assumed actions)

**✅ Safe (Extraction-oriented):**
- "Document decisions that affect future work"
- "Extract explicitly discussed next actions"  
- "Record what was agreed upon for continuation"
- "Save only the tasks that were specifically mentioned"

## Design Principles for Effective Save Prompts

### 1. Role-Based Cognitive Restructuring

Assign the AI a specific professional identity that naturally prioritizes outcomes over process:

```
You are a Project Continuity Archivist. Your exclusive function is to extract 
and document work artifacts from this session that enable seamless project resumption.
```

This role assignment leverages the model's tendency to adopt professional behavioral patterns, moving it away from conversational assistant mode.

### 2. Explicit Extraction Constraints

Use clear directives that prevent fabrication:

```
EXTRACT, DON'T PREDICT: Document only decisions made, results achieved, 
and steps explicitly discussed in this session
```

This creates a hard boundary between documenting what exists versus inventing what might come next.

### 3. Outcome-Focused Structure

Enforce a template that naturally separates continuation-relevant information:

- **Current State**: Tangible artifacts and their status
- **Key Decisions**: Choices that constrain or enable future work  
- **Mentioned Next Steps**: Tasks explicitly stated during the session
- **Critical Context**: Constraints, requirements, deadlines that affect continuation

### 4. Domain-Agnostic Examples (for general-purpose tools)

Provide concrete illustrations across different work domains to demonstrate the pattern. Note: If you're building a save prompt for a specific domain (e.g., only software development), focus on detailed examples within that domain rather than trying to create a universal prompt.

```
✅ Developer: "Contact form validation implemented: email format checking, 
required field validation, success/error messaging. Key decisions: Client-side 
validation with server confirmation, 5-second timeout for submissions. 
Next: Add CAPTCHA integration, implement form analytics, write unit tests."
```

Examples should demonstrate factual extraction without interpretation or assumption.

### 5. Positive Pattern Reinforcement

Reinforce the correct extraction pattern by contrasting it with conversation-logging patterns. Frame this as "correct vs incorrect" rather than "do vs don't":

```
❌ Conversation logging: "User asked about logo design"
✅ State documentation: "Logo design: green leaf shape, white font"

❌ Process recap: "We discussed several options"
✅ Decision record: "Rejected blue circle, approved organic concept"
```

## Implementation Guidelines

### Prompt Structure

1. **Identity Assignment**: Clear professional role definition
2. **Core Directive**: Extract-only constraint with hallucination prevention
3. **Output Template**: Structured format for continuation-ready information
4. **Domain Examples**: Concrete illustrations of correct extraction
5. **Positive Pattern Reinforcement**: Contrasts showing correct vs incorrect approaches
6. **Visual Structure**: Consider using visual markers (🔒, 📋, ✅) to help AI parse prompt sections, especially in longer instructions

### Testing Approach

**Continuity Success Rate**: Measure how often new sessions can proceed without clarification requests when using only the saved context.

**Hallucination Detection**: Review saved contexts for invented tasks, assumed preferences, or predictions not grounded in session content.

**Domain Coverage**: For general-purpose tools, test across diverse work types (creative, technical, analytical) to ensure pattern generalization. For domain-specific tools, focus on comprehensive testing within your target domain.

## Key Success Metrics

- **Factual Accuracy**: All saved information directly traceable to session content
- **Continuation Readiness**: Saved context enables immediate productive work resumption  
- **Conciseness**: Essential information captured without conversation noise
- **Actionability**: Clear understanding of current state and next steps

## Common Failure Patterns to Address

1. **Process Logging**: "User requested X, AI provided Y" instead of documenting outcomes
2. **Conversation Recap**: Chronological summary instead of state extraction
3. **Future Invention**: Creating plausible but undiscussed next steps
4. **Context Dilution**: Including tangential discussion that doesn't affect continuation

The goal is transforming AI from a conversation transcriber into a project state archivist - preserving the essential continuation data while filtering out the conversational scaffolding used to create it.