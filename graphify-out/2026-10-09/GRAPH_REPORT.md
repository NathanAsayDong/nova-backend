# Graph Report - nova-backend  (2026-10-08)

## Corpus Check
- 153 files · ~111,996 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 5 file(s) not represented in the graph (top: (none) 2, .mdc 1, .example 1)

## Summary
- 2856 nodes · 6566 edges · 146 communities (75 shown, 71 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 695 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- ASR Audio Checks
- Meeting DAO
- Meeting Chunking
- Transcription Service
- Core Imports and API
- Conversation DAO
- Tool Registration Scripts
- Simpl Finances Service
- Agent Loop
- Command Line Service
- Memory Chunk DAO
- Meeting Chunk Search
- Hosting and Login Docs
- Process Supervisor
- Update Delivery
- Meeting Controller
- Coding Controller
- Call Delivery Tests
- GitHub Service
- Create Update Tests
- Auth Controller
- Meeting Service Tests
- Update DAO
- Coding Service
- Memory Chunk Tests
- Settings Controller
- Mac Agent Processes
- Twilio Call Webhooks
- Claude Service
- Coding Session DAO
- Cursor Service
- Conversation Controller
- Call Setup Preflight
- Settings Service
- Code Service Tests
- Auth Service
- OpenAI Loop Tests
- Nova Session DAO
- Live Reply Streaming
- Mac Claude Sessions
- Mac Agent Config
- Responsibility Model
- Turn Stream
- Speech Floor Tests
- Project DAO
- Call Conversation Tests
- Base DAO
- MCP Server DAO
- Responsibility Service
- Conversation Stream Tests
- Transcribe Socket Tests
- Report Types
- Background Agent
- Auth Gate
- Code Service
- Spoken Line Watcher
- Model Selection
- MCP OAuth Tests
- Twilio Errors
- MCP Server Model
- Community 60
- Community 61
- Community 62
- Community 63
- Community 64
- Community 65
- Community 66
- Community 67
- Community 69
- Community 70
- Community 71
- Community 72
- Community 73
- Community 74
- Community 75
- Community 76
- Community 77
- Community 78
- Community 79
- Community 80
- Community 81
- Community 82
- Community 83
- Community 84
- Community 85
- Community 86
- Community 87
- Community 88
- Community 89
- Community 90
- Community 91
- Community 92
- Community 93
- Community 94
- Community 95
- Community 96
- Community 97
- Community 98
- Community 100
- Community 101
- Community 102
- Community 103
- Community 105
- Community 106
- Community 107
- Community 108
- Community 109
- Community 110
- Community 111
- Community 112
- Community 113
- Community 114
- Community 115
- Community 116
- Community 117
- Community 118
- Community 119
- Community 120
- Community 121
- Community 123
- Community 124
- Community 125
- Community 126
- Community 127
- Community 128
- Community 129
- Community 130
- Community 131
- Community 132
- Community 134
- Community 135
- Community 136
- Community 138
- Community 140
- Community 142
- Community 143

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
- `transcribe_socket()` --uses--> `PromptSourceEnum`  [INFERRED]
  src/controller/nova_controller.py → prompting/prompt_source_prompt.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Remote hosting request path** — docs_hosting_firebase_hosting, docs_hosting_cloudflare_tunnel, docs_hosting_bearer_token_login [EXTRACTED 1.00]
- **Mac agent core design principles** — mac_agent_readme_dial_out, mac_agent_readme_sessions_as_threads, mac_agent_readme_git_worktree [EXTRACTED 1.00]

## Communities (146 total, 71 thin omitted)

### Community 0 - "ASR Audio Checks"
Cohesion: 0.05
Nodes (12): main(), AsrLock, ASRService, missing_cuda_libraries(), _nvidia_wheel_dll_dirs(), _platform_default_provider(), _resolve_whisper_device(), _setup_cuda_libraries() (+4 more)

### Community 1 - "Meeting DAO"
Cohesion: 0.06
Nodes (3): MeetingDao, Meeting, MeetingService

### Community 2 - "Meeting Chunking"
Cohesion: 0.07
Nodes (17): MeetingSegment, build_service(), ChunkingTests, CommitSegmentsTests, DeleteMeetingTests, FakeProjectDao, FinalizeTests, FollowUpTests (+9 more)

### Community 3 - "Transcription Service"
Cohesion: 0.05
Nodes (22): suffix_for_mime(), transcribe_serialized(), has_stop_phrase(), has_wake_phrase(), normalize_wake_text(), parse_conversation_id(), _partial_is_due(), resolve_chat_request() (+14 more)

### Community 4 - "Core Imports and API"
Cohesion: 0.09
Nodes (11): PromptSourceEnum, chat_stream(), event_source(), sse_event(), _is_stale(), resolve_sms_conversation(), _run_sms_turn(), iter_in_thread() (+3 more)

### Community 5 - "Conversation DAO"
Cohesion: 0.08
Nodes (4): ConversationDao, Conversation, ConversationService, ThreadResolutionTests

### Community 6 - "Tool Registration Scripts"
Cohesion: 0.10
Nodes (9): main(), main(), list_tools(), ToolDao, Tool, ToolExecutionError, ToolService, FakeToolDao (+1 more)

### Community 7 - "Simpl Finances Service"
Cohesion: 0.11
Nodes (6): SimplApiError, SimplConfigurationError, SimpleFinancesService, response(), SimpleFinancesServiceTest, SimplFinancesToolRegistrationTest

### Community 8 - "Agent Loop"
Cohesion: 0.07
Nodes (4): AgentLoop, persist(), _env_flag(), PrefetchedConversationTests

### Community 9 - "Command Line Service"
Cohesion: 0.07
Nodes (3): CommandLineService, BackgroundTests, ForegroundTests

### Community 10 - "Memory Chunk DAO"
Cohesion: 0.07
Nodes (6): MemoryChunkDao, MemoryChunk, MemoryMatch, MemoryChunkService, ParseChunksTests, RetrievableQueryTests

### Community 11 - "Meeting Chunk Search"
Cohesion: 0.08
Nodes (6): MeetingChunkDao, MeetingNotesDao, MeetingChunk, MeetingNotes, MeetingStatus, EmbeddingService

### Community 12 - "Hosting and Login Docs"
Cohesion: 0.06
Nodes (41): Hosting Nova off the home network, Backend environment variables, Bearer token login and sessions, Cloudflare Tunnel (nova-tower), Firebase Hosting frontend, Login rate-limit lockout, MCP OAuth callback, nova_sessions table (+33 more)

### Community 13 - "Process Supervisor"
Cohesion: 0.11
Nodes (18): _all(), await_ready(), check(), classify(), _entry(), kill_tree(), _log_paths(), pid_alive() (+10 more)

### Community 14 - "Update Delivery"
Cohesion: 0.12
Nodes (3): Update, _env_int(), UpdateDeliveryService

### Community 15 - "Meeting Controller"
Cohesion: 0.09
Nodes (19): transcribe_segments_serialized(), delete_meeting(), get_active_meeting(), get_meeting(), get_meeting_segments(), list_meetings(), _meeting_error(), meeting_socket() (+11 more)

### Community 16 - "Coding Controller"
Cohesion: 0.07
Nodes (18): adopt_claude_thread(), _authorized(), coding_socket(), coding_status(), get_coding_session(), list_claude_threads(), list_coding_sessions(), read_claude_thread() (+10 more)

### Community 17 - "Call Delivery Tests"
Cohesion: 0.17
Nodes (8): at(), build_service(), CallDeliveryTests, EmailDeliveryTests, make_update(), QuietHoursTests, SettleCallTests, SmsDeliveryTests

### Community 18 - "GitHub Service"
Cohesion: 0.15
Nodes (4): GithubService, GithubServiceError, _FakeResponse, GithubServiceTests

### Community 19 - "Create Update Tests"
Cohesion: 0.08
Nodes (8): build_service(), CreateUpdateTests, FakeConversationDao, FakeProjectDao, FakeUpdateDao, make_update(), ReportTypeTests, ViewingTests

### Community 20 - "Auth Controller"
Cohesion: 0.09
Nodes (11): _client_ip(), current_session(), list_sessions(), login(), logout(), logout_all(), AuthNotConfigured, BadCredentials (+3 more)

### Community 21 - "Meeting Service Tests"
Cohesion: 0.06
Nodes (9): FakeAgentLoop, FakeChunkDao, FakeClaudeService, FakeConversationDao, FakeEmbeddingService, FakeNotesDao, FakeUpdateService, RecoveryTests (+1 more)

### Community 24 - "Memory Chunk Tests"
Cohesion: 0.11
Nodes (9): build_service(), FakeClaudeResponse, FakeClaudeService, FakeConversationService, FakeEmbeddingService, FakeMemoryChunkDao, FakeTextBlock, FetchMemoryTests (+1 more)

### Community 25 - "Settings Controller"
Cohesion: 0.09
Nodes (6): get_all_settings(), get_available_models(), get_claude_credits(), ModelSwitchRequest, set_model(), ClaudeCreditsService

### Community 26 - "Mac Agent Processes"
Cohesion: 0.15
Nodes (16): _all(), await_ready(), check(), _entry(), kill_tree(), _log_paths(), pid_alive(), port_open() (+8 more)

### Community 27 - "Twilio Call Webhooks"
Cohesion: 0.08
Nodes (15): answer_call(), call_status(), _escape(), mint_relay_token(), _opening_prompt(), relay_socket(), start_turn(), run_after_previous() (+7 more)

### Community 28 - "Claude Service"
Cohesion: 0.11
Nodes (3): ClaudeService, GenerationKwargsTests, ClaudeServiceMcpKwargsTests

### Community 29 - "Coding Session DAO"
Cohesion: 0.15
Nodes (4): CodingSessionDao, CodingEvent, CodingSession, __iter__()

### Community 30 - "Cursor Service"
Cohesion: 0.17
Nodes (4): CursorService, CursorServiceError, CursorServiceTests, _FakeResponse

### Community 31 - "Conversation Controller"
Cohesion: 0.12
Nodes (11): close_conversation(), get_conversation(), get_conversation_messages(), _parse_uuid(), _project_payload(), get_project(), list_projects(), list_unviewed_updates() (+3 more)

### Community 32 - "Call Setup Preflight"
Cohesion: 0.11
Nodes (4): main(), report(), TwilioService, ConfigurationGuardTests

### Community 33 - "Settings Service"
Cohesion: 0.11
Nodes (3): SettingsService, ModelListTests, _ResetsSharedState

### Community 34 - "Code Service Tests"
Cohesion: 0.09
Nodes (5): CodeServiceTestCase, EditTests, FakeConversationDao, FakeProjectDao, PathContainmentTests

### Community 35 - "Auth Service"
Cohesion: 0.13
Nodes (4): AuthService, GateTestCase, AuthServiceTestCase, ConfigurationTests

### Community 36 - "OpenAI Loop Tests"
Cohesion: 0.17
Nodes (7): FakeClient, FakeFunctionCall, FakeResponse, FakeResponsesAPI, FakeTool, FakeToolService, OpenAILoopTests

### Community 40 - "Mac Agent Config"
Cohesion: 0.13
Nodes (7): Config, _flag(), load_env_file(), _configure_logging(), main(), _run(), _task()

### Community 41 - "Responsibility Model"
Cohesion: 0.18
Nodes (4): Responsibility, at(), CheckForResponsibilitiesTests, DueTests

### Community 42 - "Turn Stream"
Cohesion: 0.10
Nodes (7): ToolUseStarted, TurnStream, fake_stream(), fake_stream(), fake_stream(), TurnStreamTests, get_final_message()

### Community 43 - "Speech Floor Tests"
Cohesion: 0.27
Nodes (4): FakeMessage, FakeTextBlock, fake_stream(), ToolTurnSpeechTests

### Community 44 - "Project DAO"
Cohesion: 0.18
Nodes (3): ProjectDao, Project, ProjectService

### Community 45 - "Call Conversation Tests"
Cohesion: 0.16
Nodes (5): ConversationResolutionTests, make_update(), OpeningPromptTests, TwiMLTests, form()

### Community 49 - "Conversation Stream Tests"
Cohesion: 0.15
Nodes (5): ConversationLoopStreamTests, fake_stream(), fake_stream(), fake_stream(), EventStreamTests

### Community 51 - "Report Types"
Cohesion: 0.22
Nodes (5): DeliveryStatus, ReportType, EscapingTests, BadgeOnlyTests, UndeliverableTypeTests

### Community 53 - "Auth Gate"
Cohesion: 0.15
Nodes (6): AuthGate, bearer_token(), _header(), is_exempt(), build_app(), ExemptionTests

### Community 57 - "MCP OAuth Tests"
Cohesion: 0.16
Nodes (5): CompleteAndRefreshTests, fake_post(), ConnectorFilteringTests, FakeDao, oauth_server()

### Community 58 - "Twilio Errors"
Cohesion: 0.15
Nodes (6): describe_twilio_error(), is_permanent_twilio_error(), SimpleNamespace_Exception, TwilioErrorClassificationTests, reject(), flake()

### Community 59 - "MCP Server Model"
Cohesion: 0.19
Nodes (4): McpServer, _b64url(), _now(), _parse_expiry()

### Community 60 - "Community 60"
Cohesion: 0.16
Nodes (4): main(), migration_files(), _jsonable(), SQLService

### Community 61 - "Community 61"
Cohesion: 0.18
Nodes (5): classify(), _clip(), _resolve_cwd(), run(), _scratch_pair()

### Community 63 - "Community 63"
Cohesion: 0.13
Nodes (7): can_use_tool(), _allowed_origins(), health(), lifespan(), root(), _broadcast(), face_socket()

### Community 65 - "Community 65"
Cohesion: 0.16
Nodes (4): CountingService, FakeConversationService, FakeToolDao, fake_stream()

### Community 66 - "Community 66"
Cohesion: 0.13
Nodes (8): AgentLoopMcpTests, fake_stream(), fake_stream(), FakeBlock, FakeConversationService, FakeMcpService, FakeMessage, FakeToolDao

### Community 67 - "Community 67"
Cohesion: 0.18
Nodes (6): deliver(), _clamp(), clamp_spoken(), _comparable(), is_repeat(), ClampSpokenTests

### Community 69 - "Community 69"
Cohesion: 0.20
Nodes (3): normalize_phone_number(), SmsRecipientError, NormalizationTests

### Community 70 - "Community 70"
Cohesion: 0.23
Nodes (3): FakeToolUseBlock, SpokenTrackTests, fake_stream()

### Community 71 - "Community 71"
Cohesion: 0.19
Nodes (3): LiveScreenTests, ScriptedTurnStream, get_final_message()

### Community 72 - "Community 72"
Cohesion: 0.17
Nodes (3): build_service(), FakeMcpServerDao, McpServerServiceTests

### Community 75 - "Community 75"
Cohesion: 0.28
Nodes (4): build_service(), FakeMessages, RecipientAllowlistTests, SendSmsTests

### Community 76 - "Community 76"
Cohesion: 0.23
Nodes (7): create(), _git(), remove(), resolve_repo(), slugify(), Workspace, WorktreeError

### Community 77 - "Community 77"
Cohesion: 0.26
Nodes (3): McpOAuthService, _origin(), _path()

### Community 78 - "Community 78"
Cohesion: 0.18
Nodes (7): fake_get_response(), FakeConversationService, FakeMessage, FakeProjectDao, FakeTextBlock, FakeToolDao, FakeUpdateService

### Community 80 - "Community 80"
Cohesion: 0.26
Nodes (5): build_memory_service(), FakeEmbeddingService, FakeMemoryChunkDao, match(), RetrieveContextTests

### Community 81 - "Community 81"
Cohesion: 0.19
Nodes (4): build_service(), FakeProjectDao, FakeUpdateService, WindowTests

### Community 82 - "Community 82"
Cohesion: 0.27
Nodes (7): backend_url(), close_current_conversation(), fetch_conversation_info(), fetch_health(), fetch_projects(), fetch_tools(), stream_reply()

### Community 83 - "Community 83"
Cohesion: 0.27
Nodes (3): stream(), StreamedSpeechTests, fake_stream()

### Community 85 - "Community 85"
Cohesion: 0.19
Nodes (3): _contained(), make_guard(), _is_prose()

### Community 87 - "Community 87"
Cohesion: 0.19
Nodes (5): _callback_page(), delete_mcp_server(), list_mcp_servers(), mcp_oauth_callback(), update_mcp_server()

### Community 89 - "Community 89"
Cohesion: 0.26
Nodes (5): BeginFlowTests, fake_get(), fake_post(), fake_post(), FakeResponse

### Community 91 - "Community 91"
Cohesion: 0.25
Nodes (3): _as_int(), _flatten(), _ms_to_iso()

### Community 93 - "Community 93"
Cohesion: 0.27
Nodes (3): _plain_text(), speech_summary(), SpeechSummaryTests

### Community 102 - "Community 102"
Cohesion: 0.20
Nodes (5): FakeConversationService, FakeMessage, FakeTextBlock, FakeToolDao, fake_stream()

### Community 103 - "Community 103"
Cohesion: 0.31
Nodes (6): build_jobs(), _run_check_for_responsibilities(), _run_deliver_pending_updates(), _run_process_conversations(), run_worker(), ScheduledJob

### Community 111 - "Community 111"
Cohesion: 0.39
Nodes (3): _artifact_for(), encode(), _truncate()

### Community 112 - "Community 112"
Cohesion: 0.32
Nodes (3): host_environment_prompt(), _host_kind(), _machine_line()

### Community 114 - "Community 114"
Cohesion: 0.32
Nodes (3): _ack(), inbound_sms(), _verified_form()

## Ambiguous Edges - Review These
- `Voice mode: spoken line vs written answer` → `TTS conversion enhancer prompt (empty)`  [AMBIGUOUS]
  prompting/tts_conversion_enhancer_prompt.txt · relation: conceptually_related_to

## Knowledge Gaps
- **17 isolated node(s):** `type`, `install.sh script`, `uninstall.sh script`, `nova-backend`, `nova_sessions table` (+12 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 935 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **71 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Voice mode: spoken line vs written answer` and `TTS conversion enhancer prompt (empty)`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `AgentLoop` connect `Agent Loop` to `Community 129`, `Meeting DAO`, `Community 132`, `Core Imports and API`, `Tool Registration Scripts`, `Conversation DAO`, `Memory Chunk DAO`, `Meeting Chunk Search`, `Update DAO`, `Claude Service`, `Live Reply Streaming`, `Speech Floor Tests`, `Base DAO`, `MCP Server DAO`, `Responsibility Service`, `Conversation Stream Tests`, `Report Types`, `Background Agent`, `Community 61`, `Community 62`, `Community 65`, `Community 66`, `Community 70`, `Community 71`, `Community 78`, `Community 83`, `Community 84`, `Community 90`, `Community 92`, `Community 102`?**
  _High betweenness centrality (0.123) - this node is a cross-community bridge._
- **Are the 31 inferred relationships involving `AgentLoop` (e.g. with `PromptEnums` and `PromptSourceEnum`) actually correct?**
  _`AgentLoop` has 31 INFERRED edges - model-reasoned connections that need verification._
- **What connects `type`, `install.sh script`, `uninstall.sh script` to the rest of the system?**
  _17 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `ASR Audio Checks` be split into smaller, more focused modules?**
  _Cohesion score 0.05086071987480438 - nodes in this community are weakly interconnected._
- **Why does `ClaudeService` connect `Claude Service` to `Settings Service`, `Meeting DAO`, `Core Imports and API`, `Community 68`, `Agent Loop`, `Community 104`, `Memory Chunk DAO`, `Meeting Chunk Search`, `Model Selection`, `Settings Controller`, `Community 92`?**
  _High betweenness centrality (0.051) - this node is a cross-community bridge._
- **Are the 17 inferred relationships involving `Conversation` (e.g. with `_is_stale()` and `ConversationDao`) actually correct?**
  _`Conversation` has 17 INFERRED edges - model-reasoned connections that need verification._