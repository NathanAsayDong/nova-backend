# Graph Report - nova-backend  (2026-10-15)

## Corpus Check
- 185 files · ~139,218 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 10 file(s) not represented in the graph (top: (none) 3, .mdc 1, .pbxproj 1)

## Summary
- 3743 nodes · 8600 edges · 176 communities (103 shown, 73 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 901 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `e1ae411c`
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
- UpdateDeliveryService
- make_update
- ClaudeService
- GithubService
- build_service
- Nova system prompt (persona)
- test_memory_injection.py
- CurrentModelTests
- Harness
- CodingService
- ScheduledTask
- settings_controller.py
- processes.py
- process_supervisor.py
- build_service
- MeetingError
- CursorService
- MeetingService
- FileOperationTests
- CodingSession
- Update
- ConversationController
- ElevenLabsService
- unittest
- NovaSession
- LiveReply
- asyncio
- SessionManager
- __main__.py
- nova_controller.py
- test_meeting_service.py
- test_sms.py
- ScheduledTaskService
- build_service
- ResponsibilityService
- Responsibility
- .ensure_fresh
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
- SpeechPlayer
- EndpointDecisionTests
- meeting_service.py
- os
- Rig
- ._artifact_for_tool
- test_spoken_reply.py
- ClientEvent
- MacShellTests
- AppModel
- auth_service.py
- McpServer
- AuthenticateTests
- TwilioService
- HttpGateTests
- AgentLoop
- main.py
- sessions.py
- CapturePurpose
- dict
- SpokenTrackTests
- LiveScreenTests
- FakeMcpServerDao
- FakeMeetingDao
- CrudTests
- SettingsService
- worktree.py
- BipService
- ServerEvent
- StreamedSpeechTests
- AgentBindingTests
- build_memory_service
- test_responsibility_service.py
- ASRService
- GlassesSocketTests
- pending
- Mac code agent daemon
- FakeTaskDao
- ServiceMethodToolConfig
- FailureSpeechTests
- ._run_begin
- NovaSocket
- Keys
- test_auth_service.py
- Sendable
- test_glasses_voice.py
- .ingest
- PreRollBuffer
- test_asr_filters.py
- McpOAuthService
- MemoryInjectionTests
- permissions.py
- HomeView
- BaseDao
- FakeUpdateService
- host_environment_prompt.py
- APIClient
- Foundation
- Earcon
- PromptSourceTests
- EndSessionTests
- ClaudeCreditsService
- worker.py
- pathlib
- Link
- PromptSourceEnum
- ._to_dict
- FakeDao
- ClassificationTests
- MeetingSegment
- CaptureEngine
- FakePlayer
- requests
- .split_sms_body
- WorkingTreeTests
- AudioRouteManager
- .startsWithWakePhrase
- sql_service.py
- SpokenProse
- AuthStore
- RelayTokenTests
- SpeechWakeDetector
- Double
- clamp_spoken
- PerformTests
- speech_summary
- .iter_sentence_chunks
- GoodbyeTimingTests
- .completed
- mcp_server_controller.py
- WakeDetecting
- StatusTextTests
- FakeResponse
- ConversationControllerTests.swift
- CLAUDE.md
- protocol.py
- install.sh
- uninstall.sh
- ReportMediumTests
- nova-backend
- FakeResponsibilityDao
- _said
- .test_a_live_turn_reads_deltas_then_exposes_the_message
- .get_current_time
- DemoService
- CodingStatus

## God Nodes (most connected - your core abstractions)
1. `AgentLoop` - 90 edges
2. `Conversation` - 76 edges
3. `build_service()` - 57 edges
4. `ConversationController` - 53 edges
5. `MeetingService` - 52 edges
6. `ToolService` - 50 edges
7. `Responsibility` - 47 edges
8. `CodingService` - 47 edges
9. `Update` - 42 edges
10. `UpdateService` - 42 edges

## Surprising Connections (you probably didn't know these)
- `Build and test (CLI)` --references--> `ConversationController`  [INFERRED]
  ios/NovaGlasses/README.md → ios/NovaGlasses/NovaGlasses/Conversation/ConversationController.swift
- `Code map` --references--> `WakeDetecting`  [INFERRED]
  ios/NovaGlasses/README.md → ios/NovaGlasses/NovaGlasses/Conversation/Ports.swift
- `Build and test (CLI)` --references--> `TurnDetector`  [INFERRED]
  ios/NovaGlasses/README.md → ios/NovaGlasses/NovaGlasses/Voice/TurnDetector.swift
- `can_use_tool()` --indirect_call--> `root()`  [INFERRED]
  mac_agent/novacode/permissions.py → main.py
- `encode()` --indirect_call--> `text()`  [INFERRED]
  mac_agent/novacode/protocol.py → tests/test_sms_controller.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Remote access path: Firebase frontend to Cloudflare Tunnel to tower API** — docs_hosting_firebase_hosting, docs_hosting_cloudflare_tunnel, docs_hosting_tower_api [EXTRACTED 0.95]
- **Mac agent core design principles** — mac_agent_readme_dial_out, mac_agent_readme_sessions_as_threads, mac_agent_readme_git_worktree [EXTRACTED 1.00]
- **Persisted-action safety rules across foreground and background agents** — prompting_nova_persona_prompt_confirm_persisted_actions, prompting_nova_persona_prompt_clarify_before_executing, prompting_background_agent_prompt_no_outward_actions [INFERRED 0.85]

## Communities (176 total, 73 thin omitted)

### Community 1 - "Conversation"
Cohesion: 0.08
Nodes (5): ConversationDao, Conversation, ConversationService, FakeConversationService, ThreadResolutionTests

### Community 2 - "SimpleFinancesService"
Cohesion: 0.11
Nodes (6): SimplApiError, SimplConfigurationError, SimpleFinancesService, response(), SimpleFinancesServiceTest, SimplFinancesToolRegistrationTest

### Community 3 - "text"
Cohesion: 0.08
Nodes (9): AgentLink, ToolUseStarted, AuthenticationTests, forward(), make_request(), PathTokenRouteTests, SenderGateTests, go() (+1 more)

### Community 5 - "Tool"
Cohesion: 0.07
Nodes (14): main(), main(), ToolDao, Tool, ToolExecutionError, FakeClient, FakeFunctionCall, FakeResponse (+6 more)

### Community 6 - "CommandLineService"
Cohesion: 0.07
Nodes (3): CommandLineService, BackgroundTests, ForegroundTests

### Community 7 - "normalize_phone_number"
Cohesion: 0.31
Nodes (3): normalize_phone_number(), SmsRecipientError, NormalizationTests

### Community 8 - ".run_agent"
Cohesion: 0.10
Nodes (3): BackgroundAgentTests, ReportTypeTests, ResponsibilityRunToolRestrictionTests

### Community 9 - "UpdateDeliveryService"
Cohesion: 0.10
Nodes (4): user_phone_number(), EmailService, _env_int(), UpdateDeliveryService

### Community 10 - "make_update"
Cohesion: 0.15
Nodes (11): at(), BadgeOnlyTests, build_service(), CallDeliveryTests, EmailDeliveryTests, make_update(), QuietHoursTests, SettleCallTests (+3 more)

### Community 11 - "ClaudeService"
Cohesion: 0.11
Nodes (3): ClaudeService, GenerationKwargsTests, ClaudeServiceMcpKwargsTests

### Community 12 - "GithubService"
Cohesion: 0.15
Nodes (4): GithubService, GithubServiceError, _FakeResponse, GithubServiceTests

### Community 13 - "build_service"
Cohesion: 0.08
Nodes (8): build_service(), CreateUpdateTests, FakeConversationDao, FakeProjectDao, FakeUpdateDao, make_update(), ReportTypeTests, ViewingTests

### Community 14 - "Nova system prompt (persona)"
Cohesion: 0.07
Nodes (28): Hosting Nova off the home network, Backend environment variables, Cloudflare Tunnel (nova-tower, cloudflared), Firebase Hosting frontend (nova-voice-nd.web.app), Infobip SMS integration (/sms/inbound), Failed-login lockout policy, Mac coding agent (/ws/coding), MCP OAuth callback (+20 more)

### Community 15 - "test_memory_injection.py"
Cohesion: 0.05
Nodes (14): MemoryChunkDao, MemoryChunk, MemoryMatch, EmbeddingService, MemoryChunkService, FakeClaudeResponse, FakeClaudeService, FakeTextBlock (+6 more)

### Community 17 - "Harness"
Cohesion: 0.08
Nodes (15): LevelSmoother, Snapshot, State, calibrating, cooldown, idle, onset, speaking (+7 more)

### Community 19 - "ScheduledTask"
Cohesion: 0.12
Nodes (4): ScheduledTaskDao, ScheduledTask, FakeProjectDao, FakeUpdateService

### Community 20 - "settings_controller.py"
Cohesion: 0.19
Nodes (4): get_all_settings(), get_available_models(), ModelSwitchRequest, set_model()

### Community 21 - "processes.py"
Cohesion: 0.15
Nodes (16): _all(), await_ready(), check(), _entry(), kill_tree(), _log_paths(), pid_alive(), port_open() (+8 more)

### Community 22 - "process_supervisor.py"
Cohesion: 0.11
Nodes (18): _all(), await_ready(), check(), classify(), _entry(), kill_tree(), _log_paths(), pid_alive() (+10 more)

### Community 23 - "build_service"
Cohesion: 0.12
Nodes (6): build_service(), FakeConversationService, FakeEmbeddingService, FakeMemoryChunkDao, FetchMemoryTests, ProcessConversationsTests

### Community 24 - "MeetingError"
Cohesion: 0.09
Nodes (19): transcribe_segments_serialized(), delete_meeting(), get_active_meeting(), get_meeting(), get_meeting_segments(), list_meetings(), _meeting_error(), meeting_socket() (+11 more)

### Community 25 - "CursorService"
Cohesion: 0.17
Nodes (4): CursorService, CursorServiceError, CursorServiceTests, _FakeResponse

### Community 26 - "MeetingService"
Cohesion: 0.05
Nodes (3): MeetingDao, Meeting, MeetingService

### Community 27 - "FileOperationTests"
Cohesion: 0.09
Nodes (3): EditTests, FileOperationTests, PathContainmentTests

### Community 28 - "CodingSession"
Cohesion: 0.16
Nodes (3): CodingSessionDao, CodingEvent, CodingSession

### Community 29 - "Update"
Cohesion: 0.08
Nodes (6): UpdateDao, DeliveryStatus, ReportType, Update, UpdateService, EscapingTests

### Community 30 - "ConversationController"
Cohesion: 0.16
Nodes (4): Capture, ConversationController, .isEnabled, .wakeWatching

### Community 31 - "ElevenLabsService"
Cohesion: 0.07
Nodes (11): _describe_failure(), ElevenLabsService, NovaService, OpenAITTS, _requested_provider(), TTSService, ElevenLabsRequestTests, _env() (+3 more)

### Community 32 - "unittest"
Cohesion: 0.07
Nodes (9): MessageDao, ProjectDao, Message, Project, ProjectService, CodeServiceTestCase, FakeConversationDao, FakeProjectDao (+1 more)

### Community 35 - "asyncio"
Cohesion: 0.08
Nodes (16): logout_all(), close_conversation(), get_conversation(), get_conversation_messages(), _parse_uuid(), _project_payload(), delete_mcp_server(), start_mcp_oauth() (+8 more)

### Community 37 - "__main__.py"
Cohesion: 0.13
Nodes (7): Config, _flag(), load_env_file(), _configure_logging(), main(), _run(), _task()

### Community 38 - "nova_controller.py"
Cohesion: 0.06
Nodes (27): suffix_for_mime(), transcribe_serialized(), _canonical_wake_text(), chat_stream(), event_source(), get_nova_power(), get_nova_state(), has_stop_phrase() (+19 more)

### Community 39 - "test_meeting_service.py"
Cohesion: 0.06
Nodes (9): FakeAgentLoop, FakeChunkDao, FakeClaudeService, FakeConversationDao, FakeEmbeddingService, FakeNotesDao, FakeUpdateService, RecoveryTests (+1 more)

### Community 40 - "test_sms.py"
Cohesion: 0.21
Nodes (3): BipConfigurationError, BipRequestError, is_permanent_bip_error()

### Community 42 - "build_service"
Cohesion: 0.21
Nodes (4): build_service(), CreateTests, ListAndCancelTests, soon()

### Community 44 - "Responsibility"
Cohesion: 0.19
Nodes (4): Responsibility, at(), CheckForResponsibilitiesTests, DueTests

### Community 45 - ".ensure_fresh"
Cohesion: 0.16
Nodes (4): _b64url(), _now(), _origin(), _path()

### Community 46 - "make_update"
Cohesion: 0.16
Nodes (5): ConversationResolutionTests, make_update(), OpeningPromptTests, TwiMLTests, form()

### Community 47 - "build_service"
Cohesion: 0.08
Nodes (12): build_service(), CommitSegmentsTests, DeleteMeetingTests, FakeProjectDao, FollowUpTests, explode(), NotesTests, recording_meeting() (+4 more)

### Community 48 - "asr_service.py"
Cohesion: 0.19
Nodes (8): main(), _hotwords(), _load_parakeet(), missing_cuda_libraries(), _nvidia_wheel_dll_dirs(), _platform_default_provider(), _resolve_whisper_device(), _setup_cuda_libraries()

### Community 49 - "call_controller.py"
Cohesion: 0.09
Nodes (16): answer_call(), call_status(), _escape(), mint_relay_token(), _opening_prompt(), relay_socket(), start_turn(), run_after_previous() (+8 more)

### Community 52 - "FakeHttp"
Cohesion: 0.20
Nodes (5): build_service(), FakeHttp, InfobipRequestTests, RecipientAllowlistTests, SendSmsTests

### Community 53 - "test_auth_gate.py"
Cohesion: 0.15
Nodes (6): AuthGate, bearer_token(), _header(), is_exempt(), build_app(), ExemptionTests

### Community 56 - "TwilioErrorClassificationTests"
Cohesion: 0.14
Nodes (6): describe_twilio_error(), is_permanent_twilio_error(), SimpleNamespace_Exception, TwilioErrorClassificationTests, reject(), flake()

### Community 57 - "FakeMessage"
Cohesion: 0.27
Nodes (4): FakeMessage, FakeTextBlock, fake_stream(), ToolTurnSpeechTests

### Community 58 - "post"
Cohesion: 0.09
Nodes (17): adopt_claude_thread(), _authorized(), coding_socket(), coding_status(), get_coding_session(), list_claude_threads(), list_coding_sessions(), read_claude_thread() (+9 more)

### Community 59 - "ConversationLoopStreamTests"
Cohesion: 0.15
Nodes (5): ConversationLoopStreamTests, fake_stream(), fake_stream(), fake_stream(), EventStreamTests

### Community 61 - "SpeechPlayer"
Cohesion: 0.09
Nodes (4): MP3StreamDecoder, SpeechPlayer, .isBusy, Stream

### Community 62 - "EndpointDecisionTests"
Cohesion: 0.10
Nodes (4): endpoint_decision(), EndpointDecision, silence_budget_ms(), EndpointDecisionTests

### Community 63 - "meeting_service.py"
Cohesion: 0.12
Nodes (4): MeetingNotesDao, MeetingChunk, MeetingNotes, MeetingStatus

### Community 64 - "os"
Cohesion: 0.11
Nodes (7): classify(), _clip(), _resolve_cwd(), run(), _scratch_pair(), _endpoint_scale(), MirrorTests

### Community 67 - "test_spoken_reply.py"
Cohesion: 0.16
Nodes (6): _comparable(), is_repeat(), _plain_text(), strip_speak_tags(), IsRepeatTests, StripSpeakTagsTests

### Community 68 - "ClientEvent"
Cohesion: 0.11
Nodes (12): ClientEvent, abort, .name, ping, speechPause, speechResume, start, stop (+4 more)

### Community 70 - "AppModel"
Cohesion: 0.13
Nodes (5): AppModel, .api, .baseURL, .serverURLString, .body

### Community 71 - "auth_service.py"
Cohesion: 0.11
Nodes (10): _client_ip(), current_session(), list_sessions(), login(), logout(), AuthNotConfigured, BadCredentials, _hash_token() (+2 more)

### Community 73 - "AuthenticateTests"
Cohesion: 0.12
Nodes (3): AuthenticateTests, AuthServiceTestCase, LockoutTests

### Community 74 - "TwilioService"
Cohesion: 0.09
Nodes (5): main(), report(), TwilioConfigurationError, TwilioService, ConfigurationGuardTests

### Community 75 - "HttpGateTests"
Cohesion: 0.15
Nodes (3): GateTestCase, HttpGateTests, WebSocketGateTests

### Community 76 - "AgentLoop"
Cohesion: 0.04
Nodes (26): AgentLoop, persist(), MessageRole, TurnStream, ToolService, fake_get_response(), FakeConversationService, FakeMessage (+18 more)

### Community 77 - "main.py"
Cohesion: 0.14
Nodes (6): _allowed_origins(), health(), lifespan(), root(), _broadcast(), face_socket()

### Community 78 - "sessions.py"
Cohesion: 0.18
Nodes (4): _as_int(), _flatten(), _is_prose(), _ms_to_iso()

### Community 79 - "CapturePurpose"
Cohesion: 0.09
Nodes (20): Note, Phase, idle, listening, off, speaking, thinking, AudioRole (+12 more)

### Community 80 - "dict"
Cohesion: 0.23
Nodes (3): basic(), InboundSecretTests, SenderAllowlistTests

### Community 81 - "SpokenTrackTests"
Cohesion: 0.23
Nodes (3): FakeToolUseBlock, SpokenTrackTests, fake_stream()

### Community 83 - "FakeMcpServerDao"
Cohesion: 0.17
Nodes (3): build_service(), FakeMcpServerDao, McpServerServiceTests

### Community 86 - "SettingsService"
Cohesion: 0.11
Nodes (3): SettingsService, ModelListTests, _ResetsSharedState

### Community 87 - "worktree.py"
Cohesion: 0.23
Nodes (7): create(), _git(), remove(), resolve_repo(), slugify(), Workspace, WorktreeError

### Community 88 - "BipService"
Cohesion: 0.17
Nodes (3): BipService, _describe_response_error(), _parse_number_list()

### Community 89 - "ServerEvent"
Cohesion: 0.08
Nodes (20): ServerEvent, audioStreamChunk, audioStreamEnd, audioStreamStart, chunkReceived, done, error, followUpStopped (+12 more)

### Community 90 - "StreamedSpeechTests"
Cohesion: 0.27
Nodes (3): stream(), StreamedSpeechTests, fake_stream()

### Community 92 - "build_memory_service"
Cohesion: 0.26
Nodes (5): build_memory_service(), FakeEmbeddingService, FakeMemoryChunkDao, match(), RetrieveContextTests

### Community 93 - "test_responsibility_service.py"
Cohesion: 0.19
Nodes (4): build_service(), FakeProjectDao, FakeUpdateService, WindowTests

### Community 95 - "GlassesSocketTests"
Cohesion: 0.10
Nodes (3): AsrLock, FakeAgentLoop, GlassesSocketTests

### Community 96 - "pending"
Cohesion: 0.22
Nodes (4): pending(), RecoverStuckTests, RunDueTests, RunTests

### Community 97 - "Mac code agent daemon"
Cohesion: 0.16
Nodes (14): Nova code agent (Mac) README, Anthropic API key stripping, Mac dials out design, Per-session git worktree, Known limits (awake Mac, bounded replay, cache cost), launchd install and menu app, Mac code agent daemon, NOVA_CODE_TOKEN shared secret (+6 more)

### Community 101 - "._run_begin"
Cohesion: 0.24
Nodes (6): BeginFlowTests, fake_get(), fake_post(), fake_post(), fake_post(), FakeResponse

### Community 104 - "Keys"
Cohesion: 0.09
Nodes (19): Keys, assistantText, bytes, chunkBase64, client, code, conversationId, count (+11 more)

### Community 105 - "test_auth_service.py"
Cohesion: 0.20
Nodes (3): row_to_session(), LoginTests, RowConversionTests

### Community 106 - "Sendable"
Cohesion: 0.14
Nodes (10): Cancellable, Handle, MainScheduler, NovaSocketing, Scheduling, SocketConnectionState, connected, connecting (+2 more)

### Community 107 - "test_glasses_voice.py"
Cohesion: 0.10
Nodes (4): audio_file_bytes(), is_raw_pcm(), _pcm_params(), AudioFileBytesTests

### Community 109 - "PreRollBuffer"
Cohesion: 0.18
Nodes (4): PCMFormat, PreRollBuffer, .count, AudioFramingTests

### Community 110 - "test_asr_filters.py"
Cohesion: 0.26
Nodes (4): drop_hallucination(), DropHallucinationTests, _segment(), WhisperSegmentFilterTests

### Community 111 - "McpOAuthService"
Cohesion: 0.22
Nodes (5): McpOAuthService, CompleteAndRefreshTests, ConnectorFilteringTests, FakeDao, oauth_server()

### Community 113 - "permissions.py"
Cohesion: 0.32
Nodes (3): _contained(), make_guard(), can_use_tool()

### Community 114 - "HomeView"
Cohesion: 0.13
Nodes (12): NovaGlassesApp, .body, RootView, .body, HomeView, .connectionText, .controller, .phaseColor (+4 more)

### Community 117 - "host_environment_prompt.py"
Cohesion: 0.16
Nodes (4): host_environment_prompt(), _host_kind(), _machine_line(), HostEnvironmentPromptTests

### Community 118 - "APIClient"
Cohesion: 0.20
Nodes (6): APIClient, APIError, badResponse, .errorDescription, server, unauthorized

### Community 119 - "Foundation"
Cohesion: 0.17
Nodes (7): AudioToolbox, AVFoundation, Foundation, Observation, Speech, UIKit, UserNotifications

### Community 120 - "Earcon"
Cohesion: 0.18
Nodes (9): Earcons, Earcon, cancel, done, error, thinking, wake, EarconPlaying (+1 more)

### Community 125 - "worker.py"
Cohesion: 0.27
Nodes (8): build_jobs(), _recover_stuck_tasks(), _run_check_for_responsibilities(), _run_deliver_pending_updates(), _run_process_conversations(), _run_scheduled_tasks(), run_worker(), ScheduledJob

### Community 126 - "pathlib"
Cohesion: 0.16
Nodes (6): cut_clips(), default_audio(), load(), main(), main(), migration_files()

### Community 128 - "PromptSourceEnum"
Cohesion: 0.10
Nodes (7): PromptSourceEnum, _handle_inbound(), _is_stale(), resolve_sms_conversation(), _run_sms_turn(), ConversationClosedError, GlassesPromptSourceTests

### Community 132 - "MeetingSegment"
Cohesion: 0.16
Nodes (5): MeetingSegment, ChunkingTests, FinalizeTests, NotesUseNoToolsTests, TranscriptTests

### Community 135 - "FakePlayer"
Cohesion: 0.19
Nodes (3): FakePlayer, .isBusy, FakeWake

### Community 136 - "requests"
Cohesion: 0.27
Nodes (7): backend_url(), close_current_conversation(), fetch_conversation_info(), fetch_health(), fetch_projects(), fetch_tools(), stream_reply()

### Community 139 - "AudioRouteManager"
Cohesion: 0.23
Nodes (3): AudioRouteManager, Route, .summary

### Community 143 - "AuthStore"
Cohesion: 0.21
Nodes (3): AuthStore, .baseQuery, Security

### Community 148 - "clamp_spoken"
Cohesion: 0.25
Nodes (4): deliver(), _clamp(), clamp_spoken(), ClampSpokenTests

### Community 153 - ".completed"
Cohesion: 0.14
Nodes (6): fake_stream(), fake_stream(), fake_stream(), fake_stream(), TurnStreamTests, get_final_message()

### Community 154 - "mcp_server_controller.py"
Cohesion: 0.27
Nodes (4): _callback_page(), create_mcp_server(), list_mcp_servers(), mcp_oauth_callback()

### Community 155 - "WakeDetecting"
Cohesion: 0.20
Nodes (8): WakeDetecting, Build and test (CLI), Code map, How it behaves, Install on your iPhone, NovaGlasses, On-device field checklist, What is verified and what is not

### Community 159 - "ConversationControllerTests.swift"
Cohesion: 0.39
Nodes (3): ConversationControllerTests.Rig, NovaGlasses, XCTest

### Community 161 - "protocol.py"
Cohesion: 0.39
Nodes (3): _artifact_for(), encode(), _truncate()

## Ambiguous Edges - Review These
- `TTS conversion enhancer prompt (empty)` → `Voice mode tone guidelines`  [AMBIGUOUS]
  prompting/tts_conversion_enhancer_prompt.txt · relation: conceptually_related_to

## Knowledge Gaps
- **122 isolated node(s):** `UIKit`, `UserNotifications`, `.serverURLString`, `.api`, `.summary` (+117 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1206 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **73 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `TTS conversion enhancer prompt (empty)` and `Voice mode tone guidelines`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `AgentLoop` connect `AgentLoop` to `PromptSourceEnum`, `agent_loop.py`, `Conversation`, `Tool`, `.run_agent`, `ClaudeService`, `test_memory_injection.py`, `ScheduledTask`, `.iter_sentence_chunks`, `MeetingService`, `Update`, `unittest`, `LiveReply`, `nova_controller.py`, `ScheduledTaskService`, `ResponsibilityService`, `call_controller.py`, `McpServerService`, `FakeMessage`, `ConversationLoopStreamTests`, `meeting_service.py`, `os`, `._artifact_for_tool`, `SpokenTrackTests`, `LiveScreenTests`, `StreamedSpeechTests`, `FailureSpeechTests`, `test_glasses_voice.py`, `MemoryInjectionTests`?**
  _High betweenness centrality (0.075) - this node is a cross-community bridge._
- **Are the 34 inferred relationships involving `AgentLoop` (e.g. with `PromptEnums` and `PromptSourceEnum`) actually correct?**
  _`AgentLoop` has 34 INFERRED edges - model-reasoned connections that need verification._
- **What connects `UIKit`, `UserNotifications`, `.serverURLString` to the rest of the system?**
  _122 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `agent_loop.py` be split into smaller, more focused modules?**
  _Cohesion score 0.10461538461538461 - nodes in this community are weakly interconnected._
- **Why does `MeetingService` connect `MeetingService` to `agent_loop.py`, `Conversation`, `unittest`, `MeetingSegment`, `nova_controller.py`, `test_meeting_service.py`, `ClaudeService`, `AgentLoop`, `test_memory_injection.py`, `build_service`, `BaseDao`, `MeetingError`, `Update`, `meeting_service.py`?**
  _High betweenness centrality (0.047) - this node is a cross-community bridge._
- **Are the 17 inferred relationships involving `Conversation` (e.g. with `_is_stale()` and `ConversationDao`) actually correct?**
  _`Conversation` has 17 INFERRED edges - model-reasoned connections that need verification._