# Graph Report - nova-backend  (2026-10-09)

## Corpus Check
- 153 files · ~113,721 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 5 file(s) not represented in the graph (top: (none) 2, .mdc 1, .example 1)

## Summary
- 2886 nodes · 6646 edges · 156 communities (78 shown, 78 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 699 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `12354ca5`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- TTSService
- MeetingService
- MeetingSegment
- EndpointDecisionTests
- agent_loop.py
- Conversation
- Tool
- SimpleFinancesService
- AgentLoop
- CommandLineService
- MemoryChunkService
- EmbeddingService
- Mac code agent daemon
- process_supervisor.py
- Update
- MeetingError
- post
- make_update
- GithubService
- build_service
- auth_controller.py
- test_meeting_service.py
- UpdateService
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
- SettingsService
- test_code_service.py
- AuthService
- test_openai_loop.py
- test_auth_service.py
- LiveReply
- SessionManager
- meeting_service.py
- Responsibility
- .completed
- FakeMessage
- Project
- make_update
- BaseDao
- McpServerService
- ResponsibilityService
- ConversationLoopStreamTests
- TranscribeSocketTests
- ReportType
- .run_agent
- test_auth_gate.py
- CodeService
- ToolService
- CurrentModelTests
- FakeDao
- TwilioErrorClassificationTests
- McpServer
- run_migrations.py
- os
- ._artifact_for_tool
- asyncio
- MacShellTests
- recording_meeting
- FakeConversationService
- clamp_spoken
- twilio_service.py
- SpokenTrackTests
- LiveScreenTests
- FakeMcpServerDao
- FakeMeetingDao
- CrudTests
- FakeMessages
- worktree.py
- McpOAuthService
- asr_service.py
- test_coding_service.py
- build_memory_service
- test_responsibility_service.py
- requests
- StreamedSpeechTests
- FailureSpeechTests
- typing
- email_service.py
- test_spoken_reply.py
- FileOperationTests
- ._run_begin
- MemoryInjectionTests
- build_service
- ConversationService
- speech_summary
- .conversation_loop_events
- HttpGateTests
- FakeUpdateService
- test_transcribe_socket_endpointing.py
- auth_service.py
- StatusTextTests
- EndSessionTests
- FakeConversationService
- worker.py
- ._to_dict
- FakeDao
- PromptSourceTests
- ClassificationTests
- ReplyTests
- ASRService
- audio_ws.py
- host_environment_prompt.py
- TwilioConfigurationError
- inbound_sms
- ReportMediumTests
- .split_sms_body
- AuthenticateTests
- WorkingTreeTests
- SpokenProse
- ServiceMethodToolConfig
- TranscriptSegment
- .allowed_sms_senders
- RelayTokenTests
- ProjectResolutionTests
- MirrorTests
- PerformTests
- MeetingChunk
- .iter_sentence_chunks
- GoodbyeTimingTests
- nova_controller.py
- MeetingNotes
- FollowUpTests
- ToolServiceTests
- DemoService
- asr-bench.py
- install.sh
- uninstall.sh
- test_settings_service.py
- package.json
- nova-backend
- _said
- .test_a_live_turn_reads_deltas_then_exposes_the_message
- meeting_socket
- FakeAgentLoop
- FakeClaudeService
- FakeNotesDao
- CLAUDE.md

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
- `AgentLoop` --uses--> `PromptEnums`  [INFERRED]
  src/harness/agent_loop.py → prompting/prompt_enums.py
- `MeetingService` --uses--> `PromptEnums`  [INFERRED]
  src/service/meeting_service.py → prompting/prompt_enums.py
- `_run_turn()` --uses--> `PromptSourceEnum`  [INFERRED]
  src/controller/call_controller.py → prompting/prompt_source_prompt.py
- `chat_stream()` --uses--> `PromptSourceEnum`  [INFERRED]
  src/controller/nova_controller.py → prompting/prompt_source_prompt.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Remote hosting request path** — docs_hosting_firebase_hosting, docs_hosting_cloudflare_tunnel, docs_hosting_bearer_token_login [EXTRACTED 1.00]
- **Mac agent core design principles** — mac_agent_readme_dial_out, mac_agent_readme_sessions_as_threads, mac_agent_readme_git_worktree [EXTRACTED 1.00]

## Communities (156 total, 78 thin omitted)

### Community 0 - "TTSService"
Cohesion: 0.18
Nodes (3): ElevenLabsService, NovaService, TTSService

### Community 2 - "MeetingSegment"
Cohesion: 0.13
Nodes (6): MeetingSegment, ChunkingTests, FinalizeTests, NotesTests, NotesUseNoToolsTests, TranscriptTests

### Community 3 - "EndpointDecisionTests"
Cohesion: 0.10
Nodes (5): endpoint_decision(), _endpoint_scale(), EndpointDecision, silence_budget_ms(), EndpointDecisionTests

### Community 4 - "agent_loop.py"
Cohesion: 0.06
Nodes (17): PromptEnums, PromptSourceEnum, _is_stale(), resolve_sms_conversation(), _run_sms_turn(), ToolUseStarted, TurnStream, ConversationClosedError (+9 more)

### Community 5 - "Conversation"
Cohesion: 0.11
Nodes (3): ConversationDao, Conversation, ThreadResolutionTests

### Community 6 - "Tool"
Cohesion: 0.16
Nodes (4): list_tools(), ToolDao, Tool, FakeToolDao

### Community 7 - "SimpleFinancesService"
Cohesion: 0.11
Nodes (6): SimplApiError, SimplConfigurationError, SimpleFinancesService, response(), SimpleFinancesServiceTest, SimplFinancesToolRegistrationTest

### Community 8 - "AgentLoop"
Cohesion: 0.06
Nodes (5): AgentLoop, persist(), CountingService, FakeConversationService, FakeToolDao

### Community 9 - "CommandLineService"
Cohesion: 0.07
Nodes (3): CommandLineService, BackgroundTests, ForegroundTests

### Community 10 - "MemoryChunkService"
Cohesion: 0.08
Nodes (6): MemoryChunkDao, MemoryChunk, MemoryMatch, MemoryChunkService, ParseChunksTests, RetrievableQueryTests

### Community 12 - "Mac code agent daemon"
Cohesion: 0.06
Nodes (41): Hosting Nova off the home network, Backend environment variables, Bearer token login and sessions, Cloudflare Tunnel (nova-tower), Firebase Hosting frontend, Login rate-limit lockout, MCP OAuth callback, nova_sessions table (+33 more)

### Community 13 - "process_supervisor.py"
Cohesion: 0.11
Nodes (18): _all(), await_ready(), check(), classify(), _entry(), kill_tree(), _log_paths(), pid_alive() (+10 more)

### Community 14 - "Update"
Cohesion: 0.10
Nodes (3): Update, _env_int(), UpdateDeliveryService

### Community 15 - "MeetingError"
Cohesion: 0.12
Nodes (13): delete_meeting(), get_active_meeting(), get_meeting(), get_meeting_segments(), list_meetings(), _meeting_error(), regenerate_notes(), _resolve_meeting_id() (+5 more)

### Community 16 - "post"
Cohesion: 0.07
Nodes (17): logout_all(), adopt_claude_thread(), _authorized(), coding_socket(), coding_status(), get_coding_session(), list_claude_threads(), list_coding_sessions() (+9 more)

### Community 17 - "make_update"
Cohesion: 0.17
Nodes (8): at(), build_service(), CallDeliveryTests, EmailDeliveryTests, make_update(), QuietHoursTests, SettleCallTests, SmsDeliveryTests

### Community 18 - "GithubService"
Cohesion: 0.15
Nodes (4): GithubService, GithubServiceError, _FakeResponse, GithubServiceTests

### Community 19 - "build_service"
Cohesion: 0.09
Nodes (8): build_service(), CreateUpdateTests, FakeConversationDao, FakeProjectDao, FakeUpdateDao, make_update(), ReportTypeTests, ViewingTests

### Community 20 - "auth_controller.py"
Cohesion: 0.11
Nodes (9): _client_ip(), current_session(), list_sessions(), login(), logout(), AuthNotConfigured, BadCredentials, LockedOut (+1 more)

### Community 21 - "test_meeting_service.py"
Cohesion: 0.10
Nodes (6): FakeChunkDao, FakeConversationDao, FakeEmbeddingService, FakeUpdateService, RecoveryTests, ReplyQueue

### Community 24 - "test_memory_chunk_service.py"
Cohesion: 0.11
Nodes (9): build_service(), FakeClaudeResponse, FakeClaudeService, FakeConversationService, FakeEmbeddingService, FakeMemoryChunkDao, FakeTextBlock, FetchMemoryTests (+1 more)

### Community 25 - "settings_controller.py"
Cohesion: 0.11
Nodes (6): get_all_settings(), get_available_models(), get_claude_credits(), ModelSwitchRequest, set_model(), ClaudeCreditsService

### Community 26 - "processes.py"
Cohesion: 0.15
Nodes (16): _all(), await_ready(), check(), _entry(), kill_tree(), _log_paths(), pid_alive(), port_open() (+8 more)

### Community 27 - "call_controller.py"
Cohesion: 0.07
Nodes (16): answer_call(), call_status(), _escape(), mint_relay_token(), _opening_prompt(), relay_socket(), start_turn(), run_after_previous() (+8 more)

### Community 28 - "ClaudeService"
Cohesion: 0.09
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
Cohesion: 0.11
Nodes (4): main(), report(), TwilioService, ConfigurationGuardTests

### Community 34 - "test_code_service.py"
Cohesion: 0.12
Nodes (3): FakeConversationDao, FakeProjectDao, PathContainmentTests

### Community 36 - "test_openai_loop.py"
Cohesion: 0.17
Nodes (7): FakeClient, FakeFunctionCall, FakeResponse, FakeResponsesAPI, FakeTool, FakeToolService, OpenAILoopTests

### Community 37 - "test_auth_service.py"
Cohesion: 0.10
Nodes (4): NovaSessionDao, row_to_session(), NovaSession, RowConversionTests

### Community 39 - "SessionManager"
Cohesion: 0.07
Nodes (12): Config, load_env_file(), Link, _configure_logging(), main(), _run(), _task(), _as_int() (+4 more)

### Community 41 - "Responsibility"
Cohesion: 0.22
Nodes (4): Responsibility, at(), CheckForResponsibilitiesTests, DueTests

### Community 42 - ".completed"
Cohesion: 0.14
Nodes (6): fake_stream(), fake_stream(), fake_stream(), fake_stream(), TurnStreamTests, get_final_message()

### Community 43 - "FakeMessage"
Cohesion: 0.27
Nodes (4): FakeMessage, FakeTextBlock, fake_stream(), ToolTurnSpeechTests

### Community 44 - "Project"
Cohesion: 0.20
Nodes (3): ProjectDao, Project, ProjectService

### Community 45 - "make_update"
Cohesion: 0.16
Nodes (5): ConversationResolutionTests, make_update(), OpeningPromptTests, TwiMLTests, form()

### Community 49 - "ConversationLoopStreamTests"
Cohesion: 0.15
Nodes (5): ConversationLoopStreamTests, fake_stream(), fake_stream(), fake_stream(), EventStreamTests

### Community 51 - "ReportType"
Cohesion: 0.21
Nodes (5): DeliveryStatus, ReportType, EscapingTests, BadgeOnlyTests, UndeliverableTypeTests

### Community 53 - "test_auth_gate.py"
Cohesion: 0.14
Nodes (6): AuthGate, bearer_token(), _header(), is_exempt(), build_app(), ExemptionTests

### Community 55 - "ToolService"
Cohesion: 0.20
Nodes (4): main(), main(), ToolExecutionError, ToolService

### Community 57 - "FakeDao"
Cohesion: 0.18
Nodes (4): CompleteAndRefreshTests, ConnectorFilteringTests, FakeDao, oauth_server()

### Community 58 - "TwilioErrorClassificationTests"
Cohesion: 0.15
Nodes (6): describe_twilio_error(), is_permanent_twilio_error(), SimpleNamespace_Exception, TwilioErrorClassificationTests, reject(), flake()

### Community 59 - "McpServer"
Cohesion: 0.19
Nodes (4): McpServer, _b64url(), _now(), _parse_expiry()

### Community 60 - "run_migrations.py"
Cohesion: 0.17
Nodes (4): main(), migration_files(), _jsonable(), SQLService

### Community 61 - "os"
Cohesion: 0.12
Nodes (5): classify(), _clip(), _resolve_cwd(), run(), _scratch_pair()

### Community 63 - "asyncio"
Cohesion: 0.06
Nodes (20): can_use_tool(), _allowed_origins(), health(), lifespan(), root(), _broadcast(), face_socket(), _callback_page() (+12 more)

### Community 65 - "recording_meeting"
Cohesion: 0.15
Nodes (6): MeetingStatus, CommitSegmentsTests, DeleteMeetingTests, recording_meeting(), StopMeetingTests, UpdateMeetingTests

### Community 66 - "FakeConversationService"
Cohesion: 0.20
Nodes (3): FakeConversationService, FakeMcpService, FakeToolDao

### Community 67 - "clamp_spoken"
Cohesion: 0.25
Nodes (4): deliver(), _clamp(), clamp_spoken(), ClampSpokenTests

### Community 69 - "twilio_service.py"
Cohesion: 0.20
Nodes (3): normalize_phone_number(), SmsRecipientError, NormalizationTests

### Community 70 - "SpokenTrackTests"
Cohesion: 0.23
Nodes (3): FakeToolUseBlock, SpokenTrackTests, fake_stream()

### Community 72 - "FakeMcpServerDao"
Cohesion: 0.17
Nodes (3): build_service(), FakeMcpServerDao, McpServerServiceTests

### Community 75 - "FakeMessages"
Cohesion: 0.28
Nodes (4): build_service(), FakeMessages, RecipientAllowlistTests, SendSmsTests

### Community 76 - "worktree.py"
Cohesion: 0.23
Nodes (7): create(), _git(), remove(), resolve_repo(), slugify(), Workspace, WorktreeError

### Community 77 - "McpOAuthService"
Cohesion: 0.24
Nodes (3): McpOAuthService, _origin(), _path()

### Community 78 - "asr_service.py"
Cohesion: 0.19
Nodes (8): main(), _hotwords(), _load_parakeet(), missing_cuda_libraries(), _nvidia_wheel_dll_dirs(), _platform_default_provider(), _resolve_whisper_device(), _setup_cuda_libraries()

### Community 80 - "build_memory_service"
Cohesion: 0.26
Nodes (5): build_memory_service(), FakeEmbeddingService, FakeMemoryChunkDao, match(), RetrieveContextTests

### Community 81 - "test_responsibility_service.py"
Cohesion: 0.11
Nodes (5): build_service(), FakeProjectDao, FakeResponsibilityDao, FakeUpdateService, WindowTests

### Community 82 - "requests"
Cohesion: 0.27
Nodes (7): backend_url(), close_current_conversation(), fetch_conversation_info(), fetch_health(), fetch_projects(), fetch_tools(), stream_reply()

### Community 83 - "StreamedSpeechTests"
Cohesion: 0.27
Nodes (3): stream(), StreamedSpeechTests, fake_stream()

### Community 85 - "typing"
Cohesion: 0.09
Nodes (7): _flag(), _contained(), make_guard(), _artifact_for(), encode(), _truncate(), _is_prose()

### Community 87 - "test_spoken_reply.py"
Cohesion: 0.16
Nodes (6): _comparable(), is_repeat(), _plain_text(), strip_speak_tags(), IsRepeatTests, StripSpeakTagsTests

### Community 88 - "FileOperationTests"
Cohesion: 0.13
Nodes (3): CodeServiceTestCase, EditTests, FileOperationTests

### Community 89 - "._run_begin"
Cohesion: 0.23
Nodes (6): BeginFlowTests, fake_get(), fake_post(), fake_post(), fake_post(), FakeResponse

### Community 91 - "build_service"
Cohesion: 0.18
Nodes (4): build_service(), FakeProjectDao, RetrievalTests, StartMeetingTests

### Community 92 - "ConversationService"
Cohesion: 0.12
Nodes (4): MessageDao, Message, MessageRole, ConversationService

### Community 94 - ".conversation_loop_events"
Cohesion: 0.17
Nodes (5): PrefetchedConversationTests, fake_stream(), fake_stream(), FakeBlock, FakeMessage

### Community 102 - "FakeConversationService"
Cohesion: 0.20
Nodes (5): FakeConversationService, FakeMessage, FakeTextBlock, FakeToolDao, fake_stream()

### Community 103 - "worker.py"
Cohesion: 0.31
Nodes (6): build_jobs(), _run_check_for_responsibilities(), _run_deliver_pending_updates(), _run_process_conversations(), run_worker(), ScheduledJob

### Community 106 - "FakeDao"
Cohesion: 0.14
Nodes (3): GateTestCase, WebSocketGateTests, FakeDao

### Community 112 - "host_environment_prompt.py"
Cohesion: 0.31
Nodes (3): host_environment_prompt(), _host_kind(), _machine_line()

### Community 114 - "inbound_sms"
Cohesion: 0.32
Nodes (3): _ack(), inbound_sms(), _verified_form()

### Community 117 - "AuthenticateTests"
Cohesion: 0.12
Nodes (3): AuthenticateTests, AuthServiceTestCase, LoginTests

### Community 131 - "nova_controller.py"
Cohesion: 0.07
Nodes (25): suffix_for_mime(), transcribe_serialized(), _canonical_wake_text(), chat_stream(), event_source(), get_nova_power(), get_nova_state(), has_stop_phrase() (+17 more)

### Community 136 - "asr-bench.py"
Cohesion: 0.36
Nodes (4): cut_clips(), default_audio(), load(), main()

### Community 148 - "meeting_socket"
Cohesion: 0.60
Nodes (5): meeting_socket(), capture_loop(), flush_tail(), send(), _transcribe_tail()

## Ambiguous Edges - Review These
- `Voice mode: spoken line vs written answer` → `TTS conversion enhancer prompt (empty)`  [AMBIGUOUS]
  prompting/tts_conversion_enhancer_prompt.txt · relation: conceptually_related_to

## Knowledge Gaps
- **18 isolated node(s):** `type`, `install.sh script`, `uninstall.sh script`, `nova-backend`, `graphify` (+13 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 938 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **78 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Voice mode: spoken line vs written answer` and `TTS conversion enhancer prompt (empty)`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `AgentLoop` connect `AgentLoop` to `.iter_sentence_chunks`, `MeetingService`, `nova_controller.py`, `agent_loop.py`, `Conversation`, `MemoryChunkService`, `UpdateService`, `call_controller.py`, `ClaudeService`, `LiveReply`, `meeting_service.py`, `FakeMessage`, `McpServerService`, `ResponsibilityService`, `ConversationLoopStreamTests`, `ReportType`, `.run_agent`, `ToolService`, `os`, `._artifact_for_tool`, `FakeConversationService`, `SpokenTrackTests`, `LiveScreenTests`, `StreamedSpeechTests`, `FailureSpeechTests`, `MemoryInjectionTests`, `ConversationService`, `.conversation_loop_events`, `FakeConversationService`?**
  _High betweenness centrality (0.134) - this node is a cross-community bridge._
- **Are the 31 inferred relationships involving `AgentLoop` (e.g. with `PromptEnums` and `PromptSourceEnum`) actually correct?**
  _`AgentLoop` has 31 INFERRED edges - model-reasoned connections that need verification._
- **What connects `type`, `install.sh script`, `uninstall.sh script` to the rest of the system?**
  _18 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `MeetingService` be split into smaller, more focused modules?**
  _Cohesion score 0.0957983193277311 - nodes in this community are weakly interconnected._
- **Why does `ClaudeService` connect `ClaudeService` to `SettingsService`, `MeetingService`, `agent_loop.py`, `.get_model_options`, `AgentLoop`, `.resolve_model`, `meeting_service.py`, `MemoryChunkService`, `.get_available_models`, `CurrentModelTests`, `settings_controller.py`, `ConversationService`?**
  _High betweenness centrality (0.077) - this node is a cross-community bridge._
- **Are the 17 inferred relationships involving `Conversation` (e.g. with `_is_stale()` and `ConversationDao`) actually correct?**
  _`Conversation` has 17 INFERRED edges - model-reasoned connections that need verification._