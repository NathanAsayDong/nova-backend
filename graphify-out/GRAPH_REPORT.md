# Graph Report - nova-backend  (2026-11-16)

## Corpus Check
- 241 files · ~217,290 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 11 file(s) not represented in the graph (top: (none) 3, .mdc 1, .pbxproj 1)

## Summary
- 5359 nodes · 12598 edges · 237 communities (140 shown, 97 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 1321 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `dddae08c`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- ToolService
- audio_file_bytes
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
- ._conversation_turn
- Harness
- CodingService
- ScheduledTaskService
- _most_recent_local_midnight_utc
- FakeChunkDao
- process_supervisor.py
- test_memory_injection.py
- MeetingError
- CursorService
- MeetingService
- FileOperationTests
- CodingSession
- UpdateDeliveryService
- ConversationController
- .__init__
- deploy_main.py
- NovaSession
- LiveReply
- test_auth_service.py
- SessionManager
- transcribe_socket
- test_conversation_loop.py
- json
- DATGlassesCamera
- Sendable
- CodeService
- ResponsibilityService
- Responsibility
- McpOAuthService
- make_update
- build_service
- asyncio
- call_controller.py
- McpServerService
- FakeConversationService
- TurnTimer
- main.py
- AuthService
- run_migrations.py
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
- test_background_agent.py
- ClientEvent
- IsIdleTests
- Conversation
- agent_loop.py
- McpServer
- PersonaService
- TwilioService
- HttpGateTests
- AgentLoop
- conversation_controller.py
- .durationMs
- parse_gate_reply
- is_nova_interrupt_phrase
- fake_stream
- LiveScreenTests
- FakeMcpServerDao
- FakeMeetingDao
- CrudTests
- ModelListTests
- Person
- test_sms.py
- test_responsibility_service.py
- StreamedSpeechTests
- RetryCapTests
- build_memory_service
- meeting_service.py
- ASRService
- AsrLock
- UpdateService
- Mac code agent daemon
- test_spoken_reply.py
- SpokenProse
- HomeView
- ._run_begin
- BipService
- NovaSocket
- Keys
- asr_service.py
- ._build_kwargs
- CompletionNotificationTests
- TwilioErrorClassificationTests
- .repair_tool_pairing
- test_deploy_main.py
- FakeDao
- .run_turn
- typing
- AppModel
- asr-bench.py
- .completed
- FaceService
- APIClient
- Foundation
- Earcon
- SidekickSocketTests
- PromptSourceTests
- EndSessionTests
- SidekickSession
- worker.py
- VoiceMode
- Hosting Nova off the home network
- test_mcp_integration.py
- FakeSocket
- FakeDao
- ClassificationTests
- build_app
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
- RelayTokenTests
- Rig
- ToolExecutionError
- FakeSendWebSocket
- FallbackChainTests
- SpokenTrackTests
- .iter_sentence_chunks
- VisionService
- test_asr_filters.py
- MemoryChunkService
- pathlib
- host_environment_prompt.py
- PassSentinelTests
- TTSService
- CLAUDE.md
- subprocess
- install.sh
- uninstall.sh
- ClaudeCreditsService
- nova-backend
- worktree.py
- SettingsService
- FakeHttp
- CommandLineService
- DemoService
- SenderGateTests
- dict
- VisionRoutesTests
- SpeechWakeDetector
- SentryModeTests
- ._spoken_track
- AddPersonView
- PersonaPrompt
- .setUp
- DeployRunner
- prepare
- os
- StatusTextTests
- FailureSpeechTests
- ToolServiceTests
- HostEnvironmentPromptTests
- MacSessionLifecycleTests
- XCTestCase
- .wantsToSee
- ElevenLabsService
- GlassesCameraState
- InterruptedToolCallTests
- CooldownTests
- speech_summary
- Rig
- GuardrailTests
- split_wake_phrase
- _PassHold
- .test_a_live_turn_reads_deltas_then_exposes_the_message
- test_persona_service.py
- match
- AgentLink
- _FakeTable
- clamp_spoken
- auth_service.py
- ProviderSelectionTests
- FinishedSessionTowerTests
- get_nova_state
- FallbackTests
- AuthStore
- FakeUpdateService
- FakeAgentLoop
- SidekickService
- WorktreeCollisionTests
- MirrorTests
- ResponsibilityDeliveryTests
- sms_controller.py
- FakeTaskDao
- Entry
- vision_controller.py
- ReportMediumTests
- .allowed_sms_senders
- _said
- ServiceMethodToolConfig
- faces_controller.py
- ToolUseStarted
- classify

## God Nodes (most connected - your core abstractions)
1. `AgentLoop` - 131 edges
2. `Conversation` - 89 edges
3. `ConversationController` - 83 edges
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

## Communities (237 total, 97 thin omitted)

### Community 0 - "ToolService"
Cohesion: 0.13
Nodes (9): main(), main(), main(), main(), list_tools(), ToolDao, Tool, ToolService (+1 more)

### Community 1 - "audio_file_bytes"
Cohesion: 0.09
Nodes (12): audio_file_bytes(), is_raw_pcm(), _pcm_params(), suffix_for_mime(), transcribe_serialized(), emit_partial_transcript(), run_speculative_transcription(), endpoint_decision() (+4 more)

### Community 2 - "SimpleFinancesService"
Cohesion: 0.11
Nodes (6): SimplApiError, SimplConfigurationError, SimpleFinancesService, response(), SimpleFinancesServiceTest, SimplFinancesToolRegistrationTest

### Community 3 - "text"
Cohesion: 0.22
Nodes (4): AuthenticationTests, forward(), PathTokenRouteTests, text()

### Community 5 - "test_openai_loop.py"
Cohesion: 0.17
Nodes (7): FakeClient, FakeFunctionCall, FakeResponse, FakeResponsesAPI, FakeTool, FakeToolService, OpenAILoopTests

### Community 6 - "ServerEvent"
Cohesion: 0.06
Nodes (26): ServerEvent, audioStreamChunk, audioStreamEnd, audioStreamStart, captureRequest, chunkReceived, done, error (+18 more)

### Community 7 - "AgentLoopImageTests"
Cohesion: 0.16
Nodes (6): AgentLoopImageTests, fake_stream(), FakeConversationService, FakeMessage, FakeTextBlock, FakeToolUseBlock

### Community 8 - ".run_agent"
Cohesion: 0.09
Nodes (4): BackgroundAgentTests, MultiChannelReportTypeTests, ReportTypeTests, ResponsibilityRunToolRestrictionTests

### Community 10 - "make_update"
Cohesion: 0.11
Nodes (13): at(), BadgeOnlyTests, build_service(), CallDeliveryTests, EmailDeliveryTests, make_update(), MultiChannelDeliveryTests, QuietHoursTests (+5 more)

### Community 11 - "ClaudeService"
Cohesion: 0.10
Nodes (4): _env_flag(), ClaudeService, _maybe_print_prompt(), GenerationKwargsTests

### Community 12 - "GithubService"
Cohesion: 0.15
Nodes (4): GithubService, GithubServiceError, _FakeResponse, GithubServiceTests

### Community 13 - "build_service"
Cohesion: 0.06
Nodes (10): build_service(), CreateUpdateTests, FakeConversationDao, FakeProjectDao, FakeUpdateDao, make_update(), MultiChannelReportTypeTests, NotificationQueueFieldsTests (+2 more)

### Community 14 - "Nova system prompt (persona)"
Cohesion: 0.11
Nodes (15): Background agent prompt, Meeting follow-up prompt, Notify decision (email vs call), Meeting notes prompt, Meeting notes JSON output (title, summary, decisions, action items), Nova system prompt (persona), About Nate (user profile), agent_loop.py core tool-calling loop (+7 more)

### Community 15 - "SidekickController"
Cohesion: 0.11
Nodes (10): ConversationIdStore, EarconPlaying, GlassesCamera, MainScheduler, NovaSocketing, Scheduling, SpeechPlaying, VisionUploading (+2 more)

### Community 16 - "._conversation_turn"
Cohesion: 0.08
Nodes (4): persist(), _memory_block_budget_seconds(), strip_expects_reply(), _strip_expects_reply_events()

### Community 17 - "Harness"
Cohesion: 0.08
Nodes (15): LevelSmoother, Snapshot, State, calibrating, cooldown, idle, onset, speaking (+7 more)

### Community 18 - "CodingService"
Cohesion: 0.05
Nodes (5): CodingService, AgentBindingTests, FakeLink, MacShellTests, StartReportTypeTests

### Community 19 - "ScheduledTaskService"
Cohesion: 0.08
Nodes (5): ScheduledTaskDao, ScheduledTask, TaskStatus, ScheduledTaskService, CurrentTimeTests

### Community 20 - "_most_recent_local_midnight_utc"
Cohesion: 0.10
Nodes (6): _most_recent_local_midnight_utc(), IsPastRolloverTests, build_service(), CheckForStaleConversationsTests, FakeConversationDao, MostRecentLocalMidnightUtcTests

### Community 21 - "FakeChunkDao"
Cohesion: 0.08
Nodes (5): FakeAgentLoop, FakeChunkDao, FakeClaudeService, FakeNotesDao, ReplyQueue

### Community 22 - "process_supervisor.py"
Cohesion: 0.15
Nodes (14): _all(), await_ready(), check(), _entry(), _log_paths(), port_open(), read_log(), _recover() (+6 more)

### Community 23 - "test_memory_injection.py"
Cohesion: 0.06
Nodes (16): MemoryChunkDao, MemoryChunk, MemoryMatch, build_service(), FakeClaudeResponse, FakeClaudeService, FakeConversationService, FakeEmbeddingService (+8 more)

### Community 24 - "MeetingError"
Cohesion: 0.09
Nodes (19): transcribe_segments_serialized(), delete_meeting(), get_active_meeting(), get_meeting(), get_meeting_segments(), list_meetings(), _meeting_error(), meeting_socket() (+11 more)

### Community 25 - "CursorService"
Cohesion: 0.17
Nodes (4): CursorService, CursorServiceError, CursorServiceTests, _FakeResponse

### Community 27 - "FileOperationTests"
Cohesion: 0.09
Nodes (3): EditTests, FileOperationTests, PathContainmentTests

### Community 28 - "CodingSession"
Cohesion: 0.10
Nodes (5): CodingSessionDao, CodingEvent, CodingSession, CodingStatus, TimestampShapeTests

### Community 29 - "UpdateDeliveryService"
Cohesion: 0.08
Nodes (3): EmailService, _env_int(), UpdateDeliveryService

### Community 30 - "ConversationController"
Cohesion: 0.10
Nodes (8): Capture, ConversationController, .idleMessage, .isEnabled, .isWorking, .wakeWatching, Once, Sentry mode

### Community 31 - ".__init__"
Cohesion: 0.14
Nodes (6): _build_provider(), _ChainedProvider, OpenAITTS, _cartesia(), _eleven_labs(), _mock_chain()

### Community 32 - "deploy_main.py"
Cohesion: 0.13
Nodes (13): build_logger(), check_health_once(), current_commit(), DeployConfig, DeployError, git_pull(), git_reset_hard(), main() (+5 more)

### Community 33 - "NovaSession"
Cohesion: 0.10
Nodes (4): NovaSessionDao, row_to_session(), NovaSession, RowConversionTests

### Community 35 - "test_auth_service.py"
Cohesion: 0.12
Nodes (7): AuthNotConfigured, BadCredentials, LockedOut, AuthServiceTestCase, ConfigurationTests, LockoutTests, LoginTests

### Community 36 - "SessionManager"
Cohesion: 0.07
Nodes (12): Config, load_env_file(), Link, _configure_logging(), main(), _run(), _task(), _as_int() (+4 more)

### Community 37 - "transcribe_socket"
Cohesion: 0.12
Nodes (12): idle_stopped_event(), parse_conversation_id(), parse_image_ids(), _partial_is_due(), resolve_chat_request(), send_assistant_text(), _send_locked(), _speculative_asr_enabled() (+4 more)

### Community 38 - "test_conversation_loop.py"
Cohesion: 0.06
Nodes (12): MessageDao, ProjectDao, Message, MessageRole, Project, TurnStream, ProjectService, CodeServiceTestCase (+4 more)

### Community 39 - "json"
Cohesion: 0.16
Nodes (16): _all(), await_ready(), check(), _entry(), kill_tree(), _log_paths(), pid_alive(), port_open() (+8 more)

### Community 40 - "DATGlassesCamera"
Cohesion: 0.08
Nodes (8): CameraError, .errorDescription, failed, glassesAudioNotUp, noCamera, notReady, timeout, DATGlassesCamera

### Community 41 - "Sendable"
Cohesion: 0.14
Nodes (9): Phase, idle, listening, off, sentryBlocked, speaking, thinking, Cancellable (+1 more)

### Community 44 - "Responsibility"
Cohesion: 0.19
Nodes (4): Responsibility, at(), CheckForResponsibilitiesTests, DueTests

### Community 45 - "McpOAuthService"
Cohesion: 0.18
Nodes (5): McpOAuthService, _now(), _origin(), _path(), CompleteAndRefreshTests

### Community 46 - "make_update"
Cohesion: 0.16
Nodes (5): ConversationResolutionTests, make_update(), OpeningPromptTests, TwiMLTests, form()

### Community 47 - "build_service"
Cohesion: 0.06
Nodes (21): MeetingSegment, build_service(), ChunkingTests, CommitSegmentsTests, DeleteMeetingTests, FakeConversationDao, FakeEmbeddingService, FakeProjectDao (+13 more)

### Community 48 - "asyncio"
Cohesion: 0.05
Nodes (32): _client_ip(), current_session(), list_sessions(), login(), logout(), logout_all(), adopt_claude_thread(), _authorized() (+24 more)

### Community 49 - "call_controller.py"
Cohesion: 0.07
Nodes (20): answer_call(), call_status(), _escape(), mint_relay_token(), _opening_prompt(), relay_socket(), start_turn(), run_after_previous() (+12 more)

### Community 51 - "FakeConversationService"
Cohesion: 0.10
Nodes (5): CountingService, FakeConversationService, FakeToolDao, GlassesCannotRecordMeetingsTests, get_all()

### Community 52 - "TurnTimer"
Cohesion: 0.10
Nodes (8): _emit(), TurnTimer, _drain(), _FakeMessage, _FakeStream, _FakeUsage, TurnStreamUsageMarkTests, TurnTimerTests

### Community 53 - "main.py"
Cohesion: 0.08
Nodes (13): can_use_tool(), _allowed_origins(), health(), lifespan(), root(), _broadcast(), face_socket(), AuthGate (+5 more)

### Community 55 - "run_migrations.py"
Cohesion: 0.16
Nodes (4): main(), migration_files(), _jsonable(), SQLService

### Community 56 - "build_service"
Cohesion: 0.10
Nodes (10): build_service(), CreateTests, FakeProjectDao, FakeUpdateService, ListAndCancelTests, pending(), RecoverStuckTests, RunDueTests (+2 more)

### Community 57 - "FakeMessage"
Cohesion: 0.24
Nodes (6): FakeMessage, FakeTextBlock, fake_stream(), fake_stream(), ToolTurnSpeechTests, fake_stream()

### Community 58 - "FakePersonaDao"
Cohesion: 0.14
Nodes (7): build_service(), CachingTests, FakePersonaDao, LoadingTests, seed_row(), ToolFacingWrapperTests, VersioningAndRollbackTests

### Community 59 - "ConversationLoopStreamTests"
Cohesion: 0.15
Nodes (4): ConversationLoopStreamTests, fake_stream(), fake_stream(), EventStreamTests

### Community 61 - "SpeechPlayer"
Cohesion: 0.07
Nodes (7): MP3StreamDecoder, PlaybackWatchdog, SpeechPlayer, .isBusy, .now, Stream, PlaybackWatchdogTests

### Community 63 - ".look"
Cohesion: 0.16
Nodes (11): Vision: "Hey Nova, what do you see?", Client → server, Connecting, Deviations from the brief and additions, Interjections, Prompt and tools, Server behaviour, Server → client (+3 more)

### Community 64 - "FakeCamera"
Cohesion: 0.21
Nodes (4): FakeCamera, FakeVision, settle(), VisionControllerTests

### Community 67 - "test_background_agent.py"
Cohesion: 0.17
Nodes (9): fake_get_response(), FakeConversationService, FakeMessage, FakeProjectDao, FakeTextBlock, FakeToolDao, FakeUpdateService, fake_get_response() (+1 more)

### Community 68 - "ClientEvent"
Cohesion: 0.06
Nodes (30): Note, PhotoSlot, AudioRole, final, progress, status, wake, CapturePurpose (+22 more)

### Community 70 - "Conversation"
Cohesion: 0.09
Nodes (6): ConversationDao, Conversation, ConversationService, PrefetchedConversationTests, FakeConversationService, ThreadResolutionTests

### Community 71 - "agent_loop.py"
Cohesion: 0.07
Nodes (12): PromptSourceEnum, _canonical_wake_text(), has_stop_phrase(), normalize_wake_text(), voice_prompt_source(), _remove(), transcribe_utterance(), is_sidekick_pass() (+4 more)

### Community 72 - "McpServer"
Cohesion: 0.21
Nodes (3): McpServer, _b64url(), _parse_expiry()

### Community 74 - "TwilioService"
Cohesion: 0.07
Nodes (12): backend_url(), close_current_conversation(), fetch_conversation_info(), fetch_health(), fetch_projects(), fetch_tools(), stream_reply(), main() (+4 more)

### Community 77 - "conversation_controller.py"
Cohesion: 0.27
Nodes (5): close_conversation(), get_conversation(), get_conversation_messages(), _parse_uuid(), _project_payload()

### Community 78 - ".durationMs"
Cohesion: 0.19
Nodes (4): PCMFormat, PreRollBuffer, .count, AudioFramingTests

### Community 79 - "parse_gate_reply"
Cohesion: 0.22
Nodes (3): parse_gate_reply(), SidekickGate, GateReplyTests

### Community 80 - "is_nova_interrupt_phrase"
Cohesion: 0.15
Nodes (4): is_nova_interrupt_phrase(), _normalize_tokens(), NegativeMatchTests, PositiveMatchTests

### Community 81 - "fake_stream"
Cohesion: 0.15
Nodes (6): fake_stream(), FailureHistoryAndRetryTests, fake_stream(), fake_stream(), fake_stream(), _FakeBadRequestError

### Community 83 - "FakeMcpServerDao"
Cohesion: 0.17
Nodes (3): build_service(), FakeMcpServerDao, McpServerServiceTests

### Community 87 - "Person"
Cohesion: 0.11
Nodes (3): PersonDao, Person, FakePersonDao

### Community 88 - "test_sms.py"
Cohesion: 0.13
Nodes (6): BipConfigurationError, BipRequestError, is_permanent_bip_error(), normalize_phone_number(), SmsRecipientError, NormalizationTests

### Community 89 - "test_responsibility_service.py"
Cohesion: 0.12
Nodes (5): build_service(), CreateScheduleRequirementTests, FakeProjectDao, FakeUpdateService, WindowTests

### Community 90 - "StreamedSpeechTests"
Cohesion: 0.27
Nodes (3): stream(), StreamedSpeechTests, fake_stream()

### Community 91 - "RetryCapTests"
Cohesion: 0.16
Nodes (3): boom(), RetryCapTests, SplitTranscriptTests

### Community 92 - "build_memory_service"
Cohesion: 0.11
Nodes (8): build_memory_service(), FakeConversationService, FakeEmbeddingService, FakeMemoryChunkDao, FakeToolDao, FakeUpdateService, match(), RetrieveContextTests

### Community 93 - "meeting_service.py"
Cohesion: 0.06
Nodes (8): BaseDao, MeetingChunkDao, MeetingDao, MeetingNotesDao, Meeting, MeetingChunk, MeetingNotes, MeetingStatus

### Community 96 - "UpdateService"
Cohesion: 0.05
Nodes (9): UpdateDao, DeliveryStatus, encode_report_types(), normalize_report_types(), ReportType, Update, UpdateService, EscapingTests (+1 more)

### Community 97 - "Mac code agent daemon"
Cohesion: 0.16
Nodes (14): Nova code agent (Mac) README, Anthropic API key stripping, Mac dials out design, Per-session git worktree, Known limits (awake Mac, bounded replay, cache cost), launchd install and menu app, Mac code agent daemon, NOVA_CODE_TOKEN shared secret (+6 more)

### Community 98 - "test_spoken_reply.py"
Cohesion: 0.19
Nodes (5): _comparable(), is_repeat(), strip_speak_tags(), IsRepeatTests, StripSpeakTagsTests

### Community 100 - "HomeView"
Cohesion: 0.12
Nodes (12): NovaGlassesApp, .body, RootView, HomeView, .cameraText, .connectionText, .controller, .phaseColor (+4 more)

### Community 101 - "._run_begin"
Cohesion: 0.23
Nodes (6): BeginFlowTests, fake_get(), fake_post(), fake_post(), fake_post(), FakeResponse

### Community 102 - "BipService"
Cohesion: 0.13
Nodes (4): BipService, _describe_response_error(), _parse_number_list(), BodySplittingTests

### Community 104 - "Keys"
Cohesion: 0.08
Nodes (24): Keys, assistantText, bytes, chunkBase64, client, code, conversationId, count (+16 more)

### Community 105 - "asr_service.py"
Cohesion: 0.20
Nodes (8): main(), _hotwords(), _load_parakeet(), missing_cuda_libraries(), _nvidia_wheel_dll_dirs(), _platform_default_provider(), _resolve_whisper_device(), _setup_cuda_libraries()

### Community 108 - "TwilioErrorClassificationTests"
Cohesion: 0.15
Nodes (6): describe_twilio_error(), is_permanent_twilio_error(), SimpleNamespace_Exception, TwilioErrorClassificationTests, reject(), flake()

### Community 110 - "test_deploy_main.py"
Cohesion: 0.06
Nodes (11): DeployService, DryRunTests, FailingTestsAbortTests, HappyPathTests, HealthTimeoutTests, RollbackPathTests, _runner(), _silent_logger() (+3 more)

### Community 111 - "FakeDao"
Cohesion: 0.23
Nodes (3): ConnectorFilteringTests, FakeDao, oauth_server()

### Community 112 - ".run_turn"
Cohesion: 0.09
Nodes (9): MemoryInjectionTests, boom(), notification(), NotificationCapTests, NotificationCrossMediumTests, NotificationRecencyTests, NotificationScopingTests, ParallelPreRequestLookupsTests (+1 more)

### Community 113 - "typing"
Cohesion: 0.07
Nodes (9): _flag(), _contained(), make_guard(), _artifact_for(), encode(), _truncate(), _is_prose(), ModelSwitchRequest (+1 more)

### Community 114 - "AppModel"
Cohesion: 0.14
Nodes (6): AppModel, .serverURLString, .body, .body, LoginView, .body

### Community 115 - "asr-bench.py"
Cohesion: 0.36
Nodes (4): cut_clips(), default_audio(), load(), main()

### Community 116 - ".completed"
Cohesion: 0.12
Nodes (7): fake_stream(), fake_stream(), fake_stream(), fake_stream(), fake_stream(), TurnStreamTests, get_final_message()

### Community 117 - "FaceService"
Cohesion: 0.14
Nodes (5): FaceService, face_row(), FaceServiceTests, FacesRoutesTests, unit()

### Community 118 - "APIClient"
Cohesion: 0.16
Nodes (7): APIClient, APIError, badResponse, .errorDescription, server, unauthorized, Person

### Community 119 - "Foundation"
Cohesion: 0.09
Nodes (12): AudioToolbox, AVFoundation, Foundation, ImageIO, AudioSessionPolicy, ImagePrep, MWDATCamera, MWDATCore (+4 more)

### Community 120 - "Earcon"
Cohesion: 0.13
Nodes (14): Earcons, Earcon, cancel, done, error, shutter, sidekickCue, sidekickOff (+6 more)

### Community 123 - "EndSessionTests"
Cohesion: 0.17
Nodes (3): build_service(), EndSessionTests, GoodbyeTimingTests

### Community 125 - "worker.py"
Cohesion: 0.16
Nodes (10): BuildJobsTests, build_jobs(), _recover_stuck_tasks(), _run_check_for_responsibilities(), _run_check_for_stale_conversations(), _run_deliver_pending_updates(), _run_process_conversations(), _run_scheduled_tasks() (+2 more)

### Community 126 - "VoiceMode"
Cohesion: 0.26
Nodes (4): VoiceMode, conversation, sentry, VoiceModeStore

### Community 127 - "Hosting Nova off the home network"
Cohesion: 0.21
Nodes (13): Hosting Nova off the home network, Backend environment variables, Cloudflare Tunnel (nova-tower, cloudflared), Firebase Hosting frontend (nova-voice-nd.web.app), Infobip SMS integration (/sms/inbound), Failed-login lockout policy, Mac coding agent (/ws/coding), MCP OAuth callback (+5 more)

### Community 128 - "test_mcp_integration.py"
Cohesion: 0.13
Nodes (10): AgentLoopMcpTests, fake_stream(), fake_stream(), ConversationTurnMcpDisabledReplayTests, fake_stream(), FakeBlock, FakeConversationService, FakeMcpService (+2 more)

### Community 129 - "FakeSocket"
Cohesion: 0.17
Nodes (7): SocketConnectionState, connected, connecting, disconnected, unauthorized, FakeSocket, .starts

### Community 130 - "FakeDao"
Cohesion: 0.12
Nodes (3): GateTestCase, WebSocketGateTests, FakeDao

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
Cohesion: 0.29
Nodes (6): Build and test (CLI), Code map, How it behaves, Install on your iPhone, NovaGlasses, On-device field checklist

### Community 144 - "ImageStore"
Cohesion: 0.16
Nodes (4): ImageStore, VisionImage, GlassesSocketTests, ImageStoreTests

### Community 146 - "Rig"
Cohesion: 0.12
Nodes (7): ConversationControllerTests.Rig, FakePlayer, .isBusy, FakeWake, Item, ManualScheduler, Rig

### Community 148 - "FakeSendWebSocket"
Cohesion: 0.09
Nodes (9): no_tts(), FakeSendWebSocket, InterruptAndCancelWiringTests, scenario(), scenario(), scenario(), SpeakOnCompletionTests, never_finishes() (+1 more)

### Community 153 - "VisionService"
Cohesion: 0.09
Nodes (6): _in_view_text(), is_image_block(), VisionService, ContentBlocksTests, LookToolTests, phone()

### Community 154 - "test_asr_filters.py"
Cohesion: 0.26
Nodes (4): drop_hallucination(), DropHallucinationTests, _segment(), WhisperSegmentFilterTests

### Community 155 - "MemoryChunkService"
Cohesion: 0.08
Nodes (4): EmbeddingService, MemoryChunkService, ParseChunksTests, RetrievableQueryTests

### Community 156 - "pathlib"
Cohesion: 0.12
Nodes (8): classify(), _clip(), _resolve_cwd(), run(), _scratch_pair(), fetch(), main(), sha256()

### Community 157 - "host_environment_prompt.py"
Cohesion: 0.31
Nodes (3): host_environment_prompt(), _host_kind(), _machine_line()

### Community 158 - "PassSentinelTests"
Cohesion: 0.12
Nodes (9): _agent_loop(), FakeMessage, FakeTextBlock, FakeToolDao, FakeToolUseBlock, _live(), LookToolExclusionTests, fake_stream() (+1 more)

### Community 161 - "subprocess"
Cohesion: 0.13
Nodes (7): find_pid_on_port(), find_worker_pid(), run_test_suite(), stop_pid(), kill_tree(), pid_alive(), _prune()

### Community 165 - "ClaudeCreditsService"
Cohesion: 0.14
Nodes (4): get_all_settings(), get_available_models(), get_claude_credits(), ClaudeCreditsService

### Community 170 - "worktree.py"
Cohesion: 0.22
Nodes (7): create(), _git(), remove(), resolve_repo(), slugify(), Workspace, WorktreeError

### Community 172 - "FakeHttp"
Cohesion: 0.19
Nodes (5): build_service(), FakeHttp, FakeResponse, InfobipRequestTests, SendSmsTests

### Community 173 - "CommandLineService"
Cohesion: 0.07
Nodes (3): CommandLineService, BackgroundTests, ForegroundTests

### Community 175 - "SenderGateTests"
Cohesion: 0.23
Nodes (3): make_request(), SenderGateTests, go()

### Community 176 - "dict"
Cohesion: 0.25
Nodes (3): basic(), InboundSecretTests, RecipientAllowlistTests

### Community 177 - "VisionRoutesTests"
Cohesion: 0.26
Nodes (3): Identification, FakeFaceService, VisionRoutesTests

### Community 181 - "AddPersonView"
Cohesion: 0.12
Nodes (7): .api, VisionClient, AddPersonView, .body, FacesView, .body, PhotosUI

### Community 183 - ".setUp"
Cohesion: 0.12
Nodes (4): DirectTurnCounterTests, fake_transcribe(), FakeGate, FakeSidekickLoop

### Community 185 - "prepare"
Cohesion: 0.31
Nodes (3): prepare(), jpeg(), PrepareTests

### Community 186 - "os"
Cohesion: 0.08
Nodes (15): main(), one_call(), main(), one_call(), variants(), _build_file_logger(), _default_log_path(), mark() (+7 more)

### Community 191 - "MacSessionLifecycleTests"
Cohesion: 0.10
Nodes (3): MacConcurrentSessionTests, MacSessionLifecycleTests, sink()

### Community 192 - "XCTestCase"
Cohesion: 0.09
Nodes (8): AudioSessionPolicyTests, AmbientForwardingTests, ThinkingPulseTests, WakePhraseAloneTests, WakeStraightToListeningTests, What is verified and what is not, NovaGlasses, XCTest

### Community 195 - "GlassesCameraState"
Cohesion: 0.25
Nodes (7): GlassesCameraState, .canCapture, ready, registering, streaming, unavailable, unregistered

### Community 196 - "InterruptedToolCallTests"
Cohesion: 0.26
Nodes (3): FakeToolUseBlock, InterruptedToolCallTests, _call()

### Community 199 - "Rig"
Cohesion: 0.18
Nodes (3): Rig, SidekickControllerTests, SidekickEventCodingTests

### Community 201 - "split_wake_phrase"
Cohesion: 0.23
Nodes (4): has_wake_phrase(), split_wake_phrase(), SplitWakePhraseTests, WakePhraseTests

### Community 205 - "match"
Cohesion: 0.19
Nodes (4): GalleryPerson, match(), _normalise(), MatchTests

### Community 207 - "_FakeTable"
Cohesion: 0.13
Nodes (4): CheckForStaleConversationsLoopTests, _FakeResponse, _FakeSupabaseClient, _FakeTable

### Community 208 - "clamp_spoken"
Cohesion: 0.23
Nodes (5): deliver(), mark_first_speech(), _clamp(), clamp_spoken(), ClampSpokenTests

### Community 216 - "AuthStore"
Cohesion: 0.24
Nodes (3): AuthStore, .baseQuery, Security

### Community 227 - "sms_controller.py"
Cohesion: 0.16
Nodes (8): _authorize(), _handle_inbound(), inbound_sms(), inbound_sms_with_path_token(), _is_stale(), _receive(), resolve_sms_conversation(), _run_sms_turn()

### Community 231 - "Entry"
Cohesion: 0.27
Nodes (4): AudioLog, Entry, AudioLogView, .body

### Community 232 - "vision_controller.py"
Cohesion: 0.19
Nodes (5): capture_failed(), read_jpeg_body(), upload_image(), CaptureFailed, InvalidImage

### Community 242 - "faces_controller.py"
Cohesion: 0.14
Nodes (9): add_sample(), create_person(), delete_person(), _enroll(), list_people(), DuplicatePerson, EnrollmentError, FaceModelsMissing (+1 more)

## Ambiguous Edges - Review These
- `TTS conversion enhancer prompt (empty)` → `Voice mode tone guidelines`  [AMBIGUOUS]
  prompting/tts_conversion_enhancer_prompt.txt · relation: conceptually_related_to

## Knowledge Gaps
- **165 isolated node(s):** `UserNotifications`, `.serverURLString`, `.summary`, `AudioToolbox`, `.count` (+160 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1695 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **97 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `TTS conversion enhancer prompt (empty)` and `Voice mode tone guidelines`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `NovaGlasses` connect `NovaGlasses` to `XCTestCase`, `ConversationController`, `.look`?**
  _High betweenness centrality (0.305) - this node is a cross-community bridge._
- **Are the 43 inferred relationships involving `AgentLoop` (e.g. with `Server behaviour` and `PromptEnums`) actually correct?**
  _`AgentLoop` has 43 INFERRED edges - model-reasoned connections that need verification._
- **What connects `UserNotifications`, `.serverURLString`, `.summary` to the rest of the system?**
  _165 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `ToolService` be split into smaller, more focused modules?**
  _Cohesion score 0.12684989429175475 - nodes in this community are weakly interconnected._
- **Why does `Vision: "Hey Nova, what do you see?"` connect `.look` to `NovaGlasses`?**
  _High betweenness centrality (0.305) - this node is a cross-community bridge._
- **Are the 21 inferred relationships involving `Conversation` (e.g. with `_is_stale()` and `ConversationDao`) actually correct?**
  _`Conversation` has 21 INFERRED edges - model-reasoned connections that need verification._