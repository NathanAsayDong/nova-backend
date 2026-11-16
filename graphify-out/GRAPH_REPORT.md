# Graph Report - ios-new-conversation-button  (2026-11-16)

## Corpus Check
- 241 files · ~219,656 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 12 file(s) not represented in the graph (top: (none) 4, .mdc 1, .pbxproj 1)

## Summary
- 5398 nodes · 12702 edges · 230 communities (132 shown, 98 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 1338 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `cba40aff`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Tool
- nova_controller.py
- SimpleFinancesService
- text
- TranscribeSocketTests
- test_openai_loop.py
- ServerEvent
- AgentLoopImageTests
- .run_agent
- ._env
- make_update
- ClaudeService
- GithubService
- build_service
- Nova system prompt (persona)
- SidekickController
- ReportType
- Harness
- CodingService
- ScheduledTask
- _most_recent_local_midnight_utc
- FakeChunkDao
- time
- test_memory_chunk_service.py
- MeetingError
- CursorService
- MeetingService
- test_code_service.py
- CodingSession
- UpdateDeliveryService
- ConversationController
- ScheduledTaskService
- deploy_main.py
- test_auth_service.py
- LiveReply
- auth_service.py
- __main__.py
- coding_controller.py
- AgentBindingTests
- json
- DATGlassesCamera
- Sendable
- Project
- ResponsibilityService
- Responsibility
- McpOAuthService
- make_update
- build_service
- asyncio
- call_controller.py
- McpServerService
- AgentLoop
- TurnTimer
- test_auth_gate.py
- AuthService
- pending
- build_service
- FakeMessage
- FakePersonaDao
- ConversationLoopStreamTests
- ReplyTests
- SpeechPlayer
- EndpointDecisionTests
- .look
- FakeCamera
- ConversationControllerTests
- ._artifact_for_tool
- .start
- ClientEvent
- NovaGlasses
- Conversation
- agent_loop.py
- McpServer
- PersonaService
- TwilioService
- HttpGateTests
- ._conversation_turn
- get_conversation_messages
- .durationMs
- parse_gate_reply
- is_nova_interrupt_phrase
- FailureHistoryAndRetryTests
- LiveScreenTests
- FakeMcpServerDao
- FakeMeetingDao
- CrudTests
- SettingsService
- Person
- test_sms.py
- test_responsibility_service.py
- StreamedSpeechTests
- sessions.py
- build_memory_service
- meeting_service.py
- ASRService
- main.py
- UpdateService
- Mac code agent daemon
- test_spoken_reply.py
- SpokenProse
- CameraError
- ._run_begin
- BipService
- NovaSocket
- test_coding_service.py
- asr_service.py
- SessionManager
- CompletionNotificationTests
- TwilioErrorClassificationTests
- .repair_tool_pairing
- pathlib
- FakeDao
- .run_turn
- link.py
- AppModel
- test_process_supervisor.py
- .completed
- EnrollmentError
- APIClient
- Foundation
- Earcon
- SidekickSocketTests
- PromptSourceTests
- EndSessionTests
- SidekickSession
- worker.py
- FakePersonDao
- email_service.py
- .conversation_loop_events
- MacSessionLifecycleTests
- FakeDao
- ClassificationTests
- Any
- CaptureEngine
- AuthenticateTests
- history_compaction.py
- FakeResponsibilityDao
- SidekickConnection
- WorkingTreeTests
- AudioRouteManager
- .isOnlyWakePhrase
- NovaGlasses
- .sanitize_mcp_history
- PerformTests
- ImageStore
- Link
- .split_sms_body
- test_settings_service.py
- FakeSendWebSocket
- FallbackChainTests
- SpokenTrackTests
- .iter_sentence_chunks
- GlassesSocketTests
- VisionService
- test_asr_filters.py
- MemoryChunkService
- os
- host_environment_prompt.py
- PassSentinelTests
- TTSService
- CLAUDE.md
- .scaled
- install.sh
- uninstall.sh
- settings_controller.py
- nova-backend
- worktree.py
- CurrentModelTests
- FakeHttp
- CommandLineService
- DemoService
- AudioSessionPolicy
- dict
- VisionRoutesTests
- SpeechWakeDetector
- SentryModeTests
- VisionClient
- AddPersonView
- PersonaPrompt
- .setUp
- CreateScheduleRequirementTests
- prepare
- turn_timer.py
- StatusTextTests
- fake_stream
- HostEnvironmentPromptTests
- .setUp
- XCTestCase
- .wantsToSee
- GoodbyeTimingTests
- .handle
- InterruptedToolCallTests
- CooldownTests
- speech_summary
- LockoutTests
- GuardrailTests
- split_wake_phrase
- FakeConversationService
- .test_a_live_turn_reads_deltas_then_exposes_the_message
- test_persona_service.py
- FaceService
- AgentLink
- _FakeTable
- clamp_spoken
- LoginTests
- FakeResponse
- FinishedSessionTowerTests
- TranscribeUtteranceTests
- FallbackTests
- FakeUpdateService
- FakeAgentLoop
- SidekickService
- WorktreeCollisionTests
- ResponsibilityDeliveryTests
- _receive
- FakeTaskDao
- .add
- ReportMediumTests
- _said
- ServiceMethodToolConfig
- faces_controller.py

## God Nodes (most connected - your core abstractions)
1. `AgentLoop` - 131 edges
2. `Conversation` - 89 edges
3. `ConversationController` - 84 edges
4. `ToolService` - 68 edges
5. `build_service()` - 57 edges
6. `CodingService` - 55 edges
7. `Responsibility` - 54 edges
8. `MeetingService` - 52 edges
9. `UpdateService` - 49 edges
10. `Tool` - 48 edges

## Surprising Connections (you probably didn't know these)
- `Server behaviour` --references--> `audio_file_bytes()`  [INFERRED]
  SIDEKICK_PROTOCOL.md → src/controller/audio_ws.py
- `Server → client` --references--> `stream_tts_audio()`  [INFERRED]
  SIDEKICK_PROTOCOL.md → src/controller/nova_controller.py
- `Server behaviour` --references--> `AgentLoop`  [INFERRED]
  SIDEKICK_PROTOCOL.md → src/harness/agent_loop.py
- `Server behaviour` --references--> `ClaudeService`  [INFERRED]
  SIDEKICK_PROTOCOL.md → src/service/claude_service.py
- `Tests` --references--> `is_nova_interrupt_phrase()`  [INFERRED]
  SIDEKICK_PROTOCOL.md → src/service/interrupt_service.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Remote access path: Firebase frontend to Cloudflare Tunnel to tower API** — docs_hosting_firebase_hosting, docs_hosting_cloudflare_tunnel, docs_hosting_tower_api [EXTRACTED 0.95]
- **Mac agent core design principles** — mac_agent_readme_dial_out, mac_agent_readme_sessions_as_threads, mac_agent_readme_git_worktree [EXTRACTED 1.00]
- **Persisted-action safety rules across foreground and background agents** — prompting_nova_persona_prompt_confirm_persisted_actions, prompting_nova_persona_prompt_clarify_before_executing, prompting_background_agent_prompt_no_outward_actions [INFERRED 0.85]

## Communities (230 total, 98 thin omitted)

### Community 0 - "Tool"
Cohesion: 0.07
Nodes (12): main(), main(), main(), main(), main(), migration_files(), ToolDao, Tool (+4 more)

### Community 1 - "nova_controller.py"
Cohesion: 0.05
Nodes (32): audio_file_bytes(), is_raw_pcm(), _pcm_params(), suffix_for_mime(), transcribe_serialized(), _canonical_wake_text(), chat_stream(), event_source() (+24 more)

### Community 2 - "SimpleFinancesService"
Cohesion: 0.11
Nodes (6): SimplApiError, SimplConfigurationError, SimpleFinancesService, response(), SimpleFinancesServiceTest, SimplFinancesToolRegistrationTest

### Community 3 - "text"
Cohesion: 0.11
Nodes (8): ToolUseStarted, AuthenticationTests, forward(), make_request(), PathTokenRouteTests, SenderGateTests, go(), text()

### Community 5 - "test_openai_loop.py"
Cohesion: 0.17
Nodes (7): FakeClient, FakeFunctionCall, FakeResponse, FakeResponsesAPI, FakeTool, FakeToolService, OpenAILoopTests

### Community 6 - "ServerEvent"
Cohesion: 0.04
Nodes (50): Keys, assistantText, bytes, chunkBase64, client, code, conversationId, count (+42 more)

### Community 7 - "AgentLoopImageTests"
Cohesion: 0.33
Nodes (4): AgentLoopImageTests, FakeMessage, FakeTextBlock, FakeToolUseBlock

### Community 8 - ".run_agent"
Cohesion: 0.09
Nodes (4): BackgroundAgentTests, MultiChannelReportTypeTests, ReportTypeTests, ResponsibilityRunToolRestrictionTests

### Community 9 - "._env"
Cohesion: 0.13
Nodes (4): CartesiaService, CartesiaRequestTests, _full_chain_env(), ProviderSelectionTests

### Community 10 - "make_update"
Cohesion: 0.12
Nodes (13): at(), BadgeOnlyTests, build_service(), CallDeliveryTests, EmailDeliveryTests, make_update(), MultiChannelDeliveryTests, QuietHoursTests (+5 more)

### Community 11 - "ClaudeService"
Cohesion: 0.08
Nodes (6): _env_flag(), ClaudeService, _maybe_dump_request(), _maybe_print_prompt(), GenerationKwargsTests, ClaudeServiceMcpKwargsTests

### Community 12 - "GithubService"
Cohesion: 0.15
Nodes (4): GithubService, GithubServiceError, _FakeResponse, GithubServiceTests

### Community 13 - "build_service"
Cohesion: 0.06
Nodes (10): build_service(), CreateUpdateTests, FakeConversationDao, FakeProjectDao, FakeUpdateDao, make_update(), MultiChannelReportTypeTests, NotificationQueueFieldsTests (+2 more)

### Community 14 - "Nova system prompt (persona)"
Cohesion: 0.07
Nodes (28): Hosting Nova off the home network, Backend environment variables, Cloudflare Tunnel (nova-tower, cloudflared), Firebase Hosting frontend (nova-voice-nd.web.app), Infobip SMS integration (/sms/inbound), Failed-login lockout policy, Mac coding agent (/ws/coding), MCP OAuth callback (+20 more)

### Community 15 - "SidekickController"
Cohesion: 0.15
Nodes (15): Cancellable, ConversationIdStore, EarconPlaying, GlassesCamera, MainScheduler, NovaSocketing, Scheduling, SpeechPlaying (+7 more)

### Community 16 - "ReportType"
Cohesion: 0.14
Nodes (4): encode_report_types(), normalize_report_types(), ReportType, NormalizeAndEncodeReportTypesTests

### Community 17 - "Harness"
Cohesion: 0.08
Nodes (15): LevelSmoother, Snapshot, State, calibrating, cooldown, idle, onset, speaking (+7 more)

### Community 19 - "ScheduledTask"
Cohesion: 0.12
Nodes (3): ScheduledTaskDao, ScheduledTask, TaskStatus

### Community 20 - "_most_recent_local_midnight_utc"
Cohesion: 0.07
Nodes (7): _most_recent_local_midnight_utc(), IsIdleTests, IsPastRolloverTests, build_service(), CheckForStaleConversationsTests, FakeConversationDao, MostRecentLocalMidnightUtcTests

### Community 22 - "time"
Cohesion: 0.11
Nodes (18): _all(), await_ready(), check(), classify(), _entry(), kill_tree(), _log_paths(), pid_alive() (+10 more)

### Community 23 - "test_memory_chunk_service.py"
Cohesion: 0.07
Nodes (13): build_service(), FakeClaudeResponse, FakeClaudeService, FakeConversationService, FakeEmbeddingService, FakeMemoryChunkDao, FakeTextBlock, FetchMemoryTests (+5 more)

### Community 24 - "MeetingError"
Cohesion: 0.09
Nodes (19): transcribe_segments_serialized(), delete_meeting(), get_active_meeting(), get_meeting(), get_meeting_segments(), list_meetings(), _meeting_error(), meeting_socket() (+11 more)

### Community 25 - "CursorService"
Cohesion: 0.17
Nodes (4): CursorService, CursorServiceError, CursorServiceTests, _FakeResponse

### Community 26 - "MeetingService"
Cohesion: 0.05
Nodes (4): MeetingDao, Meeting, MeetingStatus, MeetingService

### Community 27 - "test_code_service.py"
Cohesion: 0.06
Nodes (7): CodeServiceTestCase, EditTests, FakeConversationDao, FakeProjectDao, FileOperationTests, PathContainmentTests, ProjectResolutionTests

### Community 30 - "ConversationController"
Cohesion: 0.10
Nodes (8): Capture, ConversationController, .idleMessage, .isEnabled, .isWorking, .wakeWatching, Once, Sentry mode

### Community 32 - "deploy_main.py"
Cohesion: 0.07
Nodes (22): build_logger(), check_health_once(), current_commit(), DeployConfig, DeployError, DeployRunner, find_all_pids_on_port(), find_all_worker_pids() (+14 more)

### Community 33 - "test_auth_service.py"
Cohesion: 0.10
Nodes (4): NovaSessionDao, row_to_session(), NovaSession, RowConversionTests

### Community 35 - "auth_service.py"
Cohesion: 0.12
Nodes (9): _client_ip(), current_session(), list_sessions(), login(), logout(), AuthNotConfigured, BadCredentials, LockedOut (+1 more)

### Community 36 - "__main__.py"
Cohesion: 0.15
Nodes (7): Config, _flag(), load_env_file(), _configure_logging(), main(), _run(), _task()

### Community 37 - "coding_controller.py"
Cohesion: 0.14
Nodes (11): adopt_claude_thread(), _authorized(), coding_socket(), coding_status(), get_coding_session(), list_claude_threads(), list_coding_sessions(), read_claude_thread() (+3 more)

### Community 39 - "json"
Cohesion: 0.16
Nodes (16): _all(), await_ready(), check(), _entry(), kill_tree(), _log_paths(), pid_alive(), port_open() (+8 more)

### Community 40 - "DATGlassesCamera"
Cohesion: 0.10
Nodes (3): failed, notReady, DATGlassesCamera

### Community 41 - "Sendable"
Cohesion: 0.14
Nodes (8): Phase, idle, listening, off, sentryBlocked, speaking, thinking, Handle

### Community 42 - "Project"
Cohesion: 0.09
Nodes (3): Project, CodeService, ProjectService

### Community 44 - "Responsibility"
Cohesion: 0.21
Nodes (4): Responsibility, at(), CheckForResponsibilitiesTests, DueTests

### Community 45 - "McpOAuthService"
Cohesion: 0.18
Nodes (5): McpOAuthService, _now(), _origin(), _path(), CompleteAndRefreshTests

### Community 46 - "make_update"
Cohesion: 0.16
Nodes (5): ConversationResolutionTests, make_update(), OpeningPromptTests, TwiMLTests, form()

### Community 47 - "build_service"
Cohesion: 0.05
Nodes (25): MeetingSegment, build_service(), ChunkingTests, CommitSegmentsTests, DeleteMeetingTests, FakeAgentLoop, FakeClaudeService, FakeConversationDao (+17 more)

### Community 48 - "asyncio"
Cohesion: 0.08
Nodes (19): logout_all(), close_conversation(), create_person(), _callback_page(), create_mcp_server(), delete_mcp_server(), list_mcp_servers(), mcp_oauth_callback() (+11 more)

### Community 49 - "call_controller.py"
Cohesion: 0.08
Nodes (16): answer_call(), call_status(), _escape(), mint_relay_token(), _opening_prompt(), relay_socket(), start_turn(), run_after_previous() (+8 more)

### Community 51 - "AgentLoop"
Cohesion: 0.05
Nodes (22): AgentLoop, ToolService, fake_get_response(), FakeConversationService, FakeMessage, FakeTextBlock, FakeToolDao, FakeUpdateService (+14 more)

### Community 52 - "TurnTimer"
Cohesion: 0.10
Nodes (8): _emit(), TurnTimer, _drain(), _FakeMessage, _FakeStream, _FakeUsage, TurnStreamUsageMarkTests, TurnTimerTests

### Community 53 - "test_auth_gate.py"
Cohesion: 0.11
Nodes (7): AuthGate, bearer_token(), _header(), is_exempt(), build_app(), ExemptionTests, SidekickAuthTests

### Community 54 - "AuthService"
Cohesion: 0.12
Nodes (3): AuthService, _hash_token(), ConfigurationTests

### Community 55 - "pending"
Cohesion: 0.21
Nodes (4): pending(), RecoverStuckTests, RunDueTests, RunTests

### Community 56 - "build_service"
Cohesion: 0.14
Nodes (6): build_service(), CreateTests, FakeProjectDao, FakeUpdateService, ListAndCancelTests, soon()

### Community 57 - "FakeMessage"
Cohesion: 0.23
Nodes (7): FakeMessage, FakeTextBlock, fake_stream(), fake_stream(), fake_stream(), ToolTurnSpeechTests, fake_stream()

### Community 58 - "FakePersonaDao"
Cohesion: 0.14
Nodes (7): build_service(), CachingTests, FakePersonaDao, LoadingTests, seed_row(), ToolFacingWrapperTests, VersioningAndRollbackTests

### Community 59 - "ConversationLoopStreamTests"
Cohesion: 0.15
Nodes (4): ConversationLoopStreamTests, fake_stream(), fake_stream(), EventStreamTests

### Community 61 - "SpeechPlayer"
Cohesion: 0.07
Nodes (7): MP3StreamDecoder, PlaybackWatchdog, SpeechPlayer, .isBusy, .now, Stream, PlaybackWatchdogTests

### Community 62 - "EndpointDecisionTests"
Cohesion: 0.06
Nodes (11): AsrLock, caption_endpoint_decision(), _caption_floor(), endpoint_decision(), _endpoint_scale(), EndpointDecision, _ms(), _score_transcript() (+3 more)

### Community 63 - ".look"
Cohesion: 0.17
Nodes (10): Client → server, Connecting, Deviations from the brief and additions, Interjections, Prompt and tools, Server behaviour, Server → client, Sidekick protocol: `WS /ws/sidekick` (+2 more)

### Community 64 - "FakeCamera"
Cohesion: 0.21
Nodes (4): FakeCamera, FakeVision, settle(), VisionControllerTests

### Community 65 - "ConversationControllerTests"
Cohesion: 0.05
Nodes (13): ConversationControllerTests, ConversationControllerTests.Rig, FakePlayer, .isBusy, FakeSocket, .starts, FakeWake, Item (+5 more)

### Community 68 - "ClientEvent"
Cohesion: 0.06
Nodes (28): AudioRole, final, progress, status, wake, CapturePurpose, sentry, turn (+20 more)

### Community 69 - "NovaGlasses"
Cohesion: 0.18
Nodes (4): AmbientForwardingTests, What is verified and what is not, NovaGlasses, XCTest

### Community 70 - "Conversation"
Cohesion: 0.07
Nodes (7): ConversationDao, MessageDao, Conversation, Message, ConversationService, FakeConversationService, ThreadResolutionTests

### Community 71 - "agent_loop.py"
Cohesion: 0.06
Nodes (15): PromptSourceEnum, _handle_inbound(), _is_stale(), resolve_sms_conversation(), _run_sms_turn(), MessageRole, TurnStream, has_be_quiet_phrase() (+7 more)

### Community 72 - "McpServer"
Cohesion: 0.21
Nodes (3): McpServer, _b64url(), _parse_expiry()

### Community 74 - "TwilioService"
Cohesion: 0.07
Nodes (7): main(), report(), TwilioConfigurationError, TwilioService, ConfigurationGuardTests, EscapingTests, RelayTokenTests

### Community 76 - "._conversation_turn"
Cohesion: 0.03
Nodes (6): persist(), _memory_block_budget_seconds(), _PassHold, strip_expects_reply(), _strip_expects_reply_events(), GlassesPromptSourceTests

### Community 77 - "get_conversation_messages"
Cohesion: 0.32
Nodes (4): get_conversation(), get_conversation_messages(), _parse_uuid(), _project_payload()

### Community 78 - ".durationMs"
Cohesion: 0.18
Nodes (4): PCMFormat, PreRollBuffer, .count, AudioFramingTests

### Community 79 - "parse_gate_reply"
Cohesion: 0.22
Nodes (3): parse_gate_reply(), SidekickGate, GateReplyTests

### Community 80 - "is_nova_interrupt_phrase"
Cohesion: 0.15
Nodes (4): is_nova_interrupt_phrase(), _normalize_tokens(), NegativeMatchTests, PositiveMatchTests

### Community 81 - "FailureHistoryAndRetryTests"
Cohesion: 0.15
Nodes (4): FailureHistoryAndRetryTests, fake_stream(), fake_stream(), _FakeBadRequestError

### Community 83 - "FakeMcpServerDao"
Cohesion: 0.17
Nodes (3): build_service(), FakeMcpServerDao, McpServerServiceTests

### Community 88 - "test_sms.py"
Cohesion: 0.13
Nodes (6): BipConfigurationError, BipRequestError, is_permanent_bip_error(), normalize_phone_number(), SmsRecipientError, NormalizationTests

### Community 89 - "test_responsibility_service.py"
Cohesion: 0.14
Nodes (4): build_service(), FakeProjectDao, FakeUpdateService, WindowTests

### Community 90 - "StreamedSpeechTests"
Cohesion: 0.27
Nodes (3): stream(), StreamedSpeechTests, fake_stream()

### Community 91 - "sessions.py"
Cohesion: 0.17
Nodes (5): _contained(), make_guard(), can_use_tool(), _flatten(), _is_prose()

### Community 92 - "build_memory_service"
Cohesion: 0.26
Nodes (5): build_memory_service(), FakeEmbeddingService, FakeMemoryChunkDao, match(), RetrieveContextTests

### Community 93 - "meeting_service.py"
Cohesion: 0.06
Nodes (9): BaseDao, CodingSessionDao, MeetingChunkDao, MeetingNotesDao, ProjectDao, CodingEvent, CodingStatus, MeetingChunk (+1 more)

### Community 95 - "main.py"
Cohesion: 0.15
Nodes (6): _allowed_origins(), health(), lifespan(), root(), _broadcast(), face_socket()

### Community 96 - "UpdateService"
Cohesion: 0.08
Nodes (4): UpdateDao, DeliveryStatus, Update, UpdateService

### Community 97 - "Mac code agent daemon"
Cohesion: 0.16
Nodes (14): Nova code agent (Mac) README, Anthropic API key stripping, Mac dials out design, Per-session git worktree, Known limits (awake Mac, bounded replay, cache cost), launchd install and menu app, Mac code agent daemon, NOVA_CODE_TOKEN shared secret (+6 more)

### Community 98 - "test_spoken_reply.py"
Cohesion: 0.16
Nodes (6): _comparable(), is_repeat(), _plain_text(), strip_speak_tags(), IsRepeatTests, StripSpeakTagsTests

### Community 100 - "CameraError"
Cohesion: 0.14
Nodes (10): APIError, badResponse, .errorDescription, server, unauthorized, CameraError, .errorDescription, glassesAudioNotUp (+2 more)

### Community 101 - "._run_begin"
Cohesion: 0.23
Nodes (6): BeginFlowTests, fake_get(), fake_post(), fake_post(), fake_post(), FakeResponse

### Community 102 - "BipService"
Cohesion: 0.17
Nodes (3): BipService, _describe_response_error(), _parse_number_list()

### Community 103 - "NovaSocket"
Cohesion: 0.11
Nodes (7): .baseURL, SocketConnectionState, connected, connecting, disconnected, unauthorized, NovaSocket

### Community 105 - "asr_service.py"
Cohesion: 0.20
Nodes (8): main(), _hotwords(), _load_parakeet(), missing_cuda_libraries(), _nvidia_wheel_dll_dirs(), _platform_default_provider(), _resolve_whisper_device(), _setup_cuda_libraries()

### Community 106 - "SessionManager"
Cohesion: 0.27
Nodes (3): _as_int(), _ms_to_iso(), SessionManager

### Community 108 - "TwilioErrorClassificationTests"
Cohesion: 0.14
Nodes (6): describe_twilio_error(), is_permanent_twilio_error(), SimpleNamespace_Exception, TwilioErrorClassificationTests, reject(), flake()

### Community 110 - "pathlib"
Cohesion: 0.05
Nodes (13): DeployService, DryRunTests, FailingTestsAbortTests, HappyPathTests, HealthTimeoutTests, LeftoverSweepTests, RollbackPathTests, _runner() (+5 more)

### Community 111 - "FakeDao"
Cohesion: 0.23
Nodes (3): ConnectorFilteringTests, FakeDao, oauth_server()

### Community 112 - ".run_turn"
Cohesion: 0.10
Nodes (8): MemoryInjectionTests, boom(), notification(), NotificationCapTests, NotificationCrossMediumTests, NotificationRecencyTests, NotificationScopingTests, PendingNotificationsInjectionTests

### Community 113 - "link.py"
Cohesion: 0.21
Nodes (3): _artifact_for(), encode(), _truncate()

### Community 114 - "AppModel"
Cohesion: 0.05
Nodes (21): AppModel, .serverURLString, NovaGlassesApp, .body, RootView, .body, AuthStore, .baseQuery (+13 more)

### Community 115 - "test_process_supervisor.py"
Cohesion: 0.10
Nodes (8): cut_clips(), default_audio(), load(), main(), fetch(), main(), sha256(), MirrorTests

### Community 116 - ".completed"
Cohesion: 0.13
Nodes (7): fake_stream(), fake_stream(), fake_stream(), fake_stream(), TurnStreamTests, get_final_message(), fake_stream()

### Community 117 - "EnrollmentError"
Cohesion: 0.18
Nodes (5): DuplicatePerson, EnrollmentError, face_row(), FaceServiceTests, unit()

### Community 119 - "Foundation"
Cohesion: 0.12
Nodes (9): AudioToolbox, AVFoundation, Foundation, MWDATCamera, MWDATCore, Observation, Security, Speech (+1 more)

### Community 120 - "Earcon"
Cohesion: 0.12
Nodes (15): Earcons, Note, Earcon, cancel, done, error, shutter, sidekickCue (+7 more)

### Community 125 - "worker.py"
Cohesion: 0.16
Nodes (10): BuildJobsTests, build_jobs(), _recover_stuck_tasks(), _run_check_for_responsibilities(), _run_check_for_stale_conversations(), _run_deliver_pending_updates(), _run_process_conversations(), _run_scheduled_tasks() (+2 more)

### Community 128 - ".conversation_loop_events"
Cohesion: 0.19
Nodes (6): PrefetchedConversationTests, fake_stream(), fake_stream(), fake_stream(), FakeBlock, FakeMessage

### Community 130 - "FakeDao"
Cohesion: 0.11
Nodes (4): GateTestCase, WebSocketGateTests, AuthServiceTestCase, FakeDao

### Community 135 - "history_compaction.py"
Cohesion: 0.20
Nodes (15): _block_chars(), cap_messages(), clear_old_tool_results(), _clearable_blocks(), compact_history(), _env_int(), _is_plain_user_turn(), _history() (+7 more)

### Community 137 - "SidekickConnection"
Cohesion: 0.12
Nodes (3): Utterances, sidekick_socket(), SidekickConnection

### Community 139 - "AudioRouteManager"
Cohesion: 0.22
Nodes (3): AudioRouteManager, Route, .summary

### Community 141 - "NovaGlasses"
Cohesion: 0.25
Nodes (7): Build and test (CLI), Code map, How it behaves, Install on your iPhone, NovaGlasses, On-device field checklist, Vision: "Hey Nova, what do you see?"

### Community 144 - "ImageStore"
Cohesion: 0.21
Nodes (3): ImageStore, VisionImage, ImageStoreTests

### Community 148 - "FakeSendWebSocket"
Cohesion: 0.09
Nodes (9): no_tts(), FakeSendWebSocket, InterruptAndCancelWiringTests, scenario(), scenario(), scenario(), SpeakOnCompletionTests, never_finishes() (+1 more)

### Community 153 - "VisionService"
Cohesion: 0.16
Nodes (4): VisionService, ContentBlocksTests, LookToolTests, phone()

### Community 154 - "test_asr_filters.py"
Cohesion: 0.26
Nodes (4): drop_hallucination(), DropHallucinationTests, _segment(), WhisperSegmentFilterTests

### Community 155 - "MemoryChunkService"
Cohesion: 0.06
Nodes (7): MemoryChunkDao, MemoryChunk, MemoryMatch, EmbeddingService, MemoryChunkService, ParseChunksTests, RetrievableQueryTests

### Community 156 - "os"
Cohesion: 0.13
Nodes (10): classify(), _clip(), _resolve_cwd(), run(), _scratch_pair(), main(), one_call(), main() (+2 more)

### Community 157 - "host_environment_prompt.py"
Cohesion: 0.31
Nodes (3): host_environment_prompt(), _host_kind(), _machine_line()

### Community 158 - "PassSentinelTests"
Cohesion: 0.08
Nodes (12): is_sidekick_pass(), _agent_loop(), FakeConversationService, FakeMessage, FakeTextBlock, FakeToolDao, FakeToolUseBlock, _live() (+4 more)

### Community 165 - "settings_controller.py"
Cohesion: 0.11
Nodes (6): get_all_settings(), get_available_models(), get_claude_credits(), ModelSwitchRequest, set_model(), ClaudeCreditsService

### Community 170 - "worktree.py"
Cohesion: 0.22
Nodes (7): create(), _git(), remove(), resolve_repo(), slugify(), Workspace, WorktreeError

### Community 172 - "FakeHttp"
Cohesion: 0.20
Nodes (5): build_service(), FakeHttp, InfobipRequestTests, RecipientAllowlistTests, SendSmsTests

### Community 173 - "CommandLineService"
Cohesion: 0.07
Nodes (3): CommandLineService, BackgroundTests, ForegroundTests

### Community 176 - "dict"
Cohesion: 0.19
Nodes (4): user_phone_number(), basic(), InboundSecretTests, SenderAllowlistTests

### Community 177 - "VisionRoutesTests"
Cohesion: 0.26
Nodes (3): Identification, FakeFaceService, VisionRoutesTests

### Community 181 - "AddPersonView"
Cohesion: 0.24
Nodes (6): .api, AddPersonView, .body, FacesView, .body, PhotosUI

### Community 183 - ".setUp"
Cohesion: 0.12
Nodes (4): DirectTurnCounterTests, fake_transcribe(), FakeGate, FakeSidekickLoop

### Community 185 - "prepare"
Cohesion: 0.31
Nodes (3): prepare(), jpeg(), PrepareTests

### Community 186 - "turn_timer.py"
Cohesion: 0.06
Nodes (22): backend_url(), close_current_conversation(), fetch_conversation_info(), fetch_health(), fetch_projects(), fetch_tools(), stream_reply(), _build_file_logger() (+14 more)

### Community 188 - "fake_stream"
Cohesion: 0.18
Nodes (3): fake_stream(), fake_stream(), FailureSpeechTests

### Community 192 - "XCTestCase"
Cohesion: 0.16
Nodes (3): ThinkingPulseTests, WakePhraseAloneTests, WakeStraightToListeningTests

### Community 195 - ".handle"
Cohesion: 0.11
Nodes (8): PhotoSlot, GlassesCameraState, .canCapture, ready, registering, streaming, unavailable, unregistered

### Community 196 - "InterruptedToolCallTests"
Cohesion: 0.26
Nodes (3): FakeToolUseBlock, InterruptedToolCallTests, _call()

### Community 197 - "CooldownTests"
Cohesion: 0.18
Nodes (3): CooldownTests, refused(), _mock_chain()

### Community 201 - "split_wake_phrase"
Cohesion: 0.23
Nodes (4): has_wake_phrase(), split_wake_phrase(), SplitWakePhraseTests, WakePhraseTests

### Community 205 - "FaceService"
Cohesion: 0.13
Nodes (5): FaceService, GalleryPerson, match(), _normalise(), MatchTests

### Community 207 - "_FakeTable"
Cohesion: 0.13
Nodes (4): CheckForStaleConversationsLoopTests, _FakeResponse, _FakeSupabaseClient, _FakeTable

### Community 208 - "clamp_spoken"
Cohesion: 0.23
Nodes (5): deliver(), mark_first_speech(), _clamp(), clamp_spoken(), ClampSpokenTests

### Community 227 - "_receive"
Cohesion: 0.31
Nodes (4): _authorize(), inbound_sms(), inbound_sms_with_path_token(), _receive()

### Community 231 - ".add"
Cohesion: 0.14
Nodes (4): AudioLog, Entry, .body, .body

### Community 242 - "faces_controller.py"
Cohesion: 0.10
Nodes (11): add_sample(), delete_person(), _enroll(), list_people(), capture_failed(), read_jpeg_body(), upload_image(), FaceModelsMissing (+3 more)

## Ambiguous Edges - Review These
- `TTS conversion enhancer prompt (empty)` → `Voice mode tone guidelines`  [AMBIGUOUS]
  prompting/tts_conversion_enhancer_prompt.txt · relation: conceptually_related_to

## Knowledge Gaps
- **165 isolated node(s):** `UserNotifications`, `.serverURLString`, `.summary`, `AudioToolbox`, `.count` (+160 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1701 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **98 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `TTS conversion enhancer prompt (empty)` and `Voice mode tone guidelines`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `NovaGlasses` connect `NovaGlasses` to `NovaGlasses`, `ConversationController`?**
  _High betweenness centrality (0.312) - this node is a cross-community bridge._
- **Are the 43 inferred relationships involving `AgentLoop` (e.g. with `Server behaviour` and `PromptEnums`) actually correct?**
  _`AgentLoop` has 43 INFERRED edges - model-reasoned connections that need verification._
- **What connects `UserNotifications`, `.serverURLString`, `.summary` to the rest of the system?**
  _165 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Tool` be split into smaller, more focused modules?**
  _Cohesion score 0.06558118498417007 - nodes in this community are weakly interconnected._
- **Why does `Vision: "Hey Nova, what do you see?"` connect `NovaGlasses` to `.look`?**
  _High betweenness centrality (0.312) - this node is a cross-community bridge._
- **Are the 21 inferred relationships involving `Conversation` (e.g. with `_is_stale()` and `ConversationDao`) actually correct?**
  _`Conversation` has 21 INFERRED edges - model-reasoned connections that need verification._