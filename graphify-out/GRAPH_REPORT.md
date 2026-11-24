# Graph Report - silent-mode-backend  (2026-11-24)

## Corpus Check
- 243 files · ~228,580 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 12 file(s) not represented in the graph (top: (none) 4, .mdc 1, .pbxproj 1)

## Summary
- 5572 nodes · 13031 edges · 248 communities (145 shown, 103 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 1389 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `a2c78d50`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- ToolExecutionError
- transcribe_socket
- SimpleFinancesService
- text
- TranscribeSocketTests
- test_openai_loop.py
- vision_service.py
- test_vision.py
- .run_agent
- ._env
- make_update
- ClaudeService
- GithubService
- build_service
- Nova system prompt (persona)
- SidekickController
- clamp_spoken
- Harness
- CodingService
- ScheduledTask
- _most_recent_local_midnight_utc
- test_meeting_service.py
- process_supervisor.py
- build_service
- ReportType
- CursorService
- MeetingService
- FileOperationTests
- AppModel
- Meeting
- ConversationController
- Keys
- deploy_main.py
- test_auth_service.py
- LiveReply
- auth_controller.py
- SessionManager
- _runner
- _silent_logger
- json
- DATGlassesCamera
- VisionService
- AgentLoopMcpTests
- ResponsibilityService
- Responsibility
- McpOAuthService
- make_update
- build_service
- asyncio
- call_controller.py
- McpServerService
- ToolService
- TurnTimer
- AuthService
- auth_service.py
- SpeakOnCompletionTests
- build_service
- FakeTextBlock
- FakePersonaDao
- ConversationLoopStreamTests
- normalize_phone_number
- SpeechPlayer
- endpoint_decision
- .look
- FakeCamera
- ConversationControllerTests
- ._artifact_for_tool
- BaseDao
- ServerEvent
- XCTestCase
- Conversation
- os
- McpServer
- PersonaService
- TwilioService
- HttpGateTests
- AgentLoop
- audio_ws.py
- Tool
- GateDecision
- is_nova_interrupt_phrase
- FailureHistoryAndRetryTests
- test_background_agent.py
- FakeMcpServerDao
- FakeMeetingDao
- CrudTests
- ModelListTests
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
- post
- CompletionNotificationTests
- ElevenLabsService
- .repair_tool_pairing
- .deploy_main
- FakeDao
- .run_turn
- TwilioErrorClassificationTests
- Person
- pathlib
- .test_a_live_turn_reads_deltas_then_exposes_the_message
- FakeAgentLoop
- APIClient
- Foundation
- Earcon
- SidekickSocketTests
- FakeSocket
- EndSessionTests
- SidekickSession
- worker.py
- DeployService
- email_service.py
- __main__.py
- FakeMessage
- FakeDao
- ClassificationTests
- TurnStream
- EndpointDecisionTests
- pending
- history_compaction.py
- AsrLock
- SidekickConnection
- WorkingTreeTests
- .add
- SpeechWakeDetector
- .durationMs
- requests
- PerformTests
- run_migrations.py
- SilentModeStatePushTests
- get_conversation_messages
- time
- FakeSendWebSocket
- FallbackChainTests
- SpokenTrackTests
- Rig
- LiveScreenTests
- ImageStore
- test_asr_filters.py
- MemoryChunkService
- Hosting Nova off the home network
- host_environment_prompt.py
- PassSentinelTests
- TTSService
- CLAUDE.md
- split_wake_phrase
- install.sh
- uninstall.sh
- settings_controller.py
- nova-backend
- worktree.py
- SettingsService
- FakeHttp
- CommandLineService
- DemoService
- MeetingError
- dict
- RelayTokenTests
- VisionRoutesTests
- SentryModeTests
- MirrorTests
- AddPersonView
- PersonaPrompt
- .setUp
- ScheduledTaskService
- shell.py
- replay_request.py
- fake_stream
- SelfKillHazardTests
- SpawnStaleAncestorHelperTimingTests
- HostEnvironmentPromptTests
- MacSessionLifecycleTests
- ReportMediumTests
- .wantsToSee
- GoodbyeTimingTests
- .handle_user_message
- InterruptedToolCallTests
- CooldownTests
- speech_summary
- LockoutTests
- GuardrailTests
- FakeUpdateService
- MacShellTests
- ._to_dict
- FaceService
- AgentLink
- _FakeTable
- FakeConversationService
- FakeTaskDao
- FakeResponse
- FinishedSessionTowerTests
- ReplyTests
- MeetingSegment
- FallbackTests
- PromptSourceTests
- FakeResponsibilityDao
- ToolServiceTests
- NovaGlasses
- _PassHold
- SidekickService
- .start
- WorktreeCollisionTests
- test_persona_service.py
- .iter_sentence_chunks
- ResponsibilityDeliveryTests
- ProviderSelectionTests
- Link
- protocol.py
- .split_sms_body
- test_settings_service.py
- _said
- FakeAgentLoop
- CreateScheduleRequirementTests
- TranscribeUtteranceTests
- ServiceMethodToolConfig
- ToolRegistrationTests
- get_nova_power
- .test_a_live_turn_refuses_a_second_read
- SilentModeStateOnConnectTests
- ToolUseStarted
- WebSocketGateTests
- LoginTests
- ConversationLoopLimitTests
- make_request

## God Nodes (most connected - your core abstractions)
1. `AgentLoop` - 135 edges
2. `Conversation` - 94 edges
3. `ConversationController` - 85 edges
4. `ToolService` - 72 edges
5. `build_service()` - 57 edges
6. `ConversationService` - 56 edges
7. `CodingService` - 55 edges
8. `Responsibility` - 54 edges
9. `MeetingService` - 52 edges
10. `UpdateService` - 50 edges

## Surprising Connections (you probably didn't know these)
- `Server behaviour` --references--> `audio_file_bytes()`  [INFERRED]
  SIDEKICK_PROTOCOL.md → src/controller/audio_ws.py
- `Server → client` --references--> `stream_tts_audio()`  [INFERRED]
  SIDEKICK_PROTOCOL.md → src/controller/nova_controller.py
- `Server behaviour` --references--> `AgentLoop`  [INFERRED]
  SIDEKICK_PROTOCOL.md → src/harness/agent_loop.py
- `Tests` --references--> `is_nova_interrupt_phrase()`  [INFERRED]
  SIDEKICK_PROTOCOL.md → src/service/interrupt_service.py
- `Interjections` --references--> `text()`  [INFERRED]
  SIDEKICK_PROTOCOL.md → tests/test_sms_controller.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Remote access path: Firebase frontend to Cloudflare Tunnel to tower API** — docs_hosting_firebase_hosting, docs_hosting_cloudflare_tunnel, docs_hosting_tower_api [EXTRACTED 0.95]
- **Mac agent core design principles** — mac_agent_readme_dial_out, mac_agent_readme_sessions_as_threads, mac_agent_readme_git_worktree [EXTRACTED 1.00]
- **Persisted-action safety rules across foreground and background agents** — prompting_nova_persona_prompt_confirm_persisted_actions, prompting_nova_persona_prompt_clarify_before_executing, prompting_background_agent_prompt_no_outward_actions [INFERRED 0.85]

## Communities (248 total, 103 thin omitted)

### Community 0 - "ToolExecutionError"
Cohesion: 0.28
Nodes (5): main(), main(), main(), main(), ToolExecutionError

### Community 1 - "transcribe_socket"
Cohesion: 0.14
Nodes (12): idle_stopped_event(), parse_image_ids(), _partial_is_due(), send_assistant_text(), _send_locked(), _speculative_asr_enabled(), stream_tts_audio(), transcribe_socket() (+4 more)

### Community 2 - "SimpleFinancesService"
Cohesion: 0.11
Nodes (6): SimplApiError, SimplConfigurationError, SimpleFinancesService, response(), SimpleFinancesServiceTest, SimplFinancesToolRegistrationTest

### Community 3 - "text"
Cohesion: 0.16
Nodes (5): AuthenticationTests, forward(), PathTokenRouteTests, SenderGateTests, text()

### Community 5 - "test_openai_loop.py"
Cohesion: 0.16
Nodes (7): FakeClient, FakeFunctionCall, FakeResponse, FakeResponsesAPI, FakeTool, FakeToolService, OpenAILoopTests

### Community 6 - "vision_service.py"
Cohesion: 0.07
Nodes (18): add_sample(), create_person(), delete_person(), _enroll(), list_people(), capture_failed(), read_jpeg_body(), upload_image() (+10 more)

### Community 7 - "test_vision.py"
Cohesion: 0.15
Nodes (6): AgentLoopImageTests, fake_stream(), FakeConversationService, FakeMessage, FakeTextBlock, FakeToolUseBlock

### Community 8 - ".run_agent"
Cohesion: 0.07
Nodes (4): BackgroundAgentTests, MultiChannelReportTypeTests, ReportTypeTests, ResponsibilityRunToolRestrictionTests

### Community 10 - "make_update"
Cohesion: 0.12
Nodes (10): at(), build_service(), CallDeliveryTests, EmailDeliveryTests, make_update(), MultiChannelDeliveryTests, QuietHoursTests, SettleCallTests (+2 more)

### Community 11 - "ClaudeService"
Cohesion: 0.09
Nodes (6): Server behaviour, _env_flag(), ClaudeService, _maybe_print_prompt(), GenerationKwargsTests, ClaudeServiceMcpKwargsTests

### Community 12 - "GithubService"
Cohesion: 0.15
Nodes (4): GithubService, GithubServiceError, _FakeResponse, GithubServiceTests

### Community 13 - "build_service"
Cohesion: 0.05
Nodes (10): build_service(), CreateUpdateTests, FakeConversationDao, FakeProjectDao, FakeUpdateDao, make_update(), MultiChannelReportTypeTests, NotificationQueueFieldsTests (+2 more)

### Community 14 - "Nova system prompt (persona)"
Cohesion: 0.11
Nodes (15): Background agent prompt, Meeting follow-up prompt, Notify decision (email vs call), Meeting notes prompt, Meeting notes JSON output (title, summary, decisions, action items), Nova system prompt (persona), About Nate (user profile), agent_loop.py core tool-calling loop (+7 more)

### Community 15 - "SidekickController"
Cohesion: 0.08
Nodes (15): Cancellable, ConversationIdStore, EarconPlaying, GlassesCamera, Handle, MainScheduler, NovaSocketing, Scheduling (+7 more)

### Community 16 - "clamp_spoken"
Cohesion: 0.23
Nodes (5): deliver(), mark_first_speech(), _clamp(), clamp_spoken(), ClampSpokenTests

### Community 17 - "Harness"
Cohesion: 0.08
Nodes (15): LevelSmoother, Snapshot, State, calibrating, cooldown, idle, onset, speaking (+7 more)

### Community 19 - "ScheduledTask"
Cohesion: 0.12
Nodes (3): ScheduledTaskDao, ScheduledTask, TaskStatus

### Community 20 - "_most_recent_local_midnight_utc"
Cohesion: 0.07
Nodes (7): _most_recent_local_midnight_utc(), IsIdleTests, IsPastRolloverTests, build_service(), CheckForStaleConversationsTests, FakeConversationDao, MostRecentLocalMidnightUtcTests

### Community 21 - "test_meeting_service.py"
Cohesion: 0.06
Nodes (9): FakeAgentLoop, FakeChunkDao, FakeClaudeService, FakeConversationDao, FakeEmbeddingService, FakeNotesDao, FakeUpdateService, RecoveryTests (+1 more)

### Community 22 - "process_supervisor.py"
Cohesion: 0.10
Nodes (18): _all(), await_ready(), check(), classify(), _entry(), kill_tree(), _log_paths(), pid_alive() (+10 more)

### Community 23 - "build_service"
Cohesion: 0.07
Nodes (11): build_service(), FakeClaudeService, FakeConversationService, FakeEmbeddingService, FakeMemoryChunkDao, FetchMemoryTests, ProcessConversationsTests, boom() (+3 more)

### Community 24 - "ReportType"
Cohesion: 0.10
Nodes (9): DeliveryStatus, encode_report_types(), normalize_report_types(), ReportType, EscapingTests, BadgeOnlyTests, SmsPermanentFailureTests, UndeliverableTypeTests (+1 more)

### Community 25 - "CursorService"
Cohesion: 0.17
Nodes (4): CursorService, CursorServiceError, CursorServiceTests, _FakeResponse

### Community 26 - "MeetingService"
Cohesion: 0.07
Nodes (3): MeetingChunk, MeetingNotes, MeetingService

### Community 27 - "FileOperationTests"
Cohesion: 0.09
Nodes (3): EditTests, FileOperationTests, PathContainmentTests

### Community 28 - "AppModel"
Cohesion: 0.06
Nodes (21): AppModel, .serverURLString, NovaGlassesApp, .body, RootView, .body, AuthStore, .baseQuery (+13 more)

### Community 29 - "Meeting"
Cohesion: 0.09
Nodes (3): MeetingDao, Meeting, MeetingStatus

### Community 30 - "ConversationController"
Cohesion: 0.09
Nodes (11): Capture, ConversationController, .currentConversationId, .idleMessage, .isEnabled, .isWorking, .wakeWatching, Once (+3 more)

### Community 31 - "Keys"
Cohesion: 0.08
Nodes (23): Keys, assistantText, bytes, chunkBase64, client, code, conversationId, count (+15 more)

### Community 32 - "deploy_main.py"
Cohesion: 0.07
Nodes (25): build_logger(), check_health_once(), current_commit(), DeployConfig, DeployError, DeployRunner, _ensure_single_healthy_api(), find_all_pids_on_port() (+17 more)

### Community 33 - "test_auth_service.py"
Cohesion: 0.09
Nodes (4): NovaSessionDao, row_to_session(), NovaSession, RowConversionTests

### Community 35 - "auth_controller.py"
Cohesion: 0.15
Nodes (8): _client_ip(), current_session(), list_sessions(), login(), logout(), AuthNotConfigured, BadCredentials, LockedOut

### Community 36 - "SessionManager"
Cohesion: 0.14
Nodes (3): _flatten(), Session, SessionManager

### Community 37 - "_runner"
Cohesion: 0.12
Nodes (5): DryRunTests, LeftoverSweepTests, RollbackPathTests, _runner(), SweepHandsOffStaleAncestorsTests

### Community 38 - "_silent_logger"
Cohesion: 0.12
Nodes (4): EnsureSingleHealthyApiTests, HelperModeCliTests, RunStaleAncestorHelperTests, _silent_logger()

### Community 39 - "json"
Cohesion: 0.16
Nodes (16): _all(), await_ready(), check(), _entry(), kill_tree(), _log_paths(), pid_alive(), port_open() (+8 more)

### Community 40 - "DATGlassesCamera"
Cohesion: 0.07
Nodes (15): CameraError, .errorDescription, failed, glassesAudioNotUp, noCamera, notReady, timeout, DATGlassesCamera (+7 more)

### Community 41 - "VisionService"
Cohesion: 0.10
Nodes (4): _in_view_text(), is_image_block(), VisionService, LookToolTests

### Community 42 - "AgentLoopMcpTests"
Cohesion: 0.12
Nodes (10): AgentLoopMcpTests, fake_stream(), fake_stream(), ConversationTurnMcpDisabledReplayTests, fake_stream(), FakeBlock, FakeConversationService, FakeMcpService (+2 more)

### Community 44 - "Responsibility"
Cohesion: 0.21
Nodes (4): Responsibility, at(), CheckForResponsibilitiesTests, DueTests

### Community 45 - "McpOAuthService"
Cohesion: 0.22
Nodes (4): _b64url(), McpOAuthService, _origin(), _path()

### Community 46 - "make_update"
Cohesion: 0.16
Nodes (5): ConversationResolutionTests, make_update(), OpeningPromptTests, TwiMLTests, form()

### Community 47 - "build_service"
Cohesion: 0.09
Nodes (12): build_service(), ChunkingTests, CommitSegmentsTests, DeleteMeetingTests, FakeProjectDao, FollowUpTests, explode(), recording_meeting() (+4 more)

### Community 48 - "asyncio"
Cohesion: 0.06
Nodes (18): _allowed_origins(), lifespan(), _broadcast(), face_socket(), _callback_page(), create_mcp_server(), delete_mcp_server(), list_mcp_servers() (+10 more)

### Community 49 - "call_controller.py"
Cohesion: 0.09
Nodes (14): answer_call(), call_status(), _escape(), mint_relay_token(), _opening_prompt(), relay_socket(), start_turn(), run_after_previous() (+6 more)

### Community 51 - "ToolService"
Cohesion: 0.11
Nodes (6): ToolService, CountingService, FakeConversationService, FakeToolDao, GlassesCannotRecordMeetingsTests, get_all()

### Community 52 - "TurnTimer"
Cohesion: 0.10
Nodes (8): _emit(), TurnTimer, _drain(), _FakeMessage, _FakeStream, _FakeUsage, TurnStreamUsageMarkTests, TurnTimerTests

### Community 53 - "AuthService"
Cohesion: 0.09
Nodes (8): AuthGate, bearer_token(), _header(), is_exempt(), AuthService, build_app(), ExemptionTests, SidekickAuthTests

### Community 54 - "auth_service.py"
Cohesion: 0.15
Nodes (3): _hash_token(), _now(), ConfigurationTests

### Community 55 - "SpeakOnCompletionTests"
Cohesion: 0.14
Nodes (4): no_tts(), SpeakOnCompletionTests, never_finishes(), scenario()

### Community 56 - "build_service"
Cohesion: 0.14
Nodes (6): build_service(), CreateTests, FakeProjectDao, FakeUpdateService, ListAndCancelTests, soon()

### Community 58 - "FakePersonaDao"
Cohesion: 0.14
Nodes (7): build_service(), CachingTests, FakePersonaDao, LoadingTests, seed_row(), ToolFacingWrapperTests, VersioningAndRollbackTests

### Community 59 - "ConversationLoopStreamTests"
Cohesion: 0.16
Nodes (4): ConversationLoopStreamTests, fake_stream(), fake_stream(), EventStreamTests

### Community 60 - "normalize_phone_number"
Cohesion: 0.25
Nodes (4): _handle_inbound(), normalize_phone_number(), SmsRecipientError, NormalizationTests

### Community 61 - "SpeechPlayer"
Cohesion: 0.07
Nodes (7): MP3StreamDecoder, PlaybackWatchdog, SpeechPlayer, .isBusy, .now, Stream, PlaybackWatchdogTests

### Community 62 - "endpoint_decision"
Cohesion: 0.13
Nodes (6): caption_endpoint_decision(), endpoint_decision(), EndpointDecision, _score_transcript(), silence_budget_ms(), CaptionEndpointDecisionTests

### Community 63 - ".look"
Cohesion: 0.16
Nodes (10): Vision: "Hey Nova, what do you see?", Client → server, Connecting, Deviations from the brief and additions, Interjections, Prompt and tools, Server → client, Sidekick protocol: `WS /ws/sidekick` (+2 more)

### Community 64 - "FakeCamera"
Cohesion: 0.21
Nodes (4): FakeCamera, FakeVision, settle(), VisionControllerTests

### Community 67 - "BaseDao"
Cohesion: 0.08
Nodes (6): BaseDao, MeetingChunkDao, MeetingNotesDao, MemoryChunkDao, MemoryChunk, MemoryMatch

### Community 68 - "ServerEvent"
Cohesion: 0.03
Nodes (68): Note, Phase, idle, listening, off, sentryBlocked, speaking, thinking (+60 more)

### Community 69 - "XCTestCase"
Cohesion: 0.08
Nodes (8): AudioSessionPolicyTests, AmbientForwardingTests, ThinkingPulseTests, WakePhraseAloneTests, WakeStraightToListeningTests, What is verified and what is not, NovaGlasses, XCTest

### Community 70 - "Conversation"
Cohesion: 0.05
Nodes (7): ConversationDao, Conversation, ConversationService, PrefetchedConversationTests, FakeConversationService, ConversationControllerSilentModeTests, ThreadResolutionTests

### Community 71 - "os"
Cohesion: 0.04
Nodes (30): PromptSourceEnum, _run_turn(), _canonical_wake_text(), has_stop_phrase(), normalize_wake_text(), voice_prompt_source(), _is_stale(), resolve_sms_conversation() (+22 more)

### Community 72 - "McpServer"
Cohesion: 0.20
Nodes (3): McpServer, _now(), _parse_expiry()

### Community 74 - "TwilioService"
Cohesion: 0.09
Nodes (5): main(), report(), TwilioConfigurationError, TwilioService, ConfigurationGuardTests

### Community 76 - "AgentLoop"
Cohesion: 0.03
Nodes (7): AgentLoop, persist(), _memory_block_budget_seconds(), strip_expects_reply(), _strip_expects_reply_events(), GlassesPromptSourceTests, SanitizeMcpHistoryTests

### Community 77 - "audio_ws.py"
Cohesion: 0.13
Nodes (10): audio_file_bytes(), is_raw_pcm(), _pcm_params(), suffix_for_mime(), transcribe_serialized(), emit_partial_transcript(), run_speculative_transcription(), _remove() (+2 more)

### Community 78 - "Tool"
Cohesion: 0.15
Nodes (4): list_tools(), ToolDao, Tool, FakeToolDao

### Community 79 - "GateDecision"
Cohesion: 0.23
Nodes (4): GateDecision, parse_gate_reply(), SidekickGate, GateReplyTests

### Community 80 - "is_nova_interrupt_phrase"
Cohesion: 0.15
Nodes (4): is_nova_interrupt_phrase(), _normalize_tokens(), NegativeMatchTests, PositiveMatchTests

### Community 82 - "test_background_agent.py"
Cohesion: 0.12
Nodes (12): BackgroundAgentLimitTests, never_finishes(), fake_get_response(), FakeConversationService, FakeMessage, FakeProjectDao, FakeTextBlock, FakeToolDao (+4 more)

### Community 83 - "FakeMcpServerDao"
Cohesion: 0.17
Nodes (3): build_service(), FakeMcpServerDao, McpServerServiceTests

### Community 87 - "CodingSession"
Cohesion: 0.15
Nodes (4): CodingSessionDao, CodingEvent, CodingSession, CodingStatus

### Community 88 - "test_sms.py"
Cohesion: 0.17
Nodes (4): BipConfigurationError, BipRequestError, is_permanent_bip_error(), user_phone_number()

### Community 89 - "test_responsibility_service.py"
Cohesion: 0.14
Nodes (4): build_service(), FakeProjectDao, FakeUpdateService, WindowTests

### Community 90 - "StreamedSpeechTests"
Cohesion: 0.27
Nodes (3): stream(), StreamedSpeechTests, fake_stream()

### Community 91 - "test_deploy_main.py"
Cohesion: 0.12
Nodes (4): FailingTestsAbortTests, HappyPathTests, SpawnStaleAncestorHelperTests, WaitForPidExitTests

### Community 92 - "build_memory_service"
Cohesion: 0.26
Nodes (5): build_memory_service(), FakeEmbeddingService, FakeMemoryChunkDao, match(), RetrieveContextTests

### Community 93 - "Project"
Cohesion: 0.06
Nodes (8): ProjectDao, Project, CodeService, ProjectService, CodeServiceTestCase, FakeConversationDao, FakeProjectDao, ProjectResolutionTests

### Community 95 - "sessions.py"
Cohesion: 0.12
Nodes (8): _contained(), make_guard(), can_use_tool(), _as_int(), _is_prose(), _ms_to_iso(), health(), root()

### Community 96 - "UpdateService"
Cohesion: 0.06
Nodes (5): UpdateDao, Update, _env_int(), UpdateDeliveryService, UpdateService

### Community 97 - "Mac code agent daemon"
Cohesion: 0.16
Nodes (14): Nova code agent (Mac) README, Anthropic API key stripping, Mac dials out design, Per-session git worktree, Known limits (awake Mac, bounded replay, cache cost), launchd install and menu app, Mac code agent daemon, NOVA_CODE_TOKEN shared secret (+6 more)

### Community 98 - "test_spoken_reply.py"
Cohesion: 0.16
Nodes (6): _comparable(), is_repeat(), _plain_text(), strip_speak_tags(), IsRepeatTests, StripSpeakTagsTests

### Community 101 - "._run_begin"
Cohesion: 0.23
Nodes (6): BeginFlowTests, fake_get(), fake_post(), fake_post(), fake_post(), FakeResponse

### Community 102 - "BipService"
Cohesion: 0.17
Nodes (3): BipService, _describe_response_error(), _parse_number_list()

### Community 104 - "Rig"
Cohesion: 0.18
Nodes (3): Rig, SidekickControllerTests, SidekickEventCodingTests

### Community 105 - "asr_service.py"
Cohesion: 0.20
Nodes (8): main(), _hotwords(), _load_parakeet(), missing_cuda_libraries(), _nvidia_wheel_dll_dirs(), _platform_default_provider(), _resolve_whisper_device(), _setup_cuda_libraries()

### Community 106 - "post"
Cohesion: 0.09
Nodes (18): logout_all(), adopt_claude_thread(), _authorized(), coding_socket(), coding_status(), get_coding_session(), list_claude_threads(), list_coding_sessions() (+10 more)

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

### Community 114 - "Person"
Cohesion: 0.11
Nodes (3): PersonDao, Person, FakePersonDao

### Community 115 - "pathlib"
Cohesion: 0.18
Nodes (4): cut_clips(), default_audio(), load(), main()

### Community 117 - "FakeAgentLoop"
Cohesion: 0.13
Nodes (3): FakeAgentLoop, SpeakQueuedLinesGatingTests, TTSProviderNeverCalledWhenSilentTests

### Community 118 - "APIClient"
Cohesion: 0.16
Nodes (7): APIClient, APIError, badResponse, .errorDescription, server, unauthorized, Person

### Community 119 - "Foundation"
Cohesion: 0.05
Nodes (15): AudioToolbox, AVFoundation, Foundation, ImageIO, AudioSessionPolicy, CaptureEngine, FrameConverter, ImagePrep (+7 more)

### Community 120 - "Earcon"
Cohesion: 0.13
Nodes (14): Earcons, Earcon, cancel, done, error, shutter, sidekickCue, sidekickOff (+6 more)

### Community 122 - "FakeSocket"
Cohesion: 0.13
Nodes (5): FakePlayer, .isBusy, FakeSocket, .starts, FakeWake

### Community 125 - "worker.py"
Cohesion: 0.16
Nodes (10): BuildJobsTests, build_jobs(), _recover_stuck_tasks(), _run_check_for_responsibilities(), _run_check_for_stale_conversations(), _run_deliver_pending_updates(), _run_process_conversations(), _run_scheduled_tasks() (+2 more)

### Community 128 - "__main__.py"
Cohesion: 0.13
Nodes (7): Config, _flag(), load_env_file(), _configure_logging(), main(), _run(), _task()

### Community 129 - "FakeMessage"
Cohesion: 0.17
Nodes (9): FakeMessage, fake_stream(), fake_stream(), fake_stream(), fake_stream(), StatusTextTests, fake_stream(), fake_stream() (+1 more)

### Community 130 - "FakeDao"
Cohesion: 0.10
Nodes (4): GateTestCase, AuthenticateTests, AuthServiceTestCase, FakeDao

### Community 132 - "TurnStream"
Cohesion: 0.11
Nodes (10): chat_stream(), event_source(), parse_conversation_id(), resolve_chat_request(), sse_event(), MessageDao, Message, TurnStream (+2 more)

### Community 134 - "pending"
Cohesion: 0.21
Nodes (4): pending(), RecoverStuckTests, RunDueTests, RunTests

### Community 135 - "history_compaction.py"
Cohesion: 0.20
Nodes (15): _block_chars(), cap_messages(), clear_old_tool_results(), _clearable_blocks(), compact_history(), _env_int(), _is_plain_user_turn(), _history() (+7 more)

### Community 137 - "SidekickConnection"
Cohesion: 0.15
Nodes (3): Utterances, sidekick_socket(), SidekickConnection

### Community 139 - ".add"
Cohesion: 0.13
Nodes (6): AudioLog, Entry, AudioRouteManager, Route, .summary, .body

### Community 140 - "SpeechWakeDetector"
Cohesion: 0.13
Nodes (4): SpeechWakeDetector, .isAvailable, WakePhrase, WakePhraseTests

### Community 141 - ".durationMs"
Cohesion: 0.19
Nodes (4): PCMFormat, PreRollBuffer, .count, AudioFramingTests

### Community 142 - "requests"
Cohesion: 0.27
Nodes (7): backend_url(), close_current_conversation(), fetch_conversation_info(), fetch_health(), fetch_projects(), fetch_tools(), stream_reply()

### Community 144 - "run_migrations.py"
Cohesion: 0.16
Nodes (4): main(), migration_files(), _jsonable(), SQLService

### Community 145 - "SilentModeStatePushTests"
Cohesion: 0.11
Nodes (3): build_service(), SilentModeServiceTests, SilentModeStatePushTests

### Community 146 - "get_conversation_messages"
Cohesion: 0.20
Nodes (6): close_conversation(), get_conversation(), get_conversation_messages(), _parse_uuid(), _project_payload(), set_conversation_silent_mode()

### Community 147 - "time"
Cohesion: 0.17
Nodes (4): _timestamp(), fetch(), main(), sha256()

### Community 148 - "FakeSendWebSocket"
Cohesion: 0.14
Nodes (5): FakeSendWebSocket, InterruptAndCancelWiringTests, scenario(), scenario(), scenario()

### Community 151 - "Rig"
Cohesion: 0.28
Nodes (4): ConversationControllerTests.Rig, Item, ManualScheduler, Rig

### Community 153 - "ImageStore"
Cohesion: 0.12
Nodes (5): ImageStore, VisionImage, GlassesSocketTests, ContentBlocksTests, ImageStoreTests

### Community 154 - "test_asr_filters.py"
Cohesion: 0.26
Nodes (4): drop_hallucination(), DropHallucinationTests, _segment(), WhisperSegmentFilterTests

### Community 155 - "MemoryChunkService"
Cohesion: 0.07
Nodes (4): EmbeddingService, MemoryChunkService, ParseChunksTests, RetrievableQueryTests

### Community 156 - "Hosting Nova off the home network"
Cohesion: 0.21
Nodes (13): Hosting Nova off the home network, Backend environment variables, Cloudflare Tunnel (nova-tower, cloudflared), Firebase Hosting frontend (nova-voice-nd.web.app), Infobip SMS integration (/sms/inbound), Failed-login lockout policy, Mac coding agent (/ws/coding), MCP OAuth callback (+5 more)

### Community 157 - "host_environment_prompt.py"
Cohesion: 0.31
Nodes (3): host_environment_prompt(), _host_kind(), _machine_line()

### Community 158 - "PassSentinelTests"
Cohesion: 0.09
Nodes (10): _agent_loop(), FakeMessage, FakeTextBlock, FakeToolDao, FakeToolUseBlock, FakeUpdateService, _live(), LookToolExclusionTests (+2 more)

### Community 159 - "TTSService"
Cohesion: 0.12
Nodes (7): _build_provider(), _ChainedProvider, OpenAITTS, TTSService, _cartesia(), _eleven_labs(), _mock_chain()

### Community 161 - "split_wake_phrase"
Cohesion: 0.23
Nodes (4): has_wake_phrase(), split_wake_phrase(), SplitWakePhraseTests, WakePhraseTests

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

### Community 175 - "MeetingError"
Cohesion: 0.07
Nodes (19): transcribe_segments_serialized(), delete_meeting(), get_active_meeting(), get_meeting(), get_meeting_segments(), list_meetings(), _meeting_error(), meeting_socket() (+11 more)

### Community 176 - "dict"
Cohesion: 0.23
Nodes (3): basic(), InboundSecretTests, SenderAllowlistTests

### Community 178 - "VisionRoutesTests"
Cohesion: 0.26
Nodes (3): Identification, FakeFaceService, VisionRoutesTests

### Community 181 - "AddPersonView"
Cohesion: 0.12
Nodes (7): .api, VisionClient, AddPersonView, .body, FacesView, .body, PhotosUI

### Community 183 - ".setUp"
Cohesion: 0.12
Nodes (4): DirectTurnCounterTests, fake_transcribe(), FakeGate, FakeSidekickLoop

### Community 185 - "shell.py"
Cohesion: 0.27
Nodes (5): classify(), _clip(), _resolve_cwd(), run(), _scratch_pair()

### Community 186 - "replay_request.py"
Cohesion: 0.20
Nodes (5): main(), one_call(), main(), one_call(), variants()

### Community 187 - "fake_stream"
Cohesion: 0.11
Nodes (6): fake_stream(), fake_stream(), fake_stream(), fake_stream(), FailureSpeechTests, _FakeBadRequestError

### Community 191 - "MacSessionLifecycleTests"
Cohesion: 0.10
Nodes (3): MacConcurrentSessionTests, MacSessionLifecycleTests, sink()

### Community 196 - "InterruptedToolCallTests"
Cohesion: 0.26
Nodes (3): FakeToolUseBlock, InterruptedToolCallTests, _call()

### Community 205 - "FaceService"
Cohesion: 0.09
Nodes (9): FaceService, GalleryPerson, match(), _normalise(), face_row(), FaceServiceTests, FacesRoutesTests, MatchTests (+1 more)

### Community 207 - "_FakeTable"
Cohesion: 0.13
Nodes (4): CheckForStaleConversationsLoopTests, _FakeResponse, _FakeSupabaseClient, _FakeTable

### Community 208 - "FakeConversationService"
Cohesion: 0.12
Nodes (6): FakeConversationService, FakeMessage, FakeTextBlock, FakeToolDao, FakeUpdateService, fake_stream()

### Community 213 - "MeetingSegment"
Cohesion: 0.15
Nodes (5): MeetingSegment, FinalizeTests, NotesTests, NotesUseNoToolsTests, TranscriptTests

### Community 218 - "NovaGlasses"
Cohesion: 0.29
Nodes (6): Build and test (CLI), Code map, How it behaves, Install on your iPhone, NovaGlasses, On-device field checklist

### Community 230 - "protocol.py"
Cohesion: 0.39
Nodes (3): _artifact_for(), encode(), _truncate()

## Ambiguous Edges - Review These
- `TTS conversion enhancer prompt (empty)` → `Voice mode tone guidelines`  [AMBIGUOUS]
  prompting/tts_conversion_enhancer_prompt.txt · relation: conceptually_related_to

## Knowledge Gaps
- **165 isolated node(s):** `UserNotifications`, `.serverURLString`, `.summary`, `AudioToolbox`, `.count` (+160 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1781 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **103 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `TTS conversion enhancer prompt (empty)` and `Voice mode tone guidelines`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `NovaGlasses` connect `NovaGlasses` to `XCTestCase`, `ConversationController`, `.look`?**
  _High betweenness centrality (0.310) - this node is a cross-community bridge._
- **Are the 45 inferred relationships involving `AgentLoop` (e.g. with `Server behaviour` and `PromptEnums`) actually correct?**
  _`AgentLoop` has 45 INFERRED edges - model-reasoned connections that need verification._
- **What connects `UserNotifications`, `.serverURLString`, `.summary` to the rest of the system?**
  _165 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `transcribe_socket` be split into smaller, more focused modules?**
  _Cohesion score 0.14285714285714285 - nodes in this community are weakly interconnected._
- **Why does `Vision: "Hey Nova, what do you see?"` connect `.look` to `NovaGlasses`?**
  _High betweenness centrality (0.310) - this node is a cross-community bridge._
- **Are the 23 inferred relationships involving `Conversation` (e.g. with `_is_stale()` and `ConversationDao`) actually correct?**
  _`Conversation` has 23 INFERRED edges - model-reasoned connections that need verification._