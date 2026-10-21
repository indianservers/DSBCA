# Phase 2 integration boundary

Discuss is explicitly demonstration-only. `/api/v1/discuss/capabilities` reports inference_enabled=false. The composer retains questions only in the current frontend session and never fabricates an AI response.

`app/services/interfaces.py` reserves ConversationProvider.answer(user_id, question). Implement conversation authorization, persistent history, knowledge source/document/version lifecycle, traceable citations, refusal behavior and verified source ingestion when Phase 2 specifications are supplied. The user session and server-side role/ownership framework can be reused.

No vector database, RAG, embeddings, model credentials, document ingestion, production chatbot or regulatory intelligence exists. Admin Knowledge Base, AI Configuration, Document Sources, System Instructions, Chatbot Analytics and Conversations are labeled placeholders. FileStorage and PushProvider interfaces remain available for Phase 3 adapters.
