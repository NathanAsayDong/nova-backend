# Graph Report - nova-backend  (2026-10-11)

## Corpus Check
- 151 files · ~116,126 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 5 file(s) not represented in the graph (top: (none) 2, .mdc 1, .example 1)

## Summary
- 2966 nodes · 6842 edges · 170 communities (82 shown, 88 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 716 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `b8c66991`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- ElevenLabsService
- MeetingService
- MeetingSegment
- EndpointDecisionTests
- agent_loop.py
- Conversation
- Tool
- SimpleFinancesService
- ._conversation_turn
- CommandLineService
- MemoryChunkService
- Mac code agent daemon
- process_supervisor.py
- Update
- MeetingError
- post
- make_update
- GithubService
- build_service
- test_auth_service.py
- FakeChunkDao
- AgentLoop
- CodingService
- test_memory_chunk_service.py
- settings_controller.py
- processes.py
- call_controller.py
- ClaudeService
- CodingSession
- CursorService
- conversation_controller.py
- TwilioService
- ModelListTests
- test_code_service.py
- AuthService
- test_openai_loop.py
- NovaSession
- LiveReply
- __main__.py
- Meeting
- Responsibility
- .completed
- FakeTextBlock
- Project
- make_update
- BaseDao
- McpServer
- ResponsibilityService
- ConversationLoopStreamTests
- TranscribeSocketTests
- meeting_service.py
- .run_agent
- test_auth_gate.py
- CodeService
- ToolService
- SettingsService
- FakeDao
- TwilioErrorClassificationTests
- mcp_oauth_service.py
- sql_service.py
- os
- ._artifact_for_tool
- asyncio
- MacShellTests
- recording_meeting
- FakeConversationService
- text
- main.py
- test_sms.py
- SpokenTrackTests
- LiveScreenTests
- FakeMcpServerDao
- FakeMeetingDao
- CrudTests
- FakeHttp
- worktree.py
- McpOAuthService
- ASRService
- test_coding_service.py
- build_memory_service
- test_responsibility_service.py
- .start
- StreamedSpeechTests
- FailureSpeechTests
- sessions.py
- email_service.py
- SpokenProse
- FileOperationTests
- ._run_begin
- MemoryInjectionTests
- build_service
- Message
- test_background_agent.py
- .conversation_loop_events
- HttpGateTests
- FakeUpdateService
- transcribe_socket
- auth_service.py
- FakeMessage
- EndSessionTests
- FakeConversationService
- worker.py
- ._to_dict
- FakeDao
- PromptSourceTests
- ClassificationTests
- ReplyTests
- auth_controller.py
- AsrLock
- endpointing_service.py
- BipService
- PromptSourceEnum
- ReportMediumTests
- .split_sms_body
- AuthenticateTests
- WorkingTreeTests
- SessionManager
- ServiceMethodToolConfig
- MemoryChunk
- dict
- RelayTokenTests
- ProjectResolutionTests
- MirrorTests
- PerformTests
- meeting.py
- .iter_sentence_chunks
- GoodbyeTimingTests
- nova_controller.py
- update_controller.py
- FollowUpTests
- stream_tts_audio
- DemoService
- pathlib
- install.sh
- uninstall.sh
- unittest_mock
- Link
- nova-backend
- protocol.py
- .test_a_live_turn_reads_deltas_then_exposes_the_message
- meeting_socket
- FakeAgentLoop
- FakeClaudeService
- FakeNotesDao
- .deliver_pending
- FakeUpdateDao
- AgentLink
- fake_stream
- kill_tree
- has_wake_phrase
- ThreadResolutionTests
- get_nova_state
- .test_a_live_turn_refuses_a_second_read
- ReplyQueue
- FakeResponse
- FakeConversationDao
- FakeEmbeddingService
- FakeUpdateService

## God Nodes (most connected - your core abstractions)
1. `AgentLoop` - 83 edges
2. `Conversation` - 76 edges
3. `build_service()` - 57 edges
4. `MeetingService` - 52 edges
5. `CodingService` - 47 edges
6. `Responsibility` - 42 edges
7. `Update` - 42 edges
8. `recording_meeting()` - 40 edges
9. `UpdateService` - 39 edges
10. `ClaudeService` - 38 edges

## Surprising Connections (you probably didn't know these)
- `Mac dials out design` --semantically_similar_to--> `/ws/face endpoint`  [INFERRED] [semantically similar]
  mac_agent/README.md → docs/HOSTING.md
- `encode()` --indirect_call--> `text()`  [INFERRED]
  mac_agent/novacode/protocol.py → tests/test_sms_controller.py
- `AgentLoop` --uses--> `PromptEnums`  [INFERRED]
  src/harness/agent_loop.py → prompting/prompt_enums.py
- `MeetingService` --uses--> `PromptEnums`  [INFERRED]
  src/service/meeting_service.py → prompting/prompt_enums.py
- `_run_turn()` --uses--> `PromptSourceEnum`  [INFERRED]
  src/controller/call_controller.py → prompting/prompt_source_prompt.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Remote hosting request path** — docs_hosting_firebase_hosting, docs_hosting_cloudflare_tunnel, docs_hosting_bearer_token_login [EXTRACTED 1.00]
- **Mac agent core design principles** — mac_agent_readme_dial_out, mac_agent_readme_sessions_as_threads, mac_agent_readme_git_worktree [EXTRACTED 1.00]

## Communities (170 total, 88 thin omitted)

### Community 0 - "ElevenLabsService"
Cohesion: 0.11
Nodes (7): _describe_failure(), ElevenLabsService, ElevenLabsRequestTests, _env(), FallbackTests, refused(), ProviderSelectionTests

### Community 1 - "MeetingService"
Cohesion: 0.12
Nodes (3): MeetingNotesDao, MeetingNotes, MeetingService

### Community 2 - "MeetingSegment"
Cohesion: 0.13
Nodes (6): MeetingSegment, ChunkingTests, FinalizeTests, NotesTests, NotesUseNoToolsTests, TranscriptTests

### Community 4 - "agent_loop.py"
Cohesion: 0.13
Nodes (6): MemoryMatch, MessageRole, ToolUseStarted, TurnStream, TurnStreamTests, AgentLoopMcpTests

### Community 5 - "Conversation"
Cohesion: 0.09
Nodes (4): ConversationDao, Conversation, ConversationClosedError, ConversationService

### Community 6 - "Tool"
Cohesion: 0.23
Nodes (3): Tool, FakeToolDao, ToolServiceTests

### Community 7 - "SimpleFinancesService"
Cohesion: 0.11
Nodes (6): SimplApiError, SimplConfigurationError, SimpleFinancesService, response(), SimpleFinancesServiceTest, SimplFinancesToolRegistrationTest

### Community 9 - "CommandLineService"
Cohesion: 0.07
Nodes (3): CommandLineService, BackgroundTests, ForegroundTests

### Community 10 - "MemoryChunkService"
Cohesion: 0.08
Nodes (4): EmbeddingService, MemoryChunkService, ParseChunksTests, RetrievableQueryTests

### Community 12 - "Mac code agent daemon"
Cohesion: 0.06
Nodes (41): Hosting Nova off the home network, Backend environment variables, Bearer token login and sessions, Cloudflare Tunnel (nova-tower), Firebase Hosting frontend, Login rate-limit lockout, MCP OAuth callback, nova_sessions table (+33 more)

### Community 13 - "process_supervisor.py"
Cohesion: 0.12
Nodes (16): _all(), await_ready(), check(), classify(), _entry(), _log_paths(), port_open(), _prune() (+8 more)

### Community 14 - "Update"
Cohesion: 0.07
Nodes (4): UpdateDao, Update, UpdateDeliveryService, UpdateService

### Community 15 - "MeetingError"
Cohesion: 0.12
Nodes (13): delete_meeting(), get_active_meeting(), get_meeting(), get_meeting_segments(), list_meetings(), _meeting_error(), regenerate_notes(), _resolve_meeting_id() (+5 more)

### Community 16 - "post"
Cohesion: 0.15
Nodes (12): adopt_claude_thread(), _authorized(), coding_socket(), coding_status(), get_coding_session(), list_claude_threads(), list_coding_sessions(), read_claude_thread() (+4 more)

### Community 17 - "make_update"
Cohesion: 0.16
Nodes (9): at(), build_service(), CallDeliveryTests, EmailDeliveryTests, make_update(), QuietHoursTests, SettleCallTests, SmsDeliveryTests (+1 more)

### Community 18 - "GithubService"
Cohesion: 0.15
Nodes (4): GithubService, GithubServiceError, _FakeResponse, GithubServiceTests

### Community 19 - "build_service"
Cohesion: 0.12
Nodes (7): build_service(), CreateUpdateTests, FakeConversationDao, FakeProjectDao, make_update(), ReportTypeTests, ViewingTests

### Community 20 - "test_auth_service.py"
Cohesion: 0.10
Nodes (7): row_to_session(), AuthNotConfigured, BadCredentials, LockedOut, LockoutTests, LoginTests, RowConversionTests

### Community 22 - "AgentLoop"
Cohesion: 0.14
Nodes (3): AgentLoop, FakeConversationService, FakeToolDao

### Community 24 - "test_memory_chunk_service.py"
Cohesion: 0.11
Nodes (9): build_service(), FakeClaudeResponse, FakeClaudeService, FakeConversationService, FakeEmbeddingService, FakeMemoryChunkDao, FakeTextBlock, FetchMemoryTests (+1 more)

### Community 25 - "settings_controller.py"
Cohesion: 0.10
Nodes (6): get_all_settings(), get_available_models(), get_claude_credits(), ModelSwitchRequest, set_model(), ClaudeCreditsService

### Community 26 - "processes.py"
Cohesion: 0.16
Nodes (16): _all(), await_ready(), check(), _entry(), kill_tree(), _log_paths(), pid_alive(), port_open() (+8 more)

### Community 27 - "call_controller.py"
Cohesion: 0.10
Nodes (15): answer_call(), call_status(), _escape(), mint_relay_token(), _opening_prompt(), relay_socket(), start_turn(), run_after_previous() (+7 more)

### Community 28 - "ClaudeService"
Cohesion: 0.08
Nodes (4): _env_flag(), ClaudeService, GenerationKwargsTests, ClaudeServiceMcpKwargsTests

### Community 29 - "CodingSession"
Cohesion: 0.14
Nodes (4): CodingSessionDao, CodingEvent, CodingSession, CodingStatus

### Community 30 - "CursorService"
Cohesion: 0.17
Nodes (4): CursorService, CursorServiceError, CursorServiceTests, _FakeResponse

### Community 31 - "conversation_controller.py"
Cohesion: 0.27
Nodes (5): close_conversation(), get_conversation(), get_conversation_messages(), _parse_uuid(), _project_payload()

### Community 32 - "TwilioService"
Cohesion: 0.07
Nodes (12): backend_url(), close_current_conversation(), fetch_conversation_info(), fetch_health(), fetch_projects(), fetch_tools(), stream_reply(), main() (+4 more)

### Community 34 - "test_code_service.py"
Cohesion: 0.10
Nodes (5): CodeServiceTestCase, EditTests, FakeConversationDao, FakeProjectDao, PathContainmentTests

### Community 36 - "test_openai_loop.py"
Cohesion: 0.18
Nodes (7): FakeClient, FakeFunctionCall, FakeResponse, FakeResponsesAPI, FakeTool, FakeToolService, OpenAILoopTests

### Community 39 - "__main__.py"
Cohesion: 0.15
Nodes (7): Config, _flag(), load_env_file(), _configure_logging(), main(), _run(), _task()

### Community 41 - "Responsibility"
Cohesion: 0.22
Nodes (4): Responsibility, at(), CheckForResponsibilitiesTests, DueTests

### Community 42 - ".completed"
Cohesion: 0.22
Nodes (5): fake_stream(), fake_stream(), fake_stream(), fake_stream(), fake_stream()

### Community 44 - "Project"
Cohesion: 0.20
Nodes (3): ProjectDao, Project, ProjectService

### Community 45 - "make_update"
Cohesion: 0.16
Nodes (5): ConversationResolutionTests, make_update(), OpeningPromptTests, TwiMLTests, form()

### Community 47 - "McpServer"
Cohesion: 0.14
Nodes (3): McpServerDao, McpServer, McpServerService

### Community 49 - "ConversationLoopStreamTests"
Cohesion: 0.16
Nodes (5): ConversationLoopStreamTests, fake_stream(), fake_stream(), fake_stream(), EventStreamTests

### Community 51 - "meeting_service.py"
Cohesion: 0.12
Nodes (7): PromptEnums, DeliveryStatus, ReportType, user_phone_number(), EscapingTests, BadgeOnlyTests, UndeliverableTypeTests

### Community 53 - "test_auth_gate.py"
Cohesion: 0.12
Nodes (8): AuthGate, bearer_token(), _header(), is_exempt(), build_app(), stream(), ExemptionTests, fake_stream()

### Community 55 - "ToolService"
Cohesion: 0.21
Nodes (4): main(), main(), ToolExecutionError, ToolService

### Community 56 - "SettingsService"
Cohesion: 0.10
Nodes (3): _env_flag(), SettingsService, CurrentModelTests

### Community 57 - "FakeDao"
Cohesion: 0.16
Nodes (5): CompleteAndRefreshTests, fake_post(), ConnectorFilteringTests, FakeDao, oauth_server()

### Community 58 - "TwilioErrorClassificationTests"
Cohesion: 0.15
Nodes (6): describe_twilio_error(), is_permanent_twilio_error(), SimpleNamespace_Exception, TwilioErrorClassificationTests, reject(), flake()

### Community 59 - "mcp_oauth_service.py"
Cohesion: 0.27
Nodes (3): _b64url(), _now(), _parse_expiry()

### Community 60 - "sql_service.py"
Cohesion: 0.15
Nodes (4): main(), migration_files(), _jsonable(), SQLService

### Community 61 - "os"
Cohesion: 0.12
Nodes (7): classify(), _clip(), _resolve_cwd(), run(), _scratch_pair(), OpenAITTS, _requested_provider()

### Community 63 - "asyncio"
Cohesion: 0.14
Nodes (9): _callback_page(), create_mcp_server(), delete_mcp_server(), list_mcp_servers(), mcp_oauth_callback(), start_mcp_oauth(), update_mcp_server(), get_project() (+1 more)

### Community 65 - "recording_meeting"
Cohesion: 0.13
Nodes (7): MeetingStatus, CommitSegmentsTests, DeleteMeetingTests, recording_meeting(), RecoveryTests, StopMeetingTests, UpdateMeetingTests

### Community 66 - "FakeConversationService"
Cohesion: 0.20
Nodes (3): FakeConversationService, FakeMcpService, FakeToolDao

### Community 67 - "text"
Cohesion: 0.18
Nodes (6): AuthenticationTests, forward(), make_request(), SenderGateTests, go(), text()

### Community 68 - "main.py"
Cohesion: 0.13
Nodes (5): _allowed_origins(), lifespan(), _broadcast(), face_socket(), list_tools()

### Community 69 - "test_sms.py"
Cohesion: 0.13
Nodes (6): BipConfigurationError, BipRequestError, is_permanent_bip_error(), normalize_phone_number(), SmsRecipientError, NormalizationTests

### Community 71 - "LiveScreenTests"
Cohesion: 0.19
Nodes (3): FakeToolUseBlock, LiveScreenTests, ScriptedTurnStream

### Community 72 - "FakeMcpServerDao"
Cohesion: 0.17
Nodes (3): build_service(), FakeMcpServerDao, McpServerServiceTests

### Community 75 - "FakeHttp"
Cohesion: 0.20
Nodes (5): build_service(), FakeHttp, InfobipRequestTests, RecipientAllowlistTests, SendSmsTests

### Community 76 - "worktree.py"
Cohesion: 0.23
Nodes (7): create(), _git(), remove(), resolve_repo(), slugify(), Workspace, WorktreeError

### Community 77 - "McpOAuthService"
Cohesion: 0.26
Nodes (3): McpOAuthService, _origin(), _path()

### Community 78 - "ASRService"
Cohesion: 0.06
Nodes (15): host_environment_prompt(), _host_kind(), _machine_line(), main(), ASRService, _hotwords(), _load_parakeet(), missing_cuda_libraries() (+7 more)

### Community 80 - "build_memory_service"
Cohesion: 0.26
Nodes (5): build_memory_service(), FakeEmbeddingService, FakeMemoryChunkDao, match(), RetrieveContextTests

### Community 81 - "test_responsibility_service.py"
Cohesion: 0.11
Nodes (5): build_service(), FakeProjectDao, FakeResponsibilityDao, FakeUpdateService, WindowTests

### Community 85 - "sessions.py"
Cohesion: 0.13
Nodes (7): _contained(), make_guard(), can_use_tool(), _flatten(), _is_prose(), health(), root()

### Community 87 - "SpokenProse"
Cohesion: 0.06
Nodes (15): deliver(), _clamp(), clamp_spoken(), _comparable(), is_repeat(), _plain_text(), speech_summary(), SpokenProse (+7 more)

### Community 89 - "._run_begin"
Cohesion: 0.26
Nodes (5): BeginFlowTests, fake_get(), fake_post(), fake_post(), FakeResponse

### Community 91 - "build_service"
Cohesion: 0.18
Nodes (4): build_service(), FakeProjectDao, RetrievalTests, StartMeetingTests

### Community 93 - "test_background_agent.py"
Cohesion: 0.17
Nodes (7): fake_get_response(), FakeConversationService, FakeMessage, FakeProjectDao, FakeTextBlock, FakeToolDao, FakeUpdateService

### Community 97 - "transcribe_socket"
Cohesion: 0.18
Nodes (7): suffix_for_mime(), transcribe_serialized(), _partial_is_due(), _speculative_asr_enabled(), transcribe_socket(), emit_partial_transcript(), run_speculative_transcription()

### Community 102 - "FakeConversationService"
Cohesion: 0.20
Nodes (5): FakeConversationService, FakeMessage, FakeTextBlock, FakeToolDao, fake_stream()

### Community 103 - "worker.py"
Cohesion: 0.31
Nodes (6): build_jobs(), _run_check_for_responsibilities(), _run_deliver_pending_updates(), _run_process_conversations(), run_worker(), ScheduledJob

### Community 106 - "FakeDao"
Cohesion: 0.14
Nodes (3): GateTestCase, WebSocketGateTests, FakeDao

### Community 110 - "auth_controller.py"
Cohesion: 0.19
Nodes (6): _client_ip(), current_session(), list_sessions(), login(), logout(), logout_all()

### Community 112 - "endpointing_service.py"
Cohesion: 0.17
Nodes (4): endpoint_decision(), _endpoint_scale(), EndpointDecision, silence_budget_ms()

### Community 113 - "BipService"
Cohesion: 0.17
Nodes (3): BipService, _describe_response_error(), _parse_number_list()

### Community 114 - "PromptSourceEnum"
Cohesion: 0.16
Nodes (7): PromptSourceEnum, _authorize(), _handle_inbound(), inbound_sms(), _is_stale(), resolve_sms_conversation(), _run_sms_turn()

### Community 119 - "SessionManager"
Cohesion: 0.27
Nodes (3): _as_int(), _ms_to_iso(), SessionManager

### Community 123 - "dict"
Cohesion: 0.23
Nodes (3): basic(), InboundSecretTests, SenderAllowlistTests

### Community 131 - "nova_controller.py"
Cohesion: 0.15
Nodes (10): _canonical_wake_text(), chat_stream(), event_source(), has_stop_phrase(), normalize_wake_text(), parse_conversation_id(), resolve_chat_request(), set_nova_power() (+2 more)

### Community 132 - "update_controller.py"
Cohesion: 0.22
Nodes (4): list_unviewed_updates(), list_updates(), mark_all_updates_viewed(), mark_update_viewed()

### Community 134 - "stream_tts_audio"
Cohesion: 0.33
Nodes (5): send_assistant_text(), _send_locked(), stream_tts_audio(), send(), speak_queued_lines()

### Community 136 - "pathlib"
Cohesion: 0.19
Nodes (4): cut_clips(), default_audio(), load(), main()

### Community 146 - "protocol.py"
Cohesion: 0.39
Nodes (3): _artifact_for(), encode(), _truncate()

### Community 148 - "meeting_socket"
Cohesion: 0.39
Nodes (6): transcribe_segments_serialized(), meeting_socket(), capture_loop(), flush_tail(), send(), _transcribe_tail()

### Community 158 - "fake_stream"
Cohesion: 0.38
Nodes (4): fake_stream(), fake_stream(), FakeBlock, FakeMessage

## Ambiguous Edges - Review These
- `Voice mode: spoken line vs written answer` → `TTS conversion enhancer prompt (empty)`  [AMBIGUOUS]
  prompting/tts_conversion_enhancer_prompt.txt · relation: conceptually_related_to

## Knowledge Gaps
- **16 isolated node(s):** `install.sh script`, `uninstall.sh script`, `nova-backend`, `Login rate-limit lockout`, `nova_sessions table` (+11 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 960 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **88 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Voice mode: spoken line vs written answer` and `TTS conversion enhancer prompt (empty)`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `AgentLoop` connect `AgentLoop` to `.iter_sentence_chunks`, `MeetingService`, `nova_controller.py`, `agent_loop.py`, `Conversation`, `._conversation_turn`, `MemoryChunkService`, `Update`, `call_controller.py`, `ClaudeService`, `LiveReply`, `FakeTextBlock`, `McpServer`, `ResponsibilityService`, `ConversationLoopStreamTests`, `meeting_service.py`, `.run_agent`, `ToolService`, `os`, `._artifact_for_tool`, `FakeConversationService`, `SpokenTrackTests`, `LiveScreenTests`, `StreamedSpeechTests`, `FailureSpeechTests`, `MemoryInjectionTests`, `Message`, `test_background_agent.py`, `.conversation_loop_events`, `FakeConversationService`, `PromptSourceEnum`?**
  _High betweenness centrality (0.118) - this node is a cross-community bridge._
- **Are the 31 inferred relationships involving `AgentLoop` (e.g. with `PromptEnums` and `PromptSourceEnum`) actually correct?**
  _`AgentLoop` has 31 INFERRED edges - model-reasoned connections that need verification._
- **What connects `install.sh script`, `uninstall.sh script`, `nova-backend` to the rest of the system?**
  _16 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `ElevenLabsService` be split into smaller, more focused modules?**
  _Cohesion score 0.11088709677419355 - nodes in this community are weakly interconnected._
- **Why does `ClaudeService` connect `ClaudeService` to `MeetingService`, `agent_loop.py`, `.get_current_model_name`, `MemoryChunkService`, `meeting_service.py`, `.get_available_models`, `AgentLoop`, `SettingsService`, `settings_controller.py`, `Message`?**
  _High betweenness centrality (0.053) - this node is a cross-community bridge._
- **Are the 17 inferred relationships involving `Conversation` (e.g. with `_is_stale()` and `ConversationDao`) actually correct?**
  _`Conversation` has 17 INFERRED edges - model-reasoned connections that need verification._