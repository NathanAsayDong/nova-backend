# Graph Report - nova-backend  (2026-10-13)

## Corpus Check
- 159 files · ~120,948 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 5 file(s) not represented in the graph (top: (none) 2, .mdc 1, .example 1)

## Summary
- 3109 nodes · 7172 edges · 160 communities (85 shown, 75 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 749 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `5e2e415a`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- agent_loop.py
- Conversation
- SimpleFinancesService
- test_sms_controller.py
- Tool
- CommandLineService
- register_coding_tools.py
- .run_agent
- Update
- make_update
- ClaudeService
- GithubService
- build_service
- Nova system prompt (persona)
- MemoryChunkService
- CurrentModelTests
- UpdateService
- CodingService
- ScheduledTask
- settings_controller.py
- processes.py
- process_supervisor.py
- test_memory_chunk_service.py
- MeetingError
- CursorService
- MeetingService
- FileOperationTests
- CodingSession
- ReportType
- test_openai_loop.py
- TranscribeSocketTests
- Project
- NovaSession
- LiveReply
- asyncio
- .start
- __main__.py
- nova_controller.py
- test_meeting_service.py
- test_sms.py
- ScheduledTaskService
- build_service
- ResponsibilityService
- Responsibility
- McpOAuthService
- make_update
- build_service
- asr_service.py
- call_controller.py
- McpServerService
- .setUp
- FakeHttp
- test_auth_gate.py
- AuthService
- ProjectDao
- TwilioErrorClassificationTests
- FakeTextBlock
- post
- ConversationLoopStreamTests
- FakeMessage
- TTSService
- EndpointDecisionTests
- meeting_service.py
- os
- BaseDao
- ._artifact_for_tool
- test_spoken_reply.py
- ToolService
- MacShellTests
- .conversation_loop_events
- auth_controller.py
- McpServer
- AuthenticateTests
- TwilioService
- HttpGateTests
- AgentLoop
- main.py
- SessionManager
- ASRService
- dict
- SpokenTrackTests
- LiveScreenTests
- FakeMcpServerDao
- FakeMeetingDao
- CrudTests
- SettingsService
- worktree.py
- BipService
- test_settings_service.py
- StreamedSpeechTests
- test_coding_service.py
- build_memory_service
- test_responsibility_service.py
- TranscriptSegment
- AsrLock
- pending
- Mac code agent daemon
- FakeTaskDao
- model/__init__.py
- FailureSpeechTests
- ._run_begin
- email_service.py
- auth_service.py
- split_wake_phrase
- test_auth_service.py
- SpokenProse
- tts_service.py
- .allowed_sms_senders
- conversation_controller.py
- test_asr_filters.py
- FakeDao
- MemoryInjectionTests
- sessions.py
- PathContainmentTests
- speech_summary
- FakeUpdateService
- host_environment_prompt.py
- RunTests
- update_controller.py
- PromptSourceTests
- EndSessionTests
- FakeConversationService
- worker.py
- asr-bench.py
- Link
- sms_controller.py
- ._to_dict
- FakeDao
- ClassificationTests
- protocol.py
- test_code_service.py
- ReportMediumTests
- .split_sms_body
- WorkingTreeTests
- AgentLink
- Message
- RelayTokenTests
- ProjectResolutionTests
- .test_a_live_turn_reads_deltas_then_exposes_the_message
- MirrorTests
- PerformTests
- .iter_sentence_chunks
- GoodbyeTimingTests
- .completed
- .get_current_time
- FakeResponse
- CLAUDE.md
- install.sh
- uninstall.sh
- nova-backend

## God Nodes (most connected - your core abstractions)
1. `AgentLoop` - 86 edges
2. `Conversation` - 76 edges
3. `build_service()` - 57 edges
4. `MeetingService` - 52 edges
5. `CodingService` - 47 edges
6. `Responsibility` - 42 edges
7. `Update` - 42 edges
8. `UpdateService` - 42 edges
9. `recording_meeting()` - 40 edges
10. `ClaudeService` - 38 edges

## Surprising Connections (you probably didn't know these)
- `encode()` --indirect_call--> `text()`  [INFERRED]
  mac_agent/novacode/protocol.py → tests/test_sms_controller.py
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
- **Remote access path: Firebase frontend to Cloudflare Tunnel to tower API** — docs_hosting_firebase_hosting, docs_hosting_cloudflare_tunnel, docs_hosting_tower_api [EXTRACTED 0.95]
- **Mac agent core design principles** — mac_agent_readme_dial_out, mac_agent_readme_sessions_as_threads, mac_agent_readme_git_worktree [EXTRACTED 1.00]
- **Persisted-action safety rules across foreground and background agents** — prompting_nova_persona_prompt_confirm_persisted_actions, prompting_nova_persona_prompt_clarify_before_executing, prompting_background_agent_prompt_no_outward_actions [INFERRED 0.85]

## Communities (160 total, 75 thin omitted)

### Community 0 - "agent_loop.py"
Cohesion: 0.11
Nodes (8): PromptSourceEnum, MessageRole, ToolUseStarted, TurnStream, fake_get_response(), FakeMessage, FakeProjectDao, FakeTextBlock

### Community 1 - "Conversation"
Cohesion: 0.08
Nodes (4): ConversationDao, Conversation, ConversationService, ThreadResolutionTests

### Community 2 - "SimpleFinancesService"
Cohesion: 0.11
Nodes (6): SimplApiError, SimplConfigurationError, SimpleFinancesService, response(), SimpleFinancesServiceTest, SimplFinancesToolRegistrationTest

### Community 3 - "test_sms_controller.py"
Cohesion: 0.10
Nodes (8): AuthenticationTests, forward(), make_request(), PathTokenRouteTests, ReplyTests, SenderGateTests, go(), text()

### Community 5 - "Tool"
Cohesion: 0.15
Nodes (5): ToolDao, Tool, DemoService, FakeToolDao, ToolServiceTests

### Community 6 - "CommandLineService"
Cohesion: 0.07
Nodes (3): CommandLineService, BackgroundTests, ForegroundTests

### Community 7 - "register_coding_tools.py"
Cohesion: 0.11
Nodes (4): main(), migration_files(), _jsonable(), SQLService

### Community 9 - "Update"
Cohesion: 0.10
Nodes (3): Update, _env_int(), UpdateDeliveryService

### Community 10 - "make_update"
Cohesion: 0.16
Nodes (9): at(), build_service(), CallDeliveryTests, EmailDeliveryTests, make_update(), QuietHoursTests, SettleCallTests, SmsDeliveryTests (+1 more)

### Community 11 - "ClaudeService"
Cohesion: 0.09
Nodes (4): _env_flag(), ClaudeService, GenerationKwargsTests, ClaudeServiceMcpKwargsTests

### Community 12 - "GithubService"
Cohesion: 0.15
Nodes (4): GithubService, GithubServiceError, _FakeResponse, GithubServiceTests

### Community 13 - "build_service"
Cohesion: 0.08
Nodes (8): build_service(), CreateUpdateTests, FakeConversationDao, FakeProjectDao, FakeUpdateDao, make_update(), ReportTypeTests, ViewingTests

### Community 14 - "Nova system prompt (persona)"
Cohesion: 0.07
Nodes (28): Hosting Nova off the home network, Backend environment variables, Cloudflare Tunnel (nova-tower, cloudflared), Firebase Hosting frontend (nova-voice-nd.web.app), Infobip SMS integration (/sms/inbound), Failed-login lockout policy, Mac coding agent (/ws/coding), MCP OAuth callback (+20 more)

### Community 15 - "MemoryChunkService"
Cohesion: 0.10
Nodes (4): EmbeddingService, MemoryChunkService, ParseChunksTests, RetrievableQueryTests

### Community 20 - "settings_controller.py"
Cohesion: 0.11
Nodes (6): get_all_settings(), get_available_models(), get_claude_credits(), ModelSwitchRequest, set_model(), ClaudeCreditsService

### Community 21 - "processes.py"
Cohesion: 0.15
Nodes (16): _all(), await_ready(), check(), _entry(), kill_tree(), _log_paths(), pid_alive(), port_open() (+8 more)

### Community 22 - "process_supervisor.py"
Cohesion: 0.11
Nodes (18): _all(), await_ready(), check(), classify(), _entry(), kill_tree(), _log_paths(), pid_alive() (+10 more)

### Community 23 - "test_memory_chunk_service.py"
Cohesion: 0.11
Nodes (9): build_service(), FakeClaudeResponse, FakeClaudeService, FakeConversationService, FakeEmbeddingService, FakeMemoryChunkDao, FakeTextBlock, FetchMemoryTests (+1 more)

### Community 24 - "MeetingError"
Cohesion: 0.09
Nodes (19): transcribe_segments_serialized(), delete_meeting(), get_active_meeting(), get_meeting(), get_meeting_segments(), list_meetings(), _meeting_error(), meeting_socket() (+11 more)

### Community 25 - "CursorService"
Cohesion: 0.17
Nodes (4): CursorService, CursorServiceError, CursorServiceTests, _FakeResponse

### Community 26 - "MeetingService"
Cohesion: 0.06
Nodes (3): MeetingDao, Meeting, MeetingService

### Community 28 - "CodingSession"
Cohesion: 0.14
Nodes (4): CodingSessionDao, CodingEvent, CodingSession, CodingStatus

### Community 29 - "ReportType"
Cohesion: 0.18
Nodes (5): DeliveryStatus, ReportType, EscapingTests, BadgeOnlyTests, UndeliverableTypeTests

### Community 30 - "test_openai_loop.py"
Cohesion: 0.18
Nodes (7): FakeClient, FakeFunctionCall, FakeResponse, FakeResponsesAPI, FakeTool, FakeToolService, OpenAILoopTests

### Community 31 - "TranscribeSocketTests"
Cohesion: 0.05
Nodes (10): _describe_failure(), ElevenLabsService, HostEnvironmentPromptTests, FakeAgentLoop, TranscribeSocketTests, ElevenLabsRequestTests, _env(), FallbackTests (+2 more)

### Community 35 - "asyncio"
Cohesion: 0.14
Nodes (9): _callback_page(), create_mcp_server(), delete_mcp_server(), list_mcp_servers(), mcp_oauth_callback(), start_mcp_oauth(), update_mcp_server(), get_project() (+1 more)

### Community 37 - "__main__.py"
Cohesion: 0.13
Nodes (7): Config, _flag(), load_env_file(), _configure_logging(), main(), _run(), _task()

### Community 38 - "nova_controller.py"
Cohesion: 0.08
Nodes (23): suffix_for_mime(), transcribe_serialized(), _canonical_wake_text(), chat_stream(), event_source(), get_nova_power(), get_nova_state(), has_stop_phrase() (+15 more)

### Community 39 - "test_meeting_service.py"
Cohesion: 0.06
Nodes (9): FakeAgentLoop, FakeChunkDao, FakeClaudeService, FakeConversationDao, FakeEmbeddingService, FakeNotesDao, FakeUpdateService, RecoveryTests (+1 more)

### Community 40 - "test_sms.py"
Cohesion: 0.13
Nodes (6): BipConfigurationError, BipRequestError, is_permanent_bip_error(), normalize_phone_number(), SmsRecipientError, NormalizationTests

### Community 42 - "build_service"
Cohesion: 0.21
Nodes (5): build_service(), CreateTests, FakeProjectDao, FakeUpdateService, soon()

### Community 44 - "Responsibility"
Cohesion: 0.22
Nodes (4): Responsibility, at(), CheckForResponsibilitiesTests, DueTests

### Community 45 - "McpOAuthService"
Cohesion: 0.26
Nodes (3): McpOAuthService, _origin(), _path()

### Community 46 - "make_update"
Cohesion: 0.16
Nodes (5): ConversationResolutionTests, make_update(), OpeningPromptTests, TwiMLTests, form()

### Community 47 - "build_service"
Cohesion: 0.07
Nodes (17): MeetingSegment, build_service(), ChunkingTests, CommitSegmentsTests, DeleteMeetingTests, FakeProjectDao, FinalizeTests, FollowUpTests (+9 more)

### Community 48 - "asr_service.py"
Cohesion: 0.18
Nodes (8): main(), _hotwords(), _load_parakeet(), missing_cuda_libraries(), _nvidia_wheel_dll_dirs(), _platform_default_provider(), _resolve_whisper_device(), _setup_cuda_libraries()

### Community 49 - "call_controller.py"
Cohesion: 0.10
Nodes (15): answer_call(), call_status(), _escape(), mint_relay_token(), _opening_prompt(), relay_socket(), start_turn(), run_after_previous() (+7 more)

### Community 51 - ".setUp"
Cohesion: 0.22
Nodes (3): FakeConversationService, FakeToolDao, FakeUpdateService

### Community 52 - "FakeHttp"
Cohesion: 0.25
Nodes (4): build_service(), FakeHttp, InfobipRequestTests, SendSmsTests

### Community 53 - "test_auth_gate.py"
Cohesion: 0.14
Nodes (6): AuthGate, bearer_token(), _header(), is_exempt(), build_app(), ExemptionTests

### Community 56 - "TwilioErrorClassificationTests"
Cohesion: 0.14
Nodes (6): describe_twilio_error(), is_permanent_twilio_error(), SimpleNamespace_Exception, TwilioErrorClassificationTests, reject(), flake()

### Community 58 - "post"
Cohesion: 0.13
Nodes (13): adopt_claude_thread(), _authorized(), coding_socket(), coding_status(), get_coding_session(), list_claude_threads(), list_coding_sessions(), read_claude_thread() (+5 more)

### Community 59 - "ConversationLoopStreamTests"
Cohesion: 0.16
Nodes (5): ConversationLoopStreamTests, fake_stream(), fake_stream(), fake_stream(), EventStreamTests

### Community 62 - "EndpointDecisionTests"
Cohesion: 0.10
Nodes (5): endpoint_decision(), _endpoint_scale(), EndpointDecision, silence_budget_ms(), EndpointDecisionTests

### Community 63 - "meeting_service.py"
Cohesion: 0.07
Nodes (6): PromptEnums, MeetingChunkDao, MeetingNotesDao, MeetingChunk, MeetingNotes, MeetingStatus

### Community 64 - "os"
Cohesion: 0.16
Nodes (6): classify(), _clip(), _resolve_cwd(), run(), _scratch_pair(), _speculative_asr_enabled()

### Community 67 - "test_spoken_reply.py"
Cohesion: 0.12
Nodes (9): deliver(), _clamp(), clamp_spoken(), _comparable(), is_repeat(), strip_speak_tags(), ClampSpokenTests, IsRepeatTests (+1 more)

### Community 68 - "ToolService"
Cohesion: 0.28
Nodes (4): main(), main(), ToolExecutionError, ToolService

### Community 70 - ".conversation_loop_events"
Cohesion: 0.07
Nodes (10): persist(), PrefetchedConversationTests, AgentLoopMcpTests, fake_stream(), fake_stream(), FakeBlock, FakeConversationService, FakeMcpService (+2 more)

### Community 71 - "auth_controller.py"
Cohesion: 0.17
Nodes (7): _client_ip(), current_session(), list_sessions(), login(), logout(), logout_all(), BadCredentials

### Community 72 - "McpServer"
Cohesion: 0.22
Nodes (3): McpServer, _now(), _parse_expiry()

### Community 73 - "AuthenticateTests"
Cohesion: 0.12
Nodes (3): AuthenticateTests, AuthServiceTestCase, LoginTests

### Community 74 - "TwilioService"
Cohesion: 0.07
Nodes (12): backend_url(), close_current_conversation(), fetch_conversation_info(), fetch_health(), fetch_projects(), fetch_tools(), stream_reply(), main() (+4 more)

### Community 76 - "AgentLoop"
Cohesion: 0.11
Nodes (4): AgentLoop, CountingService, FakeConversationService, FakeToolDao

### Community 77 - "main.py"
Cohesion: 0.12
Nodes (6): _allowed_origins(), health(), lifespan(), _broadcast(), face_socket(), list_tools()

### Community 78 - "SessionManager"
Cohesion: 0.20
Nodes (4): _as_int(), _flatten(), _ms_to_iso(), SessionManager

### Community 80 - "dict"
Cohesion: 0.25
Nodes (3): basic(), InboundSecretTests, RecipientAllowlistTests

### Community 81 - "SpokenTrackTests"
Cohesion: 0.23
Nodes (3): FakeToolUseBlock, SpokenTrackTests, fake_stream()

### Community 83 - "FakeMcpServerDao"
Cohesion: 0.17
Nodes (3): build_service(), FakeMcpServerDao, McpServerServiceTests

### Community 87 - "worktree.py"
Cohesion: 0.23
Nodes (7): create(), _git(), remove(), resolve_repo(), slugify(), Workspace, WorktreeError

### Community 88 - "BipService"
Cohesion: 0.17
Nodes (3): BipService, _describe_response_error(), _parse_number_list()

### Community 90 - "StreamedSpeechTests"
Cohesion: 0.27
Nodes (3): stream(), StreamedSpeechTests, fake_stream()

### Community 92 - "build_memory_service"
Cohesion: 0.26
Nodes (5): build_memory_service(), FakeEmbeddingService, FakeMemoryChunkDao, match(), RetrieveContextTests

### Community 93 - "test_responsibility_service.py"
Cohesion: 0.11
Nodes (5): build_service(), FakeProjectDao, FakeResponsibilityDao, FakeUpdateService, WindowTests

### Community 96 - "pending"
Cohesion: 0.17
Nodes (4): ListAndCancelTests, pending(), RecoverStuckTests, RunDueTests

### Community 97 - "Mac code agent daemon"
Cohesion: 0.16
Nodes (14): Nova code agent (Mac) README, Anthropic API key stripping, Mac dials out design, Per-session git worktree, Known limits (awake Mac, bounded replay, cache cost), launchd install and menu app, Mac code agent daemon, NOVA_CODE_TOKEN shared secret (+6 more)

### Community 99 - "model/__init__.py"
Cohesion: 0.11
Nodes (4): MemoryChunkDao, MemoryChunk, MemoryMatch, ServiceMethodToolConfig

### Community 101 - "._run_begin"
Cohesion: 0.33
Nodes (3): BeginFlowTests, fake_get(), FakeResponse

### Community 104 - "split_wake_phrase"
Cohesion: 0.23
Nodes (4): has_wake_phrase(), split_wake_phrase(), SplitWakePhraseTests, WakePhraseTests

### Community 105 - "test_auth_service.py"
Cohesion: 0.13
Nodes (5): row_to_session(), AuthNotConfigured, LockedOut, LockoutTests, RowConversionTests

### Community 106 - "SpokenProse"
Cohesion: 0.17
Nodes (4): _plain_text(), SpokenProse, _said(), SpokenProseTests

### Community 109 - "conversation_controller.py"
Cohesion: 0.27
Nodes (5): close_conversation(), get_conversation(), get_conversation_messages(), _parse_uuid(), _project_payload()

### Community 110 - "test_asr_filters.py"
Cohesion: 0.26
Nodes (4): drop_hallucination(), DropHallucinationTests, _segment(), WhisperSegmentFilterTests

### Community 111 - "FakeDao"
Cohesion: 0.15
Nodes (7): fake_post(), CompleteAndRefreshTests, fake_post(), fake_post(), ConnectorFilteringTests, FakeDao, oauth_server()

### Community 113 - "sessions.py"
Cohesion: 0.17
Nodes (5): _contained(), make_guard(), can_use_tool(), _is_prose(), root()

### Community 117 - "host_environment_prompt.py"
Cohesion: 0.31
Nodes (3): host_environment_prompt(), _host_kind(), _machine_line()

### Community 120 - "update_controller.py"
Cohesion: 0.22
Nodes (4): list_unviewed_updates(), list_updates(), mark_all_updates_viewed(), mark_update_viewed()

### Community 124 - "FakeConversationService"
Cohesion: 0.20
Nodes (5): FakeConversationService, FakeMessage, FakeTextBlock, FakeToolDao, fake_stream()

### Community 125 - "worker.py"
Cohesion: 0.27
Nodes (8): build_jobs(), _recover_stuck_tasks(), _run_check_for_responsibilities(), _run_deliver_pending_updates(), _run_process_conversations(), _run_scheduled_tasks(), run_worker(), ScheduledJob

### Community 126 - "asr-bench.py"
Cohesion: 0.36
Nodes (4): cut_clips(), default_audio(), load(), main()

### Community 128 - "sms_controller.py"
Cohesion: 0.13
Nodes (9): _authorize(), _handle_inbound(), inbound_sms(), inbound_sms_with_path_token(), _is_stale(), _receive(), resolve_sms_conversation(), _run_sms_turn() (+1 more)

### Community 130 - "FakeDao"
Cohesion: 0.14
Nodes (3): GateTestCase, WebSocketGateTests, FakeDao

### Community 133 - "protocol.py"
Cohesion: 0.39
Nodes (3): _artifact_for(), encode(), _truncate()

### Community 135 - "test_code_service.py"
Cohesion: 0.14
Nodes (4): CodeServiceTestCase, EditTests, FakeConversationDao, FakeProjectDao

### Community 153 - ".completed"
Cohesion: 0.13
Nodes (7): fake_stream(), fake_stream(), fake_stream(), fake_stream(), fake_stream(), TurnStreamTests, get_final_message()

## Ambiguous Edges - Review These
- `TTS conversion enhancer prompt (empty)` → `Voice mode tone guidelines`  [AMBIGUOUS]
  prompting/tts_conversion_enhancer_prompt.txt · relation: conceptually_related_to

## Knowledge Gaps
- **21 isolated node(s):** `install.sh script`, `uninstall.sh script`, `nova-backend`, `graphify`, `agent_loop.py core tool-calling loop` (+16 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1002 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **75 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `TTS conversion enhancer prompt (empty)` and `Voice mode tone guidelines`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `AgentLoop` connect `AgentLoop` to `sms_controller.py`, `agent_loop.py`, `Conversation`, `._conversation_turn`, `.run_agent`, `ClaudeService`, `Message`, `MemoryChunkService`, `UpdateService`, `.iter_sentence_chunks`, `MeetingService`, `ReportType`, `LiveReply`, `nova_controller.py`, `ScheduledTaskService`, `ResponsibilityService`, `call_controller.py`, `McpServerService`, `.setUp`, `FakeTextBlock`, `ConversationLoopStreamTests`, `meeting_service.py`, `os`, `BaseDao`, `._artifact_for_tool`, `ToolService`, `.conversation_loop_events`, `SpokenTrackTests`, `LiveScreenTests`, `StreamedSpeechTests`, `FailureSpeechTests`, `MemoryInjectionTests`, `FakeConversationService`?**
  _High betweenness centrality (0.114) - this node is a cross-community bridge._
- **Are the 32 inferred relationships involving `AgentLoop` (e.g. with `PromptEnums` and `PromptSourceEnum`) actually correct?**
  _`AgentLoop` has 32 INFERRED edges - model-reasoned connections that need verification._
- **What connects `install.sh script`, `uninstall.sh script`, `nova-backend` to the rest of the system?**
  _21 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `agent_loop.py` be split into smaller, more focused modules?**
  _Cohesion score 0.11184939091915837 - nodes in this community are weakly interconnected._
- **Why does `ClaudeService` connect `ClaudeService` to `agent_loop.py`, `AgentLoop`, `Message`, `.resolve_model`, `CurrentModelTests`, `MemoryChunkService`, `settings_controller.py`, `SettingsService`, `MeetingService`, `meeting_service.py`?**
  _High betweenness centrality (0.067) - this node is a cross-community bridge._
- **Are the 17 inferred relationships involving `Conversation` (e.g. with `_is_stale()` and `ConversationDao`) actually correct?**
  _`Conversation` has 17 INFERRED edges - model-reasoned connections that need verification._