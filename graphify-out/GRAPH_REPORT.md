# Graph Report - nova-backend  (2026-10-14)

## Corpus Check
- 159 files · ~121,724 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 5 file(s) not represented in the graph (top: (none) 2, .mdc 1, .example 1)

## Summary
- 3130 nodes · 7218 edges · 151 communities (85 shown, 66 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 758 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `a624660e`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- agent_loop.py
- Conversation
- SimpleFinancesService
- text
- TranscribeSocketTests
- Tool
- CommandLineService
- normalize_phone_number
- .run_agent
- Update
- make_update
- ClaudeService
- GithubService
- build_service
- Nova system prompt (persona)
- MemoryChunkService
- SettingsService
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
- UpdateService
- test_openai_loop.py
- ElevenLabsService
- Project
- NovaSession
- LiveReply
- asyncio
- SessionManager
- __main__.py
- nova_controller.py
- test_meeting_service.py
- test_sms.py
- ScheduledTaskService
- CreateTests
- ResponsibilityService
- Responsibility
- McpOAuthService
- make_update
- build_service
- asr_service.py
- call_controller.py
- McpServerService
- CreateScheduleRequirementTests
- FakeHttp
- test_auth_gate.py
- AuthService
- CodeService
- TwilioErrorClassificationTests
- FakeMessage
- post
- ConversationLoopStreamTests
- ReplyTests
- TTSService
- EndpointDecisionTests
- meeting.py
- os
- chat_stream
- ._artifact_for_tool
- spoken_reply.py
- fastapi
- MacShellTests
- FakeConversationService
- auth_controller.py
- McpServer
- AuthenticateTests
- TwilioService
- HttpGateTests
- AgentLoop
- main.py
- sessions.py
- ASRService
- dict
- SpokenTrackTests
- LiveScreenTests
- FakeMcpServerDao
- FakeMeetingDao
- CrudTests
- ModelListTests
- worktree.py
- BipService
- unittest_mock
- StreamedSpeechTests
- test_coding_service.py
- build_memory_service
- test_responsibility_service.py
- TranscriptSegment
- AsrLock
- build_service
- Mac code agent daemon
- FakeTaskDao
- model/__init__.py
- FailureSpeechTests
- ._run_begin
- auth_service.py
- split_wake_phrase
- test_auth_service.py
- PromptEnums
- .allowed_sms_senders
- conversation_controller.py
- test_asr_filters.py
- FakeDao
- MemoryInjectionTests
- pathlib
- FakeUpdateService
- FakeUpdateService
- host_environment_prompt.py
- update_controller.py
- PromptSourceTests
- EndSessionTests
- worker.py
- asr-bench.py
- Link
- sms_controller.py
- ._to_dict
- FakeDao
- ClassificationTests
- .split_sms_body
- WorkingTreeTests
- AgentLink
- Message
- RelayTokenTests
- MirrorTests
- PerformTests
- .iter_sentence_chunks
- GoodbyeTimingTests
- .conversation_loop_events
- FakeResponse
- CLAUDE.md
- install.sh
- uninstall.sh
- nova-backend

## God Nodes (most connected - your core abstractions)
1. `AgentLoop` - 88 edges
2. `Conversation` - 76 edges
3. `build_service()` - 57 edges
4. `MeetingService` - 52 edges
5. `Responsibility` - 47 edges
6. `CodingService` - 47 edges
7. `Update` - 42 edges
8. `UpdateService` - 42 edges
9. `recording_meeting()` - 40 edges
10. `ToolService` - 39 edges

## Surprising Connections (you probably didn't know these)
- `AgentLoop` --uses--> `PromptEnums`  [INFERRED]
  src/harness/agent_loop.py → prompting/prompt_enums.py
- `MeetingService` --uses--> `PromptEnums`  [INFERRED]
  src/service/meeting_service.py → prompting/prompt_enums.py
- `_run_turn()` --uses--> `PromptSourceEnum`  [INFERRED]
  src/controller/call_controller.py → prompting/prompt_source_prompt.py
- `chat_stream()` --uses--> `PromptSourceEnum`  [INFERRED]
  src/controller/nova_controller.py → prompting/prompt_source_prompt.py
- `transcribe_socket()` --uses--> `PromptSourceEnum`  [INFERRED]
  src/controller/nova_controller.py → prompting/prompt_source_prompt.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Remote access path: Firebase frontend to Cloudflare Tunnel to tower API** — docs_hosting_firebase_hosting, docs_hosting_cloudflare_tunnel, docs_hosting_tower_api [EXTRACTED 0.95]
- **Mac agent core design principles** — mac_agent_readme_dial_out, mac_agent_readme_sessions_as_threads, mac_agent_readme_git_worktree [EXTRACTED 1.00]
- **Persisted-action safety rules across foreground and background agents** — prompting_nova_persona_prompt_confirm_persisted_actions, prompting_nova_persona_prompt_clarify_before_executing, prompting_background_agent_prompt_no_outward_actions [INFERRED 0.85]

## Communities (151 total, 66 thin omitted)

### Community 0 - "agent_loop.py"
Cohesion: 0.12
Nodes (5): MessageRole, TurnStream, ToolService, FakeProjectDao, AgentLoopMcpTests

### Community 1 - "Conversation"
Cohesion: 0.06
Nodes (6): ConversationDao, Conversation, ConversationClosedError, ConversationService, PrefetchedConversationTests, ThreadResolutionTests

### Community 2 - "SimpleFinancesService"
Cohesion: 0.11
Nodes (6): SimplApiError, SimplConfigurationError, SimpleFinancesService, response(), SimpleFinancesServiceTest, SimplFinancesToolRegistrationTest

### Community 3 - "text"
Cohesion: 0.09
Nodes (11): _artifact_for(), encode(), _truncate(), ToolUseStarted, AuthenticationTests, forward(), make_request(), PathTokenRouteTests (+3 more)

### Community 5 - "Tool"
Cohesion: 0.05
Nodes (13): main(), main(), main(), migration_files(), list_tools(), ToolDao, Tool, _jsonable() (+5 more)

### Community 6 - "CommandLineService"
Cohesion: 0.07
Nodes (3): CommandLineService, BackgroundTests, ForegroundTests

### Community 7 - "normalize_phone_number"
Cohesion: 0.31
Nodes (3): normalize_phone_number(), SmsRecipientError, NormalizationTests

### Community 8 - ".run_agent"
Cohesion: 0.07
Nodes (11): BackgroundAgentTests, fake_get_response(), FakeConversationService, FakeMessage, FakeTextBlock, FakeToolDao, FakeUpdateService, ReportTypeTests (+3 more)

### Community 9 - "Update"
Cohesion: 0.08
Nodes (4): Update, EmailService, _env_int(), UpdateDeliveryService

### Community 10 - "make_update"
Cohesion: 0.16
Nodes (8): at(), build_service(), CallDeliveryTests, EmailDeliveryTests, make_update(), QuietHoursTests, SettleCallTests, SmsDeliveryTests

### Community 11 - "ClaudeService"
Cohesion: 0.07
Nodes (4): _env_flag(), ClaudeService, GenerationKwargsTests, ClaudeServiceMcpKwargsTests

### Community 12 - "GithubService"
Cohesion: 0.15
Nodes (4): GithubService, GithubServiceError, _FakeResponse, GithubServiceTests

### Community 13 - "build_service"
Cohesion: 0.09
Nodes (8): build_service(), CreateUpdateTests, FakeConversationDao, FakeProjectDao, FakeUpdateDao, make_update(), ReportTypeTests, ViewingTests

### Community 14 - "Nova system prompt (persona)"
Cohesion: 0.07
Nodes (28): Hosting Nova off the home network, Backend environment variables, Cloudflare Tunnel (nova-tower, cloudflared), Firebase Hosting frontend (nova-voice-nd.web.app), Infobip SMS integration (/sms/inbound), Failed-login lockout policy, Mac coding agent (/ws/coding), MCP OAuth callback (+20 more)

### Community 15 - "MemoryChunkService"
Cohesion: 0.07
Nodes (7): MemoryChunkDao, MemoryChunk, MemoryMatch, EmbeddingService, MemoryChunkService, ParseChunksTests, RetrievableQueryTests

### Community 16 - "SettingsService"
Cohesion: 0.10
Nodes (3): _env_flag(), SettingsService, CurrentModelTests

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

### Community 27 - "FileOperationTests"
Cohesion: 0.09
Nodes (3): EditTests, FileOperationTests, PathContainmentTests

### Community 28 - "CodingSession"
Cohesion: 0.14
Nodes (4): CodingSessionDao, CodingEvent, CodingSession, CodingStatus

### Community 29 - "UpdateService"
Cohesion: 0.09
Nodes (12): BaseDao, ProjectDao, ResponsibilityDao, ScheduledTaskDao, UpdateDao, DeliveryStatus, ReportType, UpdateService (+4 more)

### Community 30 - "test_openai_loop.py"
Cohesion: 0.18
Nodes (7): FakeClient, FakeFunctionCall, FakeResponse, FakeResponsesAPI, FakeTool, FakeToolService, OpenAILoopTests

### Community 31 - "ElevenLabsService"
Cohesion: 0.11
Nodes (7): _describe_failure(), ElevenLabsService, ElevenLabsRequestTests, _env(), FallbackTests, refused(), ProviderSelectionTests

### Community 32 - "Project"
Cohesion: 0.09
Nodes (6): Project, ProjectService, CodeServiceTestCase, FakeConversationDao, FakeProjectDao, ProjectResolutionTests

### Community 34 - "LiveReply"
Cohesion: 0.05
Nodes (14): deliver(), _clamp(), clamp_spoken(), LiveReply, _plain_text(), speech_summary(), SpokenProse, strip_speak_tags() (+6 more)

### Community 35 - "asyncio"
Cohesion: 0.14
Nodes (9): _callback_page(), create_mcp_server(), delete_mcp_server(), list_mcp_servers(), mcp_oauth_callback(), start_mcp_oauth(), update_mcp_server(), get_project() (+1 more)

### Community 37 - "__main__.py"
Cohesion: 0.13
Nodes (7): Config, _flag(), load_env_file(), _configure_logging(), main(), _run(), _task()

### Community 38 - "nova_controller.py"
Cohesion: 0.10
Nodes (19): suffix_for_mime(), transcribe_serialized(), _canonical_wake_text(), get_nova_power(), get_nova_state(), has_stop_phrase(), normalize_wake_text(), parse_conversation_id() (+11 more)

### Community 39 - "test_meeting_service.py"
Cohesion: 0.06
Nodes (9): FakeAgentLoop, FakeChunkDao, FakeClaudeService, FakeConversationDao, FakeEmbeddingService, FakeNotesDao, FakeUpdateService, RecoveryTests (+1 more)

### Community 40 - "test_sms.py"
Cohesion: 0.21
Nodes (3): BipConfigurationError, BipRequestError, is_permanent_bip_error()

### Community 41 - "ScheduledTaskService"
Cohesion: 0.12
Nodes (3): TaskStatus, ScheduledTaskService, CurrentTimeTests

### Community 44 - "Responsibility"
Cohesion: 0.15
Nodes (5): Responsibility, at(), CheckForResponsibilitiesTests, DueTests, ReportMediumTests

### Community 45 - "McpOAuthService"
Cohesion: 0.18
Nodes (5): McpOAuthService, _now(), _origin(), _path(), CompleteAndRefreshTests

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

### Community 52 - "FakeHttp"
Cohesion: 0.25
Nodes (4): build_service(), FakeHttp, InfobipRequestTests, SendSmsTests

### Community 53 - "test_auth_gate.py"
Cohesion: 0.15
Nodes (6): AuthGate, bearer_token(), _header(), is_exempt(), build_app(), ExemptionTests

### Community 56 - "TwilioErrorClassificationTests"
Cohesion: 0.15
Nodes (6): describe_twilio_error(), is_permanent_twilio_error(), SimpleNamespace_Exception, TwilioErrorClassificationTests, reject(), flake()

### Community 57 - "FakeMessage"
Cohesion: 0.17
Nodes (7): FakeMessage, FakeTextBlock, fake_stream(), fake_stream(), fake_stream(), StatusTextTests, ToolTurnSpeechTests

### Community 58 - "post"
Cohesion: 0.13
Nodes (13): adopt_claude_thread(), _authorized(), coding_socket(), coding_status(), get_coding_session(), list_claude_threads(), list_coding_sessions(), read_claude_thread() (+5 more)

### Community 59 - "ConversationLoopStreamTests"
Cohesion: 0.15
Nodes (3): ConversationLoopStreamTests, fake_stream(), EventStreamTests

### Community 62 - "EndpointDecisionTests"
Cohesion: 0.10
Nodes (5): endpoint_decision(), _endpoint_scale(), EndpointDecision, silence_budget_ms(), EndpointDecisionTests

### Community 63 - "meeting.py"
Cohesion: 0.09
Nodes (4): MeetingChunkDao, MeetingNotesDao, MeetingChunk, MeetingNotes

### Community 64 - "os"
Cohesion: 0.12
Nodes (7): classify(), _clip(), _resolve_cwd(), run(), _scratch_pair(), OpenAITTS, _requested_provider()

### Community 65 - "chat_stream"
Cohesion: 0.25
Nodes (4): chat_stream(), event_source(), sse_event(), iter_in_thread()

### Community 67 - "spoken_reply.py"
Cohesion: 0.31
Nodes (3): _comparable(), is_repeat(), IsRepeatTests

### Community 70 - "FakeConversationService"
Cohesion: 0.20
Nodes (3): FakeConversationService, FakeMcpService, FakeToolDao

### Community 71 - "auth_controller.py"
Cohesion: 0.17
Nodes (7): _client_ip(), current_session(), list_sessions(), login(), logout(), logout_all(), BadCredentials

### Community 72 - "McpServer"
Cohesion: 0.21
Nodes (3): McpServer, _b64url(), _parse_expiry()

### Community 73 - "AuthenticateTests"
Cohesion: 0.12
Nodes (3): AuthenticateTests, AuthServiceTestCase, LoginTests

### Community 74 - "TwilioService"
Cohesion: 0.07
Nodes (12): backend_url(), close_current_conversation(), fetch_conversation_info(), fetch_health(), fetch_projects(), fetch_tools(), stream_reply(), main() (+4 more)

### Community 76 - "AgentLoop"
Cohesion: 0.06
Nodes (6): PromptSourceEnum, AgentLoop, persist(), CountingService, FakeConversationService, FakeToolDao

### Community 78 - "sessions.py"
Cohesion: 0.18
Nodes (4): _as_int(), _flatten(), _is_prose(), _ms_to_iso()

### Community 80 - "dict"
Cohesion: 0.25
Nodes (3): basic(), InboundSecretTests, RecipientAllowlistTests

### Community 81 - "SpokenTrackTests"
Cohesion: 0.23
Nodes (3): FakeToolUseBlock, SpokenTrackTests, fake_stream()

### Community 82 - "LiveScreenTests"
Cohesion: 0.13
Nodes (4): LiveScreenTests, ScriptedTurnStream, get_final_message(), __iter__()

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
Cohesion: 0.12
Nodes (10): build_memory_service(), FakeConversationService, FakeEmbeddingService, FakeMemoryChunkDao, FakeMessage, FakeTextBlock, FakeToolDao, match() (+2 more)

### Community 93 - "test_responsibility_service.py"
Cohesion: 0.11
Nodes (5): build_service(), FakeProjectDao, FakeResponsibilityDao, FakeUpdateService, WindowTests

### Community 96 - "build_service"
Cohesion: 0.17
Nodes (7): build_service(), FakeProjectDao, ListAndCancelTests, pending(), RecoverStuckTests, RunDueTests, RunTests

### Community 97 - "Mac code agent daemon"
Cohesion: 0.16
Nodes (14): Nova code agent (Mac) README, Anthropic API key stripping, Mac dials out design, Per-session git worktree, Known limits (awake Mac, bounded replay, cache cost), launchd install and menu app, Mac code agent daemon, NOVA_CODE_TOKEN shared secret (+6 more)

### Community 101 - "._run_begin"
Cohesion: 0.23
Nodes (6): BeginFlowTests, fake_get(), fake_post(), fake_post(), fake_post(), FakeResponse

### Community 104 - "split_wake_phrase"
Cohesion: 0.23
Nodes (4): has_wake_phrase(), split_wake_phrase(), SplitWakePhraseTests, WakePhraseTests

### Community 105 - "test_auth_service.py"
Cohesion: 0.13
Nodes (5): row_to_session(), AuthNotConfigured, LockedOut, LockoutTests, RowConversionTests

### Community 109 - "conversation_controller.py"
Cohesion: 0.27
Nodes (5): close_conversation(), get_conversation(), get_conversation_messages(), _parse_uuid(), _project_payload()

### Community 110 - "test_asr_filters.py"
Cohesion: 0.26
Nodes (4): drop_hallucination(), DropHallucinationTests, _segment(), WhisperSegmentFilterTests

### Community 111 - "FakeDao"
Cohesion: 0.23
Nodes (3): ConnectorFilteringTests, FakeDao, oauth_server()

### Community 113 - "pathlib"
Cohesion: 0.20
Nodes (5): _contained(), make_guard(), can_use_tool(), health(), root()

### Community 117 - "host_environment_prompt.py"
Cohesion: 0.31
Nodes (3): host_environment_prompt(), _host_kind(), _machine_line()

### Community 120 - "update_controller.py"
Cohesion: 0.22
Nodes (4): list_unviewed_updates(), list_updates(), mark_all_updates_viewed(), mark_update_viewed()

### Community 125 - "worker.py"
Cohesion: 0.27
Nodes (8): build_jobs(), _recover_stuck_tasks(), _run_check_for_responsibilities(), _run_deliver_pending_updates(), _run_process_conversations(), _run_scheduled_tasks(), run_worker(), ScheduledJob

### Community 126 - "asr-bench.py"
Cohesion: 0.36
Nodes (4): cut_clips(), default_audio(), load(), main()

### Community 128 - "sms_controller.py"
Cohesion: 0.16
Nodes (8): _authorize(), _handle_inbound(), inbound_sms(), inbound_sms_with_path_token(), _is_stale(), _receive(), resolve_sms_conversation(), _run_sms_turn()

### Community 130 - "FakeDao"
Cohesion: 0.14
Nodes (3): GateTestCase, WebSocketGateTests, FakeDao

### Community 153 - ".conversation_loop_events"
Cohesion: 0.10
Nodes (10): fake_stream(), fake_stream(), fake_stream(), fake_stream(), TurnStreamTests, get_final_message(), fake_stream(), fake_stream() (+2 more)

## Ambiguous Edges - Review These
- `TTS conversion enhancer prompt (empty)` → `Voice mode tone guidelines`  [AMBIGUOUS]
  prompting/tts_conversion_enhancer_prompt.txt · relation: conceptually_related_to

## Knowledge Gaps
- **21 isolated node(s):** `install.sh script`, `uninstall.sh script`, `nova-backend`, `graphify`, `agent_loop.py core tool-calling loop` (+16 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1012 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **66 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `TTS conversion enhancer prompt (empty)` and `Voice mode tone guidelines`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `AgentLoop` connect `AgentLoop` to `sms_controller.py`, `agent_loop.py`, `Conversation`, `Tool`, `.run_agent`, `ClaudeService`, `Message`, `MemoryChunkService`, `.iter_sentence_chunks`, `.conversation_loop_events`, `MeetingService`, `UpdateService`, `LiveReply`, `nova_controller.py`, `ScheduledTaskService`, `ResponsibilityService`, `call_controller.py`, `McpServerService`, `FakeMessage`, `ConversationLoopStreamTests`, `os`, `._artifact_for_tool`, `FakeConversationService`, `SpokenTrackTests`, `LiveScreenTests`, `StreamedSpeechTests`, `build_memory_service`, `FailureSpeechTests`, `PromptEnums`, `MemoryInjectionTests`?**
  _High betweenness centrality (0.110) - this node is a cross-community bridge._
- **Are the 33 inferred relationships involving `AgentLoop` (e.g. with `PromptEnums` and `PromptSourceEnum`) actually correct?**
  _`AgentLoop` has 33 INFERRED edges - model-reasoned connections that need verification._
- **What connects `install.sh script`, `uninstall.sh script`, `nova-backend` to the rest of the system?**
  _21 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `agent_loop.py` be split into smaller, more focused modules?**
  _Cohesion score 0.12473572938689217 - nodes in this community are weakly interconnected._
- **Why does `ClaudeService` connect `ClaudeService` to `agent_loop.py`, `AgentLoop`, `Message`, `.get_available_models`, `SettingsService`, `MemoryChunkService`, `settings_controller.py`, `MeetingService`, `UpdateService`?**
  _High betweenness centrality (0.058) - this node is a cross-community bridge._
- **Are the 17 inferred relationships involving `Conversation` (e.g. with `_is_stale()` and `ConversationDao`) actually correct?**
  _`Conversation` has 17 INFERRED edges - model-reasoned connections that need verification._