# Graph Report - silent-mode-backend  (2026-11-24)

## Corpus Check
- 243 files · ~227,456 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 12 file(s) not represented in the graph (top: (none) 4, .mdc 1, .pbxproj 1)

## Summary
- 5546 nodes · 12997 edges · 240 communities (138 shown, 102 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 1382 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `29aa57c5`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- ToolService
- nova_controller.py
- SimpleFinancesService
- text
- TranscribeSocketTests
- OpenAILoopTests
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
- test_meeting_service.py
- process_supervisor.py
- build_service
- ReportType
- CursorService
- MeetingService
- test_code_service.py
- AppModel
- meeting_service.py
- ConversationController
- Keys
- deploy_main.py
- NovaSession
- LiveReply
- auth_controller.py
- SessionManager
- _runner
- _silent_logger
- time
- DATGlassesCamera
- Sendable
- .conversation_loop_events
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
- test_auth_gate.py
- AuthService
- SpeakOnCompletionTests
- build_service
- FakeMessage
- FakePersonaDao
- ConversationLoopStreamTests
- sms_controller.py
- SpeechPlayer
- EndpointDecisionTests
- .look
- FakeCamera
- ConversationControllerTests
- ._artifact_for_tool
- BaseDao
- ClientEvent
- NovaGlasses
- Conversation
- agent_loop.py
- McpServer
- PersonaService
- TwilioService
- HttpGateTests
- AgentLoop
- sidekick_controller.py
- IsIdleTests
- GateDecision
- is_nova_interrupt_phrase
- FailureHistoryAndRetryTests
- .setUp
- FakeMcpServerDao
- FakeMeetingDao
- CrudTests
- SettingsService
- CodingSession
- test_sms.py
- test_responsibility_service.py
- StreamedSpeechTests
- test_deploy_main.py
- build_memory_service
- Project
- ASRService
- sessions.py
- UpdateService
- Mac code agent daemon
- test_spoken_reply.py
- SpokenProse
- AgentBindingTests
- ._run_begin
- BipService
- NovaSocket
- Rig
- asr_service.py
- coding_controller.py
- CompletionNotificationTests
- ElevenLabsService
- .repair_tool_pairing
- .deploy_main
- FakeDao
- .run_turn
- TwilioErrorClassificationTests
- HomeView
- asr-bench.py
- .test_a_live_turn_reads_deltas_then_exposes_the_message
- FakeAgentLoop
- APIClient
- Foundation
- Earcon
- SidekickSocketTests
- AuthStore
- EndSessionTests
- SidekickSession
- worker.py
- DeployService
- email_service.py
- subprocess
- DeployRunner
- AuthenticateTests
- ClassificationTests
- ._build_kwargs
- CaptureEngine
- pending
- history_compaction.py
- AsrLock
- SidekickConnection
- WorkingTreeTests
- AudioRouteManager
- .isOnlyWakePhrase
- VoiceMode
- requests
- PerformTests
- FakeDao
- SilentModeServiceTests
- conversation_controller.py
- .allowed_sms_senders
- FakeSendWebSocket
- FallbackChainTests
- SpokenTrackTests
- ConversationControllerSilentModeTests
- CommandLineService
- VisionService
- test_asr_filters.py
- MemoryChunkService
- .run_terminal_command
- host_environment_prompt.py
- PassSentinelTests
- .__init__
- CLAUDE.md
- .decode
- install.sh
- uninstall.sh
- ClaudeCreditsService
- nova-backend
- worktree.py
- CurrentModelTests
- FakeHttp
- BackgroundTests
- DemoService
- MeetingError
- dict
- RelayTokenTests
- SpeechWakeDetector
- SentryModeTests
- MirrorTests
- AddPersonView
- PersonaPrompt
- .setUp
- test_scheduled_task_service.py
- AmbientForwardingTests
- os
- FailureSpeechTests
- SelfKillHazardTests
- SpawnStaleAncestorHelperTimingTests
- HostEnvironmentPromptTests
- MacSessionLifecycleTests
- ThinkingPulseTests
- .wantsToSee
- GoodbyeTimingTests
- TTSService
- InterruptedToolCallTests
- CooldownTests
- speech_summary
- test_auth_service.py
- GuardrailTests
- FakeUpdateService
- MacShellTests
- ._to_dict
- FaceService
- AgentLink
- _FakeTable
- FakeUpdateService
- FakeTaskDao
- FakeResponse
- FinishedSessionTowerTests
- ReplyTests
- FallbackTests
- FakeUpdateDao
- FakeResponsibilityDao
- VisionClient
- NovaGlasses
- _PassHold
- .start
- WorktreeCollisionTests
- test_persona_service.py
- .iter_sentence_chunks
- build_service
- strip_speak_tags
- SidekickGate
- ThreadResolutionTests
- Entry
- CheckForStaleConversationsLoopTests
- FakeConversationService
- FakeConversationService
- _describe_failure
- TranscribeUtteranceTests
- ServiceMethodToolConfig
- ToolRegistrationTests

## God Nodes (most connected - your core abstractions)
1. `AgentLoop` - 135 edges
2. `Conversation` - 92 edges
3. `ConversationController` - 85 edges
4. `ToolService` - 72 edges
5. `build_service()` - 57 edges
6. `CodingService` - 55 edges
7. `Responsibility` - 54 edges
8. `MeetingService` - 52 edges
9. `UpdateService` - 50 edges
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

## Communities (240 total, 102 thin omitted)

### Community 0 - "ToolService"
Cohesion: 0.13
Nodes (10): main(), main(), main(), main(), Tool, ToolService, _agent_loop(), FakeToolDao (+2 more)

### Community 1 - "nova_controller.py"
Cohesion: 0.05
Nodes (30): _canonical_wake_text(), chat_stream(), event_source(), get_nova_power(), get_nova_state(), has_stop_phrase(), has_wake_phrase(), idle_stopped_event() (+22 more)

### Community 2 - "SimpleFinancesService"
Cohesion: 0.11
Nodes (6): SimplApiError, SimplConfigurationError, SimpleFinancesService, response(), SimpleFinancesServiceTest, SimplFinancesToolRegistrationTest

### Community 3 - "text"
Cohesion: 0.06
Nodes (15): _artifact_for(), encode(), _truncate(), main(), migration_files(), ToolUseStarted, _jsonable(), SQLService (+7 more)

### Community 5 - "OpenAILoopTests"
Cohesion: 0.16
Nodes (7): FakeClient, FakeFunctionCall, FakeResponse, FakeResponsesAPI, FakeTool, FakeToolService, OpenAILoopTests

### Community 6 - "ServerEvent"
Cohesion: 0.06
Nodes (26): ServerEvent, audioStreamChunk, audioStreamEnd, audioStreamStart, captureRequest, chunkReceived, done, error (+18 more)

### Community 7 - "AgentLoopImageTests"
Cohesion: 0.16
Nodes (6): AgentLoopImageTests, fake_stream(), FakeConversationService, FakeMessage, FakeTextBlock, FakeToolUseBlock

### Community 8 - ".run_agent"
Cohesion: 0.07
Nodes (4): BackgroundAgentTests, MultiChannelReportTypeTests, ReportTypeTests, ResponsibilityRunToolRestrictionTests

### Community 9 - "._env"
Cohesion: 0.14
Nodes (4): CartesiaService, CartesiaRequestTests, _full_chain_env(), ProviderSelectionTests

### Community 10 - "make_update"
Cohesion: 0.12
Nodes (10): at(), build_service(), CallDeliveryTests, EmailDeliveryTests, make_update(), MultiChannelDeliveryTests, QuietHoursTests, SettleCallTests (+2 more)

### Community 11 - "ClaudeService"
Cohesion: 0.12
Nodes (4): _env_flag(), ClaudeService, _maybe_print_prompt(), GenerationKwargsTests

### Community 12 - "GithubService"
Cohesion: 0.15
Nodes (4): GithubService, GithubServiceError, _FakeResponse, GithubServiceTests

### Community 13 - "build_service"
Cohesion: 0.07
Nodes (9): build_service(), CreateUpdateTests, FakeConversationDao, FakeProjectDao, make_update(), MultiChannelReportTypeTests, NotificationQueueFieldsTests, ReportTypeTests (+1 more)

### Community 14 - "Nova system prompt (persona)"
Cohesion: 0.07
Nodes (28): Hosting Nova off the home network, Backend environment variables, Cloudflare Tunnel (nova-tower, cloudflared), Firebase Hosting frontend (nova-voice-nd.web.app), Infobip SMS integration (/sms/inbound), Failed-login lockout policy, Mac coding agent (/ws/coding), MCP OAuth callback (+20 more)

### Community 15 - "SidekickController"
Cohesion: 0.11
Nodes (11): .currentConversationId, ConversationIdStore, EarconPlaying, GlassesCamera, MainScheduler, NovaSocketing, Scheduling, SpeechPlaying (+3 more)

### Community 16 - "._conversation_turn"
Cohesion: 0.09
Nodes (6): deliver(), mark_first_speech(), persist(), _memory_block_budget_seconds(), strip_expects_reply(), _strip_expects_reply_events()

### Community 17 - "Harness"
Cohesion: 0.08
Nodes (15): LevelSmoother, Snapshot, State, calibrating, cooldown, idle, onset, speaking (+7 more)

### Community 19 - "ScheduledTaskService"
Cohesion: 0.09
Nodes (4): ScheduledTaskDao, ScheduledTask, TaskStatus, ScheduledTaskService

### Community 20 - "_most_recent_local_midnight_utc"
Cohesion: 0.10
Nodes (6): _most_recent_local_midnight_utc(), IsPastRolloverTests, build_service(), CheckForStaleConversationsTests, FakeConversationDao, MostRecentLocalMidnightUtcTests

### Community 21 - "test_meeting_service.py"
Cohesion: 0.06
Nodes (9): FakeAgentLoop, FakeChunkDao, FakeClaudeService, FakeConversationDao, FakeEmbeddingService, FakeNotesDao, FakeUpdateService, RecoveryTests (+1 more)

### Community 22 - "process_supervisor.py"
Cohesion: 0.11
Nodes (18): _all(), await_ready(), check(), classify(), _entry(), kill_tree(), _log_paths(), pid_alive() (+10 more)

### Community 23 - "build_service"
Cohesion: 0.07
Nodes (11): MemoryChunk, build_service(), FakeClaudeService, FakeConversationService, FakeEmbeddingService, FakeMemoryChunkDao, FetchMemoryTests, ProcessConversationsTests (+3 more)

### Community 24 - "ReportType"
Cohesion: 0.09
Nodes (10): DeliveryStatus, encode_report_types(), normalize_report_types(), ReportType, user_phone_number(), EscapingTests, BadgeOnlyTests, SmsPermanentFailureTests (+2 more)

### Community 25 - "CursorService"
Cohesion: 0.18
Nodes (4): CursorService, CursorServiceError, CursorServiceTests, _FakeResponse

### Community 27 - "test_code_service.py"
Cohesion: 0.06
Nodes (7): CodeServiceTestCase, EditTests, FakeConversationDao, FakeProjectDao, FileOperationTests, PathContainmentTests, ProjectResolutionTests

### Community 28 - "AppModel"
Cohesion: 0.12
Nodes (6): AppModel, .serverURLString, .body, .body, LoginView, .body

### Community 29 - "meeting_service.py"
Cohesion: 0.08
Nodes (7): MeetingChunkDao, MeetingDao, MeetingNotesDao, Meeting, MeetingChunk, MeetingNotes, MeetingStatus

### Community 30 - "ConversationController"
Cohesion: 0.11
Nodes (8): Capture, ConversationController, .idleMessage, .isEnabled, .isWorking, .wakeWatching, Once, Sentry mode

### Community 31 - "Keys"
Cohesion: 0.08
Nodes (24): Keys, assistantText, bytes, chunkBase64, client, code, conversationId, count (+16 more)

### Community 32 - "deploy_main.py"
Cohesion: 0.12
Nodes (14): build_logger(), check_health_once(), DeployConfig, _ensure_single_healthy_api(), find_all_pids_on_port(), find_pid_on_port(), main(), _protected_pids() (+6 more)

### Community 33 - "NovaSession"
Cohesion: 0.10
Nodes (4): NovaSessionDao, row_to_session(), NovaSession, RowConversionTests

### Community 35 - "auth_controller.py"
Cohesion: 0.26
Nodes (5): _client_ip(), current_session(), list_sessions(), login(), logout()

### Community 36 - "SessionManager"
Cohesion: 0.07
Nodes (12): Config, load_env_file(), Link, _configure_logging(), main(), _run(), _task(), _as_int() (+4 more)

### Community 37 - "_runner"
Cohesion: 0.12
Nodes (5): DryRunTests, LeftoverSweepTests, RollbackPathTests, _runner(), SweepHandsOffStaleAncestorsTests

### Community 38 - "_silent_logger"
Cohesion: 0.12
Nodes (4): EnsureSingleHealthyApiTests, HelperModeCliTests, RunStaleAncestorHelperTests, _silent_logger()

### Community 39 - "time"
Cohesion: 0.09
Nodes (21): _all(), await_ready(), check(), classify(), _entry(), kill_tree(), _log_paths(), pid_alive() (+13 more)

### Community 40 - "DATGlassesCamera"
Cohesion: 0.06
Nodes (15): CameraError, .errorDescription, failed, glassesAudioNotUp, noCamera, notReady, timeout, DATGlassesCamera (+7 more)

### Community 41 - "Sendable"
Cohesion: 0.15
Nodes (7): Cancellable, Handle, SocketConnectionState, connected, connecting, disconnected, unauthorized

### Community 42 - ".conversation_loop_events"
Cohesion: 0.08
Nodes (14): PrefetchedConversationTests, fake_stream(), fake_stream(), fake_stream(), AgentLoopMcpTests, fake_stream(), fake_stream(), ConversationTurnMcpDisabledReplayTests (+6 more)

### Community 44 - "Responsibility"
Cohesion: 0.14
Nodes (5): Responsibility, at(), CheckForResponsibilitiesTests, DueTests, ReportMediumTests

### Community 45 - "McpOAuthService"
Cohesion: 0.22
Nodes (4): _b64url(), McpOAuthService, _origin(), _path()

### Community 46 - "make_update"
Cohesion: 0.16
Nodes (5): ConversationResolutionTests, make_update(), OpeningPromptTests, TwiMLTests, form()

### Community 47 - "build_service"
Cohesion: 0.07
Nodes (17): MeetingSegment, build_service(), ChunkingTests, CommitSegmentsTests, DeleteMeetingTests, FakeProjectDao, FinalizeTests, FollowUpTests (+9 more)

### Community 48 - "asyncio"
Cohesion: 0.03
Nodes (45): lifespan(), logout_all(), _broadcast(), face_socket(), add_sample(), create_person(), delete_person(), _enroll() (+37 more)

### Community 49 - "call_controller.py"
Cohesion: 0.09
Nodes (15): answer_call(), call_status(), _escape(), mint_relay_token(), _opening_prompt(), relay_socket(), start_turn(), run_after_previous() (+7 more)

### Community 51 - "FakeConversationService"
Cohesion: 0.09
Nodes (6): ConversationLoopLimitTests, CountingService, FakeConversationService, FakeToolDao, GlassesCannotRecordMeetingsTests, get_all()

### Community 52 - "TurnTimer"
Cohesion: 0.10
Nodes (8): _emit(), TurnTimer, _drain(), _FakeMessage, _FakeStream, _FakeUsage, TurnStreamUsageMarkTests, TurnTimerTests

### Community 53 - "test_auth_gate.py"
Cohesion: 0.10
Nodes (9): AuthGate, bearer_token(), _header(), is_exempt(), build_app(), stream(), ExemptionTests, fake_stream() (+1 more)

### Community 54 - "AuthService"
Cohesion: 0.12
Nodes (3): AuthService, _hash_token(), ConfigurationTests

### Community 55 - "SpeakOnCompletionTests"
Cohesion: 0.15
Nodes (4): no_tts(), SpeakOnCompletionTests, never_finishes(), scenario()

### Community 56 - "build_service"
Cohesion: 0.19
Nodes (4): build_service(), CreateTests, ListAndCancelTests, soon()

### Community 57 - "FakeMessage"
Cohesion: 0.09
Nodes (13): fake_stream(), fake_stream(), FakeMessage, FakeTextBlock, FakeToolUseBlock, LiveScreenTests, fake_stream(), fake_stream() (+5 more)

### Community 58 - "FakePersonaDao"
Cohesion: 0.14
Nodes (7): build_service(), CachingTests, FakePersonaDao, LoadingTests, seed_row(), ToolFacingWrapperTests, VersioningAndRollbackTests

### Community 59 - "ConversationLoopStreamTests"
Cohesion: 0.11
Nodes (5): ConversationLoopStreamTests, fake_stream(), fake_stream(), EventStreamTests, PromptSourceTests

### Community 60 - "sms_controller.py"
Cohesion: 0.16
Nodes (8): _authorize(), _handle_inbound(), inbound_sms(), inbound_sms_with_path_token(), _is_stale(), _receive(), resolve_sms_conversation(), _run_sms_turn()

### Community 61 - "SpeechPlayer"
Cohesion: 0.07
Nodes (7): MP3StreamDecoder, PlaybackWatchdog, SpeechPlayer, .isBusy, .now, Stream, PlaybackWatchdogTests

### Community 62 - "EndpointDecisionTests"
Cohesion: 0.08
Nodes (7): caption_endpoint_decision(), endpoint_decision(), EndpointDecision, _score_transcript(), silence_budget_ms(), CaptionEndpointDecisionTests, EndpointDecisionTests

### Community 63 - ".look"
Cohesion: 0.16
Nodes (11): Vision: "Hey Nova, what do you see?", Client → server, Connecting, Deviations from the brief and additions, Interjections, Prompt and tools, Server behaviour, Server → client (+3 more)

### Community 64 - "FakeCamera"
Cohesion: 0.22
Nodes (4): FakeCamera, FakeVision, settle(), VisionControllerTests

### Community 65 - "ConversationControllerTests"
Cohesion: 0.05
Nodes (14): PCMFormat, PreRollBuffer, .count, AudioFramingTests, ConversationControllerTests, ConversationControllerTests.Rig, FakePlayer, .isBusy (+6 more)

### Community 68 - "ClientEvent"
Cohesion: 0.05
Nodes (36): Phase, idle, listening, off, sentryBlocked, speaking, thinking, PhotoSlot (+28 more)

### Community 69 - "NovaGlasses"
Cohesion: 0.23
Nodes (3): AudioSessionPolicyTests, NovaGlasses, XCTest

### Community 70 - "Conversation"
Cohesion: 0.08
Nodes (5): ConversationDao, MessageDao, Conversation, Message, ConversationService

### Community 71 - "agent_loop.py"
Cohesion: 0.07
Nodes (13): PromptSourceEnum, is_sidekick_pass(), MemoryMatch, MessageRole, TurnStream, ConversationClosedError, ToolExecutionError, FakeProjectDao (+5 more)

### Community 72 - "McpServer"
Cohesion: 0.20
Nodes (3): McpServer, _now(), _parse_expiry()

### Community 74 - "TwilioService"
Cohesion: 0.09
Nodes (5): main(), report(), TwilioConfigurationError, TwilioService, ConfigurationGuardTests

### Community 75 - "HttpGateTests"
Cohesion: 0.15
Nodes (3): GateTestCase, HttpGateTests, WebSocketGateTests

### Community 77 - "sidekick_controller.py"
Cohesion: 0.06
Nodes (14): fetch(), main(), sha256(), audio_file_bytes(), is_raw_pcm(), _pcm_params(), suffix_for_mime(), transcribe_segments_serialized() (+6 more)

### Community 79 - "GateDecision"
Cohesion: 0.43
Nodes (3): GateDecision, parse_gate_reply(), GateReplyTests

### Community 80 - "is_nova_interrupt_phrase"
Cohesion: 0.18
Nodes (3): is_nova_interrupt_phrase(), NegativeMatchTests, PositiveMatchTests

### Community 81 - "FailureHistoryAndRetryTests"
Cohesion: 0.14
Nodes (4): FailureHistoryAndRetryTests, fake_stream(), fake_stream(), _FakeBadRequestError

### Community 82 - ".setUp"
Cohesion: 0.11
Nodes (11): BackgroundAgentLimitTests, never_finishes(), fake_get_response(), FakeConversationService, FakeMessage, FakeTextBlock, FakeToolDao, FakeToolUseBlock (+3 more)

### Community 83 - "FakeMcpServerDao"
Cohesion: 0.17
Nodes (3): build_service(), FakeMcpServerDao, McpServerServiceTests

### Community 86 - "SettingsService"
Cohesion: 0.12
Nodes (3): SettingsService, ModelListTests, _ResetsSharedState

### Community 87 - "CodingSession"
Cohesion: 0.17
Nodes (3): CodingSessionDao, CodingEvent, CodingSession

### Community 88 - "test_sms.py"
Cohesion: 0.13
Nodes (6): BipConfigurationError, BipRequestError, is_permanent_bip_error(), normalize_phone_number(), SmsRecipientError, NormalizationTests

### Community 89 - "test_responsibility_service.py"
Cohesion: 0.12
Nodes (3): CreateScheduleRequirementTests, FakeProjectDao, FakeUpdateService

### Community 91 - "test_deploy_main.py"
Cohesion: 0.12
Nodes (4): FailingTestsAbortTests, HappyPathTests, SpawnStaleAncestorHelperTests, WaitForPidExitTests

### Community 92 - "build_memory_service"
Cohesion: 0.26
Nodes (5): build_memory_service(), FakeEmbeddingService, FakeMemoryChunkDao, match(), RetrieveContextTests

### Community 93 - "Project"
Cohesion: 0.09
Nodes (4): ProjectDao, Project, CodeService, ProjectService

### Community 95 - "sessions.py"
Cohesion: 0.08
Nodes (10): _contained(), make_guard(), can_use_tool(), _is_prose(), health(), root(), EmbeddingService, has_be_quiet_phrase() (+2 more)

### Community 96 - "UpdateService"
Cohesion: 0.06
Nodes (5): UpdateDao, Update, _env_int(), UpdateDeliveryService, UpdateService

### Community 97 - "Mac code agent daemon"
Cohesion: 0.16
Nodes (14): Nova code agent (Mac) README, Anthropic API key stripping, Mac dials out design, Per-session git worktree, Known limits (awake Mac, bounded replay, cache cost), launchd install and menu app, Mac code agent daemon, NOVA_CODE_TOKEN shared secret (+6 more)

### Community 98 - "test_spoken_reply.py"
Cohesion: 0.13
Nodes (7): _clamp(), clamp_spoken(), _comparable(), is_repeat(), _plain_text(), ClampSpokenTests, IsRepeatTests

### Community 99 - "SpokenProse"
Cohesion: 0.19
Nodes (3): SpokenProse, _said(), SpokenProseTests

### Community 101 - "._run_begin"
Cohesion: 0.23
Nodes (6): BeginFlowTests, fake_get(), fake_post(), fake_post(), fake_post(), FakeResponse

### Community 102 - "BipService"
Cohesion: 0.13
Nodes (4): BipService, _describe_response_error(), _parse_number_list(), BodySplittingTests

### Community 105 - "asr_service.py"
Cohesion: 0.20
Nodes (8): main(), _hotwords(), _load_parakeet(), missing_cuda_libraries(), _nvidia_wheel_dll_dirs(), _platform_default_provider(), _resolve_whisper_device(), _setup_cuda_libraries()

### Community 106 - "coding_controller.py"
Cohesion: 0.14
Nodes (11): adopt_claude_thread(), _authorized(), coding_socket(), coding_status(), get_coding_session(), list_claude_threads(), list_coding_sessions(), read_claude_thread() (+3 more)

### Community 108 - "ElevenLabsService"
Cohesion: 0.21
Nodes (3): _describe_failure(), ElevenLabsService, ElevenLabsRequestTests

### Community 110 - ".deploy_main"
Cohesion: 0.15
Nodes (3): HealthTimeoutTests, StopPidTreeKillTests, DeployMainTests

### Community 111 - "FakeDao"
Cohesion: 0.18
Nodes (4): CompleteAndRefreshTests, ConnectorFilteringTests, FakeDao, oauth_server()

### Community 112 - ".run_turn"
Cohesion: 0.10
Nodes (8): MemoryInjectionTests, boom(), notification(), NotificationCapTests, NotificationCrossMediumTests, NotificationRecencyTests, NotificationScopingTests, PendingNotificationsInjectionTests

### Community 113 - "TwilioErrorClassificationTests"
Cohesion: 0.15
Nodes (6): describe_twilio_error(), is_permanent_twilio_error(), SimpleNamespace_Exception, TwilioErrorClassificationTests, reject(), flake()

### Community 114 - "HomeView"
Cohesion: 0.20
Nodes (8): HomeView, .cameraText, .connectionText, .controller, .phaseColor, .phaseLabel, .voiceModeCaption, .youSaid

### Community 115 - "asr-bench.py"
Cohesion: 0.36
Nodes (4): cut_clips(), default_audio(), load(), main()

### Community 116 - ".test_a_live_turn_reads_deltas_then_exposes_the_message"
Cohesion: 0.13
Nodes (4): TurnStreamTests, get_final_message(), __iter__(), get_final_message()

### Community 117 - "FakeAgentLoop"
Cohesion: 0.13
Nodes (3): FakeAgentLoop, SpeakQueuedLinesGatingTests, TTSProviderNeverCalledWhenSilentTests

### Community 118 - "APIClient"
Cohesion: 0.16
Nodes (7): APIClient, APIError, badResponse, .errorDescription, server, unauthorized, Person

### Community 119 - "Foundation"
Cohesion: 0.08
Nodes (12): AudioToolbox, AVFoundation, Foundation, ImageIO, AudioSessionPolicy, ImagePrep, MWDATCamera, MWDATCore (+4 more)

### Community 120 - "Earcon"
Cohesion: 0.12
Nodes (15): Earcons, Note, Earcon, cancel, done, error, shutter, sidekickCue (+7 more)

### Community 122 - "AuthStore"
Cohesion: 0.24
Nodes (3): AuthStore, .baseQuery, Security

### Community 125 - "worker.py"
Cohesion: 0.16
Nodes (10): BuildJobsTests, build_jobs(), _recover_stuck_tasks(), _run_check_for_responsibilities(), _run_check_for_stale_conversations(), _run_deliver_pending_updates(), _run_process_conversations(), _run_scheduled_tasks() (+2 more)

### Community 128 - "subprocess"
Cohesion: 0.16
Nodes (9): current_commit(), DeployError, git_pull(), git_reset_hard(), _parent_pid_map(), run_git(), run_test_suite(), spawn_stale_ancestor_helper() (+1 more)

### Community 129 - "DeployRunner"
Cohesion: 0.20
Nodes (3): DeployRunner, find_all_worker_pids(), find_worker_pid()

### Community 134 - "pending"
Cohesion: 0.27
Nodes (3): pending(), RunDueTests, RunTests

### Community 135 - "history_compaction.py"
Cohesion: 0.20
Nodes (15): _block_chars(), cap_messages(), clear_old_tool_results(), _clearable_blocks(), compact_history(), _env_int(), _is_plain_user_turn(), _history() (+7 more)

### Community 137 - "SidekickConnection"
Cohesion: 0.15
Nodes (3): Utterances, sidekick_socket(), SidekickConnection

### Community 139 - "AudioRouteManager"
Cohesion: 0.22
Nodes (3): AudioRouteManager, Route, .summary

### Community 141 - "VoiceMode"
Cohesion: 0.24
Nodes (4): VoiceMode, conversation, sentry, VoiceModeStore

### Community 142 - "requests"
Cohesion: 0.27
Nodes (7): backend_url(), close_current_conversation(), fetch_conversation_info(), fetch_health(), fetch_projects(), fetch_tools(), stream_reply()

### Community 146 - "conversation_controller.py"
Cohesion: 0.23
Nodes (6): close_conversation(), get_conversation(), get_conversation_messages(), _parse_uuid(), _project_payload(), set_conversation_silent_mode()

### Community 148 - "FakeSendWebSocket"
Cohesion: 0.14
Nodes (5): FakeSendWebSocket, InterruptAndCancelWiringTests, scenario(), scenario(), scenario()

### Community 153 - "VisionService"
Cohesion: 0.04
Nodes (18): Identification, CaptureFailed, ImageStore, _in_view_text(), is_image_block(), prepare(), VisionImage, VisionService (+10 more)

### Community 154 - "test_asr_filters.py"
Cohesion: 0.26
Nodes (4): drop_hallucination(), DropHallucinationTests, _segment(), WhisperSegmentFilterTests

### Community 155 - "MemoryChunkService"
Cohesion: 0.06
Nodes (5): MemoryChunkDao, MemoryChunkService, ParseChunksTests, SplitTranscriptTests, RetrievableQueryTests

### Community 157 - "host_environment_prompt.py"
Cohesion: 0.31
Nodes (3): host_environment_prompt(), _host_kind(), _machine_line()

### Community 158 - "PassSentinelTests"
Cohesion: 0.09
Nodes (9): FakeMessage, FakeTextBlock, FakeToolUseBlock, FakeUpdateService, _live(), get_final_message(), LookToolExclusionTests, fake_stream() (+1 more)

### Community 159 - ".__init__"
Cohesion: 0.14
Nodes (6): _build_provider(), _ChainedProvider, OpenAITTS, _cartesia(), _eleven_labs(), _mock_chain()

### Community 165 - "ClaudeCreditsService"
Cohesion: 0.14
Nodes (4): get_all_settings(), get_available_models(), get_claude_credits(), ClaudeCreditsService

### Community 170 - "worktree.py"
Cohesion: 0.22
Nodes (7): create(), _git(), remove(), resolve_repo(), slugify(), Workspace, WorktreeError

### Community 172 - "FakeHttp"
Cohesion: 0.25
Nodes (4): build_service(), FakeHttp, InfobipRequestTests, SendSmsTests

### Community 175 - "MeetingError"
Cohesion: 0.15
Nodes (7): meeting_socket(), capture_loop(), flush_tail(), send(), _transcribe_tail(), _resolve_meeting_id(), MeetingError

### Community 176 - "dict"
Cohesion: 0.25
Nodes (3): basic(), InboundSecretTests, RecipientAllowlistTests

### Community 179 - "SentryModeTests"
Cohesion: 0.09
Nodes (3): SentryModeTests, WakePhraseAloneTests, WakeStraightToListeningTests

### Community 181 - "AddPersonView"
Cohesion: 0.13
Nodes (11): .api, NovaGlassesApp, .body, RootView, AudioLogView, AddPersonView, .body, FacesView (+3 more)

### Community 183 - ".setUp"
Cohesion: 0.13
Nodes (3): fake_transcribe(), FakeGate, FakeSidekickLoop

### Community 184 - "test_scheduled_task_service.py"
Cohesion: 0.15
Nodes (4): CurrentTimeTests, FakeProjectDao, FakeUpdateService, RecoverStuckTests

### Community 186 - "os"
Cohesion: 0.06
Nodes (18): _flag(), _allowed_origins(), main(), one_call(), main(), one_call(), variants(), _build_file_logger() (+10 more)

### Community 191 - "MacSessionLifecycleTests"
Cohesion: 0.10
Nodes (3): MacConcurrentSessionTests, MacSessionLifecycleTests, sink()

### Community 196 - "InterruptedToolCallTests"
Cohesion: 0.19
Nodes (3): InterruptedToolCallTests, fake_stream(), _call()

### Community 198 - "speech_summary"
Cohesion: 0.12
Nodes (3): speech_summary(), GlassesPromptSourceTests, SpeechSummaryTests

### Community 199 - "test_auth_service.py"
Cohesion: 0.12
Nodes (6): AuthNotConfigured, BadCredentials, LockedOut, _now(), LockoutTests, LoginTests

### Community 205 - "FaceService"
Cohesion: 0.05
Nodes (12): PersonDao, Person, FaceService, GalleryPerson, match(), _normalise(), face_row(), FaceServiceTests (+4 more)

### Community 207 - "_FakeTable"
Cohesion: 0.17
Nodes (3): _FakeResponse, _FakeSupabaseClient, _FakeTable

### Community 218 - "NovaGlasses"
Cohesion: 0.29
Nodes (6): Build and test (CLI), Code map, How it behaves, Install on your iPhone, NovaGlasses, On-device field checklist

### Community 226 - "build_service"
Cohesion: 0.17
Nodes (3): build_service(), ResponsibilityDeliveryTests, WindowTests

### Community 231 - "Entry"
Cohesion: 0.36
Nodes (3): AudioLog, Entry, .body

## Ambiguous Edges - Review These
- `TTS conversion enhancer prompt (empty)` → `Voice mode tone guidelines`  [AMBIGUOUS]
  prompting/tts_conversion_enhancer_prompt.txt · relation: conceptually_related_to

## Knowledge Gaps
- **165 isolated node(s):** `UserNotifications`, `.serverURLString`, `.summary`, `AudioToolbox`, `.count` (+160 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1767 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **102 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `TTS conversion enhancer prompt (empty)` and `Voice mode tone guidelines`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `NovaGlasses` connect `NovaGlasses` to `AmbientForwardingTests`, `ConversationController`, `.look`?**
  _High betweenness centrality (0.320) - this node is a cross-community bridge._
- **Are the 45 inferred relationships involving `AgentLoop` (e.g. with `Server behaviour` and `PromptEnums`) actually correct?**
  _`AgentLoop` has 45 INFERRED edges - model-reasoned connections that need verification._
- **What connects `UserNotifications`, `.serverURLString`, `.summary` to the rest of the system?**
  _165 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `ToolService` be split into smaller, more focused modules?**
  _Cohesion score 0.13360323886639677 - nodes in this community are weakly interconnected._
- **Why does `Vision: "Hey Nova, what do you see?"` connect `.look` to `NovaGlasses`?**
  _High betweenness centrality (0.318) - this node is a cross-community bridge._
- **Are the 22 inferred relationships involving `Conversation` (e.g. with `_is_stale()` and `ConversationDao`) actually correct?**
  _`Conversation` has 22 INFERRED edges - model-reasoned connections that need verification._