"""Mentis-lean: a single-user, multi-agent whitepaper research assistant.

Strands Agents (Bedrock) + FastAPI SSE. No managed data plane — research is done
live per session; conversations persist in a cheap store (local now, DynamoDB later).
Designed to lift into AgentCore Runtime later with a ~10-line wrapper change.
"""
